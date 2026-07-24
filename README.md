# intigriti_auth
OAuth2 authorization for the Intigriti API

# SECURITY NOTE:
I wrote the .py files.  You have my word that they don't do anything nefarious.  Even so, I recommend that you perform
your own static analysis and supply chain testing before use.  Many libraries are imported that are not in my own control.

# requirements
- Python 3
- [requests-oauthlib](https://pypi.org/project/requests-oauthlib/)

# usage
Running the script starts an interactive OAuth2 authorization code flow: it prints an authorization URL for you to
open in a browser, waits for you to paste back the redirect URL after you authorize, then exchanges that for a
token and immediately performs a refresh to obtain a refreshed refresh token.

```
$ python intigriti_auth.py -h
usage: intigriti_auth.py [-h] --client_id CLIENT_ID --client_secret CLIENT_SECRET [--scopes SCOPES] [--callback CALLBACK] [--uat UAT] [--proxies PROXIES] [--debug DEBUG]

options:
  -h, --help                       show this help message and exit
  --client_id CLIENT_ID            The client_id for your Intigriti account
  --client_secret CLIENT_SECRET    The client_secret for your Intigriti account
  --scopes SCOPES                  Comma-separated list of scopes for this Intigriti refresh token.
                                    Default: company_external_api,offline_access,core_platform:read
  --callback CALLBACK              The callback/redirect URL configured for the client_id (default: https://localhost/)
  --uat UAT                        connect to intigriti UAT env
  --proxies PROXIES                JSON structure specifying 'http' and 'https' proxy URLs
  --debug DEBUG                    enable debug logging (verbosity level)

```

# example
```
$ python intigriti_auth.py --client_id MyClientID --client_secret MyClientSecret

Authorize here: https://login.intigriti.com/connect/authorize?...

Paste Redirect URL: https://localhost/?code=...&state=...


Save this refresh token: <your refresh token>

```
