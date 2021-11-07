import os
import sys
from dotenv import load_dotenv
import email
import imaplib
import re
import requests
import pdfplumber

# Load variables from .env file
load_dotenv()

# .env Variables
IMAP_DOMAIN = os.getenv("IMAP_DOMAIN")
IMAP_PORT = os.getenv("IMAP_PORT")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

INTRANET_USERNAME = os.getenv("INTRANET_USERNAME")
INTRANET_PASSWORD = os.getenv("INTRANET_PASSWORD")

CERT_EMAIL_SENDER = '"' + os.getenv("CERT_EMAIL_SENDER") + '"'


# IMAP connection
try:
    imap = imaplib.IMAP4_SSL(IMAP_DOMAIN, IMAP_PORT)
except Exception as e:
    sys.exit("IMAP Server error: " + e)


# Login for IMAP Server
def email_login(IMAP_DOMAIN, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD):
    try:
        status, response = imap.login(IMAP_USERNAME, IMAP_PASSWORD)
    except Exception as e:
        sys.exit("IMAP login error: " + e)


# Logout from IMAP Server
def email_logout():
    imap.close()
    imap.logout()


# Searchs for the Certificate Download URL
def get_certificate_url_from_mail():
    status, response = imap.select("INBOX")
    status, response = imap.search(None, "FROM", CERT_EMAIL_SENDER)
    ids = response[0]
    id_list = ids.split()
    for email_id in id_list:
        status, response = imap.fetch(email_id, "(RFC822)")
        raw_email = response[0][1]
        raw_email_string = raw_email.decode("utf-8")
        email_message = email.message_from_string(raw_email_string).get_payload(
            decode=True
        )

        if "https://my.easytesting.ch/api/cert/" in str(email_message):

            match = re.search(
                "https?:\/\/(my.easytesting.ch\/api\/cert\/)([-a-zA-Z0-9]*)",
                str(email_message),
            )

            if match == None:
                sys.exit("No file URL in email message found!")

            url = match.group(0)

            print("Certificate file URL found.")
            return url


# Downloads Certificate via URL
def download_pdf(url):
    r = requests.get(url, allow_redirects=True)

    if '<!DOCTYPE html>' in str(r.content) or r.status_code != 200:
        sys.exit("Certificate download failed.")

    open("certificate.pdf", "wb").write(r.content)
    print("Successfully downloaded Certificate file.")


# Extracting Test Date from Certificate
def extract_date_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        pdf_content = pdf.pages[0].extract_text()

        match = re.search(
            "([0-9A-Z]* Datum und Zeit der )(.[.0-9]+)", pdf_content)

        if match == None:
            sys.exit("No valid timestamp in certificate found!")

        timestamp = match.group(2)
        return timestamp


# Login POST request for FHGR Intranet
def intranet_login(username, password):
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = "user=" + username + "&pass=" + password + "&logintype=login"

    r = requests.post(
        "https://my.fhgr.ch/index.php?id=home", headers=headers, data=data
    )

    match = re.search("(fe_typo_user=[0-9a-z]*)", r.headers["set-cookie"])
    session_token = match.group(1)

    if not session_token:
        sys.exit("Login failed! No session token received!")

    print("Intranet login successful.")
    return session_token


# Logout POST request for FHGR Intranet
def intranet_logout():
    data = "logintype=logout"
    r = requests.post("https://my.fhgr.ch/index.php?id=home", data=data)

    if r.status_code == 200:
        print("Intranet logout successful.")
    else:
        sys.exit("Intranet Logout failed!")


# Upload POST request for uploading:
# - typ -> 2 = "Betriebstest der FH Graubünden"
# - date -> Test Date (is in certificate.pdf)
# - result -> 1 = negative, 0 = positive
# - certificate -> pdf File
def upload_pdf(session_token, typ, date, result, file_path):
    headers = {"Cookie": session_token}
    data = {
        'tx_htwnotadr_user[covidzert][typ]': typ,
        'tx_htwnotadr_user[covidzert][date]': date,
        'tx_htwnotadr_user[covidzert][result]': result,
        'file_nachweis': open(file_path, 'rb')
    }

    r = requests.post(
        "https://my.fhgr.ch/index.php?id=home", headers=headers, data=data
    )

    if r.status_code == 200:
        print("Certificate file upload successful.")
    else:
        sys.exit("Certificate file upload failed!")


# Function calls
def main():
    print("Starting...")
    email_login(IMAP_DOMAIN, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD)
    url = get_certificate_url_from_mail()
    email_logout()
    download_pdf(url)
    timestamp = extract_date_from_pdf("./certificate.pdf")
    session_token = intranet_login(INTRANET_USERNAME, INTRANET_PASSWORD)
    upload_pdf(session_token, "2", timestamp, "1", 'certificate.pdf')
    intranet_logout()
    print("Job successfully finished!")


if __name__ == "__main__":
    main()
