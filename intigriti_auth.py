import argparse
import logging

from json import loads, dumps
from typing import Optional

from authlib.integrations.httpx_client import OAuth2Client
from playwright.sync_api import sync_playwright

import http.client

http.client.HTTPConnection.debuglevel = 0  # 0 for off, > 0 for on

log_level: int = logging.ERROR
logging.basicConfig()
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(log_level)
requests_log.propagate = True
default_scopes: list = [
    'company_external_api',
    'offline_access',
    'core_platform:read',
    # 'core_platform:write',
    # 'reward_system:read',
    # 'reward_system:write'
]
DEFAULT_SCOPES: str = ','.join(default_scopes)
DEFAULT_CALLBACK: str = 'https://localhost/'


def get_redirect_via_browser(authorization_url: str, callback: str, timeout_s: float = 300) -> str:
    """Open authorization_url in a real (headed) browser, let the user complete
    login/MFA/CAPTCHA/consent by hand, and capture the resulting redirect to
    `callback` without ever letting the browser actually try to load it."""
    captured: dict = {}

    def _capture(route):
        captured['url'] = route.request.url
        route.fulfill(
            status=200,
            content_type='text/html',
            body='<html><body>Login complete &mdash; you may close this window.</body></html>',
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
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
        proxies: Optional[dict] = None,
        manual: bool = False,
) -> dict | str:
    scope = scopes.split(',') if scopes and isinstance(scopes, str) else default_scopes
    session = OAuth2Client(
        client_id=client_id,
        client_secret=client_secret,  # binds client_secret_basic auth for fetch_token/refresh_token
        scope=scope,  # must be set here for authorization and initial token to work
        redirect_uri=callback,
        proxy=proxies,
        headers={'Accept': 'application/json'},
    )

    uat_suffix: str = ''
    if uat:
        uat_suffix = '-uat'
    authorization_url, state = session.create_authorization_url(
        url=f'https://login{uat_suffix}.intigriti.com/connect/authorize',
    )

    if manual:
        print(f'\nAuthorize here: {authorization_url}')
        redirect_response = input('\nPaste Redirect URL: ')
    else:
        print('\nOpening browser to authorize... complete login/MFA/CAPTCHA/consent there.')
        redirect_response = get_redirect_via_browser(authorization_url, callback)

    token_resp: dict = session.fetch_token(
        url=f'https://login{uat_suffix}.intigriti.com/connect/token',
        authorization_response=redirect_response,
    )

    refresh_token: str = token_resp.get('refresh_token')
    session.scope = None  # causes 400 error if scope is included in refresh_token call
    refresh_resp: dict = session.refresh_token(
        url=f'https://login{uat_suffix}.intigriti.com/connect/token',
        refresh_token=refresh_token,
    )
    refresh_token = refresh_resp.get('refresh_token')

    # access_token: str = refresh_resp.get('access_token')  # to be used as Bearer token
    requests_log.debug(f' Initial token response:\n{dumps(token_resp, indent=4)}')
    requests_log.debug(f' Refresh token response:\n{dumps(refresh_resp, indent=4)}')

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
        help="enable debug logging",
    )
    parser.add_argument(
        '--manual',
        action='store_true',
        help="fall back to the old flow: print the authorization URL and prompt for the pasted redirect URL, "
             "instead of opening a browser and capturing it automatically",
    )

    args = parser.parse_args()

    proxies: Optional[dict] = None
    if args.proxies:
        proxies: dict = loads(args.proxies)

    if args.debug:
        http.client.HTTPConnection.debuglevel = args.debug
        requests_log.setLevel(args.debug)

    if data := main(
        client_id=args.client_id,
        client_secret=args.client_secret,
        scopes=args.scopes,
        callback=args.callback,
        uat=args.uat or False,
        proxies=proxies,
        manual=args.manual,
    ):
        print(f'\n\nSave this refresh token: {data.get("refresh_token")}\n\n')
    else:
        print('whoops...')
