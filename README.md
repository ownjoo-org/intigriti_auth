# intigriti_auth
OAuth2 authorization for the Intigriti API

# SECURITY NOTE:
I wrote the .py files.  You have my word that they don't do anything nefarious.  Even so, I recommend that you perform
your own static analysis and supply chain testing before use.  Many libraries are imported that are not in my own control.

# requirements
- Python 3
- [httpx](https://pypi.org/project/httpx/)
- [Authlib](https://pypi.org/project/Authlib/)
- [Playwright](https://pypi.org/project/playwright/) (also requires a one-time browser install, see below)

```
$ pip install -r requirements.txt
$ playwright install chromium
```

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
usage: intigriti_auth.py [-h] --client_id CLIENT_ID --client_secret CLIENT_SECRET [--scopes SCOPES] [--callback CALLBACK] [--uat UAT] [--proxies PROXIES] [--debug DEBUG] [--manual]

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
  --manual                         fall back to the old flow: print the authorization URL and prompt for the
                                    pasted redirect URL, instead of opening a browser and capturing it automatically

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
