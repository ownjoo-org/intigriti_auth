# intigriti_auth
OAuth2 authorization for Intigriti API

# SECURITY NOTE:
I wrote the .py files.  You have my word that they don't do anything nefarious.  Even so, I recommend that you perform
your own static analysis and supply chain testing before use.  Many libraries are imported that are not in my own control.

# usage
```
$ python github_login.py -h
usage: github_login.py [-h] --client_id CLIENT_ID --client_secret CLIENT_SECRET --target_url TARGET_URL [--proxies PROXIES]

options:
  -h, --help                        show this help message and exit
  --client_id CLIENT_ID             The user name for your IdP account
  --client_secret CLIENT_SECRET     The password for your IdP account
  --target_url TARGET_URL           Target URL after login
  --proxies PROXIES                 JSON structure specifying 'http' and 'https' proxy URLs
```

# example
```
$ python github_logon.py --sp_url https://app.example.com/sso/saml/start --username MyUsername --password MyPassword

```
