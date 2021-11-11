"""FHGR-CovidCertBot"""

import os
import sys
import email
import imaplib
import re
import requests
import pdfplumber
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# .env Variables
IMAP_DOMAIN = os.getenv("IMAP_DOMAIN")
IMAP_PORT = os.getenv("IMAP_PORT")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

INTRANET_USERNAME = os.getenv("INTRANET_USERNAME")
INTRANET_PASSWORD = os.getenv("INTRANET_PASSWORD")

CERT_EMAIL_SENDER = os.getenv("CERT_EMAIL_SENDER")
CERT_LINK = os.getenv("CERT_LINK")
CERT_REGEX = os.getenv("CERT_REGEX")


MANDATORY_ENV_VARS = ["IMAP_DOMAIN", "IMAP_PORT",
                      "IMAP_USERNAME", "IMAP_PASSWORD",
                      "INTRANET_USERNAME", "INTRANET_PASSWORD",
                      "CERT_EMAIL_SENDER", "CERT_LINK", "CERT_REGEX"]

for var in MANDATORY_ENV_VARS:
    if var not in os.environ:
        print("Missing environment variable: " + var)
        sys.exit("Failed! Not all required environment variables are set!")


imap = imaplib.IMAP4_SSL(IMAP_DOMAIN, IMAP_PORT)


def email_login(username, password):
    """IMAP login"""
    imap.login(username, password)


def email_logout():
    """IMAP logout"""
    imap.close()
    imap.logout()


def get_cert_url(email_from, email_link, email_regex):
    """Extract the latest certificate URL from the email inbox"""

    email_from_formatted = '"' + email_from + '"'

    response = imap.select("INBOX")
    response = imap.search(None, "FROM", email_from_formatted)
    ids = response[0]
    id_list = ids.split()

    for email_id in id_list:
        response = imap.fetch(email_id, "(RFC822)")
        raw_email = response[0][1]
        raw_email_string = raw_email.decode("utf-8")
        email_message = email.message_from_string(raw_email_string)
        email_string = email_message.get_payload(decode=True)

        if email_link in str(email_string):

            match = re.search(email_regex, str(email_string))

            if match is None:
                sys.exit("No file URL in email message found!")

            url = match.group(0)

            print("Certificate file URL found.")
            return url


def download_pdf(url):
    """Download the certificate file"""

    response = requests.get(url, allow_redirects=True)

    if ('<!DOCTYPE html>' in str(response.content)
            or response.status_code != 200):
        sys.exit("Certificate download failed.")

    open("certificate.pdf", "wb").write(response.content)
    print("Successfully downloaded Certificate file.")


def extract_date_from_pdf(file_path):
    """Extract the timestamp from the certificate file"""

    with pdfplumber.open(file_path) as pdf:
        pdf_content = pdf.pages[0].extract_text()

        match = re.search(
            "([0-9A-Z]* Datum und Zeit der )(.[.0-9]+)", pdf_content)

        if match is None:
            sys.exit("No valid timestamp in certificate found!")

        timestamp = match.group(2)
        return timestamp


def intranet_login(username, password):
    """Login POST request to FHGR Intranet"""

    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = "user=" + username + "&pass=" + password + "&logintype=login"

    response = requests.post(
        "https://my.fhgr.ch/index.php?id=home", headers=headers, data=data
    )

    if not response.headers["set-cookie"]:
        print(response)
        print(response.headers)
        print(response.content)
        sys.exit("Intranet Login failed!")

    match = re.search("(fe_typo_user=[0-9a-z]*)",
                      response.headers["set-cookie"])

    session_token = match.group(1)

    if not session_token:
        sys.exit("No valid session token received!")

    print("Intranet login successful.")
    return session_token


def intranet_logout():
    """Logout POST request to FHGR Intranet"""

    data = "logintype=logout"
    response = requests.post("https://my.fhgr.ch/index.php?id=home", data=data)

    if response.status_code == 200:
        print("Intranet logout successful.")
    else:
        sys.exit("Intranet Logout failed!")


def upload_pdf(session_token, typ, date, result, file_path):
    """
    PDF File upload to FHGR Intranet:
    - typ -> 2 = "Betriebstest der FH Graubünden"
    - date -> Test Date (is in certificate.pdf)
    - result -> 1 = negative, 0 = positive
    - certificate -> pdf File
    """

    headers = {"Cookie": session_token}
    data = {
        'tx_htwnotadr_user[covidzert][typ]': typ,
        'tx_htwnotadr_user[covidzert][date]': date,
        'tx_htwnotadr_user[covidzert][result]': result,
        'file_nachweis': open(file_path, 'rb')
    }

    response = requests.post(
        "https://my.fhgr.ch/index.php?id=home", headers=headers, data=data
    )

    if response.status_code == 200:
        print("Certificate file upload successful.")
    else:
        sys.exit("Certificate file upload failed!")


def main():
    """Workflow Process"""

    print("Starting...")
    email_login(IMAP_USERNAME, IMAP_PASSWORD)
    url = get_cert_url(CERT_EMAIL_SENDER, CERT_LINK, CERT_REGEX)
    email_logout()
    download_pdf(url)
    timestamp = extract_date_from_pdf("./certificate.pdf")
    session_token = intranet_login(INTRANET_USERNAME, INTRANET_PASSWORD)
    upload_pdf(session_token, "2", timestamp, "1", 'certificate.pdf')
    intranet_logout()
    print("Job successfully finished!")


if __name__ == "__main__":
    main()
