# intigriti_auth
OAuth2 authorization for Intigriti API

# SECURITY NOTE:
I wrote the .py files.  You have my word that they don't do anything nefarious.  Even so, I recommend that you perform
your own static analysis and supply chain testing before use.  Many libraries are imported that are not in my own control.

# usage
```
$ python intigriti_auth.py -h
usage: intigriti_auth.py [-h] --client_id CLIENT_ID --client_secret CLIENT_SECRET --target_url TARGET_URL [--proxies PROXIES]

options:
  -h, --help                       show this help message and exit
  --client_id CLIENT_ID            The client_id for your Intigriti account
  --client_secret CLIENT_SECRET    The client_secret for your Intigriti account
  --target_url TARGET_URL          Target URL after login
  --proxies PROXIES                JSON structure specifying 'http' and 'https' proxy URLs

```

# example
```
$ python intigriti_auth.py --client_id MyClientID --client_secret MyClientSecret
```
