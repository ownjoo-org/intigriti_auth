"""Interactive OAuth2 authorization-code flow for the Intigriti API.

Drives Intigriti's Duende IdentityServer endpoints (authorize -> token -> refresh)
via an httpx/Authlib OAuth2Client, and automates the browser leg of the flow with
Playwright: it opens a real, headed browser to the authorization URL, lets the
human complete login/MFA/CAPTCHA/consent (none of that is or can be automated
here), and captures the resulting redirect via request interception instead of
requiring a manual copy/paste of the redirect URL.
"""

import argparse
import logging
from json import dumps, loads

from authlib.integrations.httpx_client import OAuth2Client
from oj_toolkit.logging import configure_logging
from oj_toolkit.parsing.types import dig, str_to_list
from playwright.sync_api import Route, sync_playwright

logger = logging.getLogger(__name__)

default_scopes: list[str] = [
    'company_external_api',
    'offline_access',
    'core_platform:read',
    # 'core_platform:write',
    # 'reward_system:read',
    # 'reward_system:write'
]
DEFAULT_SCOPES: str = ','.join(default_scopes)
DEFAULT_CALLBACK: str = 'https://localhost/'

# Playwright's `channel` argument for browser_type.launch(): None drives Playwright's
# own bundled Chromium build (requires `playwright install chromium`); the others drive
# an already-installed system browser directly, with no extra binary download needed.
BROWSER_CHANNELS: dict[str, str | None] = {
    'chromium': None,  # Playwright's own bundled build, requires `playwright install chromium`
    'chrome': 'chrome',  # drives the system-installed Google Chrome, no extra download
    'msedge': 'msedge',  # drives the system-installed Microsoft Edge, no extra download
}


def get_redirect_via_browser(
        authorization_url: str,
        callback: str,
        timeout_s: float = 300,
        channel: str | None = None,
) -> str:
    """Open authorization_url in a real (headed) browser, let the user complete
    login/MFA/CAPTCHA/consent by hand, and capture the resulting redirect to
    `callback` without ever letting the browser actually try to load it.

    Args:
        authorization_url: The IdentityServer /connect/authorize URL to open.
        callback: The registered redirect_uri to watch for and intercept
            (e.g. 'https://localhost/'). Nothing needs to be listening on it --
            the request is captured and short-circuited before it's ever sent.
        timeout_s: How long to wait for the user to complete the browser flow
            before giving up.
        channel: Playwright browser channel to launch (see BROWSER_CHANNELS).
            None launches Playwright's own bundled Chromium build.

    Returns:
        The full redirect URL (including the `code`/`state` query string) that
        the browser was sent to after authorization completed.

    Raises:
        TimeoutError: If the redirect isn't captured within timeout_s.
    """
    captured: dict[str, str] = {}

    def _capture(route: Route) -> None:
        # Intercept the browser's navigation to `callback` and answer it locally
        # instead of letting it actually connect -- `callback` is typically
        # unroutable (e.g. https://localhost/ with nothing listening).
        captured['url'] = route.request.url
        route.fulfill(
            status=200,
            content_type='text/html',
            body='<html><body>Login complete &mdash; you may close this window.</body></html>',
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel=channel)
        page = browser.new_page()
        page.route(f'{callback}*', _capture)
        page.goto(authorization_url)

        elapsed = 0.0
        interval = 0.5
        while 'url' not in captured and elapsed < timeout_s:
            page.wait_for_timeout(interval * 1000)
            elapsed += interval

        browser.close()

    if 'url' not in captured:
        raise TimeoutError(f'Timed out after {timeout_s}s waiting for redirect to {callback}')
    return captured['url']


def main(
        client_id: str,
        client_secret: str,
        scopes: str = DEFAULT_SCOPES,
        callback: str = DEFAULT_CALLBACK,
        uat: bool = False,
        proxies: dict[str, str] | None = None,
        manual: bool = False,
        browser: str = 'chromium',
) -> dict | str | None:
    """Run the full OAuth2 authorization-code flow against Intigriti and return tokens.

    Requests an authorization code (via a headed browser by default, or manually
    if `manual` is set), exchanges it for an access/refresh token pair, then
    immediately performs a refresh to obtain a refreshed refresh token -- Intigriti
    refresh tokens rotate on use, so the one returned by the initial token exchange
    is not the one that should be persisted for future use.

    Args:
        client_id: OAuth2 client_id for the Intigriti app registration.
        client_secret: OAuth2 client_secret for the same app registration.
        scopes: Comma-separated scope list. Defaults to DEFAULT_SCOPES.
        callback: The redirect_uri registered for client_id.
        uat: If True, target Intigriti's UAT environment instead of production.
        proxies: Optional {'http': ..., 'https': ...}-style proxy mapping.
        manual: If True, print the authorization URL and prompt for the pasted
            redirect URL instead of driving a browser automatically.
        browser: Which Playwright browser channel to use (see BROWSER_CHANNELS).
            Ignored when manual=True.

    Returns:
        The initial token response dict on success (contains access_token,
        refresh_token, etc.), or a bare refresh_token string in the unlikely
        case fetch_token() returns a falsy response.
    """
    scope: list[str] | None = str_to_list(scopes) if scopes else default_scopes
    session = OAuth2Client(
        client_id=client_id,
        client_secret=client_secret,  # binds client_secret_basic auth for fetch_token/refresh_token
        scope=scope,  # must be set here for authorization and initial token to work
        redirect_uri=callback,
        proxy=proxies,
        headers={'Accept': 'application/json'},
        http2=True,
    )

    uat_suffix: str = ''
    if uat:
        uat_suffix = '-uat'
    authorization_url, _state = session.create_authorization_url(
        url=f'https://login{uat_suffix}.intigriti.com/connect/authorize',
    )

    redirect_response: str
    if manual:
        print(f'\nAuthorize here: {authorization_url}')
        redirect_response = input('\nPaste Redirect URL: ')
    else:
        print('\nOpening browser to authorize... complete login/MFA/CAPTCHA/consent there.')
        redirect_response = get_redirect_via_browser(
            authorization_url,
            callback,
            channel=BROWSER_CHANNELS[browser],
        )

    token_resp: dict = session.fetch_token(
        url=f'https://login{uat_suffix}.intigriti.com/connect/token',
        authorization_response=redirect_response,
    )

    refresh_token: str | None = dig(token_resp, path='refresh_token', exp=str)
    session.scope = None  # causes 400 error if scope is included in refresh_token call
    refresh_resp: dict = session.refresh_token(
        url=f'https://login{uat_suffix}.intigriti.com/connect/token',
        refresh_token=refresh_token,
    )
    refresh_token = dig(refresh_resp, path='refresh_token', exp=str)

    # access_token: str = refresh_resp.get('access_token')  # to be used as Bearer token
    logger.debug(f' Initial token response:\n{dumps(token_resp, indent=4)}')
    logger.debug(f' Refresh token response:\n{dumps(refresh_resp, indent=4)}')

    if token_resp:
        return token_resp
    else:
        return refresh_token


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--client_id',
        type=str,
        required=True,
        help='The client_id for your Intigriti account',
    )
    parser.add_argument(
        '--client_secret',
        type=str,
        required=True,
        help='The client_secret for your Intigriti account',
    )
    parser.add_argument(
        '--scopes',
        type=str,
        help='Comma-separated list of scopes for this Intigriti refresh token.',
        default=DEFAULT_SCOPES,
    )
    parser.add_argument(
        '--callback',
        type=str,
        required=False,
        help='The callback/redirect URL configured for the client_id',
        default=DEFAULT_CALLBACK,
    )
    parser.add_argument(
        '--uat',
        type=bool,
        required=False,
        help="connect to intigriti UAT env",
    )
    parser.add_argument(
        '--proxies',
        type=str,
        required=False,
        help="JSON structure specifying 'http' and 'https' proxy URLs",
    )
    parser.add_argument(
        '--debug',
        type=int,
        help="numeric logging level (e.g. 10 for DEBUG, 20 for INFO); default is WARNING",
    )
    parser.add_argument(
        '--manual',
        action='store_true',
        help="fall back to the old flow: print the authorization URL and prompt for the pasted redirect URL, "
             "instead of opening a browser and capturing it automatically",
    )
    parser.add_argument(
        '--browser',
        type=str,
        choices=sorted(BROWSER_CHANNELS),
        default='chromium',
        help="which browser to drive for the automatic login flow. 'chromium' is Playwright's bundled build "
             "(requires `playwright install chromium`); 'chrome' and 'msedge' drive your already-installed "
             "system browser instead, with no extra download -- useful in locked-down environments.",
    )

    args = parser.parse_args()

    proxies: dict[str, str] | None = None
    if args.proxies:
        proxies = loads(args.proxies)

    configure_logging(service='intigriti_auth', level=args.debug or None)

    if data := main(
        client_id=args.client_id,
        client_secret=args.client_secret,
        scopes=args.scopes,
        callback=args.callback,
        uat=args.uat or False,
        proxies=proxies,
        manual=args.manual,
        browser=args.browser,
    ):
        print(f'\n\nSave this refresh token: {dig(data, path="refresh_token", exp=str)}\n\n')
    else:
        print('whoops...')
