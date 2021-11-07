# FHGR-CovidCertBot
## Functions
---
1. The CovidCertBot is designed for Github Actions. First it will scan your defined imap Email Inbox and look for a new Covid-Certificate.
2. It will download the Covid-Certificate and extract the test date
3. Afterwards it makes a post request to get the cookie for upload the files
4. It uploads the required data and the Covid-Certificate pdf

## Setup
---

### Dependencies
- Any Python 3.xx Version
- Take a look at the requirements.txt

### Variables
Create a new .env file and copy the variables from example.env
```.env
# Email setup
IMAP_DOMAIN = imap.exigo.ch
IMAP_PORT = 993
IMAP_USERNAME = exampleuser
IMAP_PASSWORD= password

# Intranet setup
INTRANET_USERNAME = "exampleuser"
INTRANET_PASSWORD = "password"

# Email from the sender of the Covid-Certificate
CERT_EMAIL_SENDER = '"noreply@2weeks.ch"'
```
## Setup Github Actions
1. Comming soon...
---
## Contributions and Issues
Feel free to make any contributions or open issues if you have some troubles.

## Credits
> Co-Authored by [Thomas Glauser](https://github.com/thomasglauser).