import argparse
import logging

from json import loads, dumps
from typing import Optional

from requests_oauthlib import OAuth2Session

import http.client

http.client.HTTPConnection.debuglevel = 0  # 0 for off, > 0 for on

log_level: int = logging.ERROR
logging.basicConfig()
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(log_level)
requests_log.propagate = True


def main(
        client_id: str,
        client_secret: str,
        scopes: str = 'offline_access',
        callback: str = 'https://localhost/',
        uat: bool = False,
        proxies: Optional[dict] = None,
) -> dict | str:
    scope = scopes.split(',') if isinstance(scopes, str) else scopes
    session = OAuth2Session(
        client_id=client_id,
        scope=scope,  # must be set here for authorization and initial token to work
        redirect_uri=callback,
    )
    session.proxies = proxies
    session.headers = {'Accept': 'application/json'}

    uat_suffix: str = ''
    if uat:
        uat_suffix = '-uat'
    authorization_url, state = session.authorization_url(
        url=f'https://login{uat_suffix}.intigriti.com/connect/authorize',
    )

    print(f'\nAuthorize here: {authorization_url}')
    redirect_response = input('\nPaste Redirect URL: ')

    token_resp: dict = session.fetch_token(
        token_url=f'https://login{uat_suffix}.intigriti.com/connect/token',
        client_secret=client_secret,
        authorization_response=redirect_response,
    )

    refresh_token: str = token_resp.get('refresh_token')  # TODO: save this somewhere
    session.scope = None  # causes 400 error if scope is included in refresh_token call
    refresh_resp: dict = session.refresh_token(
        token_url=f'https://login{uat_suffix}.intigriti.com/connect/token',
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
    )
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
        help='The scopes for this Intigriti refresh token',
        default='offline_access',
    )
    parser.add_argument(
        '--callback',
        type=str,
        required=False,
        help='The callback/redirect URL configured for the client_id',
        default='https://localhost/',
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

    args = parser.parse_args()

    proxies: Optional[dict] = None
    if args.proxies:
        proxies: dict = loads(args.proxies)

    if data := main(
        client_id=args.client_id,
        client_secret=args.client_secret,
        scopes=args.scopes,
        callback=args.callback,
        uat=args.uat or False,
        proxies=proxies,
    ):
        print(f'\n\nSave this refresh token: {data.get("refresh_token")}\n\n')
    else:
        print('whoops...')
