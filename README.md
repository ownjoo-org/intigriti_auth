# intigriti_auth

[![License](https://img.shields.io/github/license/ownjoo/intigriti_auth)](LICENSE)
OAuth2 authorization for the Intigriti API

# SECURITY NOTE:
I wrote the .py files.  You have my word that they don't do anything nefarious.  Even so, I recommend that you perform
your own static analysis and supply chain testing before use.  Many libraries are imported that are not in my own control.

# requirements
- Python 3
- [httpx](https://pypi.org/project/httpx/) (with the `http2` extra — Intigriti's endpoints negotiate HTTP/2)
- [Authlib](https://pypi.org/project/Authlib/)
- [Playwright](https://pypi.org/project/playwright/) (also requires a one-time browser install, see below)
- [oj-toolkit](https://pypi.org/project/oj-toolkit/) — shared logging/parsing utilities

```
$ pip install -r requirements.txt
$ playwright install chromium
```

`playwright install chromium` is only needed for the default `--browser chromium`. If you pass `--browser chrome`
or `--browser msedge` instead, Playwright drives your already-installed system browser directly and skips that
download entirely — useful in locked-down environments where downloading extra browser binaries isn't possible.

# usage
Running the script starts an interactive OAuth2 authorization code flow. By default it opens a real (visible)
Chromium window to the Intigriti authorization URL for you to log in, complete MFA/CAPTCHA, and consent — it then
automatically captures the resulting redirect URL (no copy/paste needed) instead of ever letting the browser try to
load `https://localhost/`. It then exchanges the resulting code for a token and immediately performs a refresh to
obtain a refreshed refresh token.

Pass `--manual` to fall back to the old flow instead: it prints the authorization URL for you to open yourself and
prompts you to paste back the redirect URL.

```
$ python intigriti_auth.py -h
usage: intigriti_auth.py [-h] --client_id CLIENT_ID --client_secret CLIENT_SECRET [--scopes SCOPES] [--callback CALLBACK] [--uat UAT] [--proxies PROXIES] [--debug DEBUG] [--manual] [--browser {chrome,chromium,msedge}]

options:
  -h, --help                       show this help message and exit
  --client_id CLIENT_ID            The client_id for your Intigriti account
  --client_secret CLIENT_SECRET    The client_secret for your Intigriti account
  --scopes SCOPES                  Comma-separated list of scopes for this Intigriti refresh token.
                                    Default: company_external_api,offline_access,core_platform:read
  --callback CALLBACK              The callback/redirect URL configured for the client_id (default: https://localhost/)
  --uat UAT                        connect to intigriti UAT env
  --proxies PROXIES                JSON structure specifying 'http' and 'https' proxy URLs
  --debug DEBUG                    numeric logging level (e.g. 10 for DEBUG, 20 for INFO); default is WARNING
  --manual                         fall back to the old flow: print the authorization URL and prompt for the
                                    pasted redirect URL, instead of opening a browser and capturing it automatically
  --browser {chrome,chromium,msedge}
                                    which browser to drive for the automatic login flow. 'chromium' (default) is
                                    Playwright's bundled build; 'chrome' and 'msedge' drive your already-installed
                                    system browser instead, with no extra download

```

# example
```
$ python intigriti_auth.py --client_id MyClientID --client_secret MyClientSecret

Opening browser to authorize... complete login/MFA/CAPTCHA/consent there.


Save this refresh token: <your refresh token>

```

# notes
- The script never handles your Intigriti username/password or solves the CAPTCHA for you — those steps stay
  entirely in your hands inside the Chromium window it opens. Automating past that (auto-filling credentials or
  solving the CAPTCHA) isn't something this project does.
- `client_id`/`client_secret` are only ever used for the direct, server-to-server token exchange and refresh
  calls (via httpx/Authlib) — they're never exposed to the browser/page context.

# testing
```
# unit tests -- fast, no network or browser (OAuth2Client and the browser leg are mocked)
$ python -m unittest discover -s test/unit -t .

# integration tests -- launches a real Chromium browser via Playwright against a local fixture server
$ python -m unittest discover -s test/int -t .

# everything
$ python -m unittest discover -s test -t .
```
