import os
from dotenv import load_dotenv
import email
import imaplib
import re
import requests
import pdfplumber

load_dotenv()

IMAP_DOMAIN = os.getenv("IMAP_DOMAIN")
IMAP_PORT = os.getenv("IMAP_PORT")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

INTRANET_USERNAME = os.getenv("INTRANET_USERNAME")
INTRANET_PASSWORD = os.getenv("INTRANET_PASSWORD")

CERT_EMAIL_SENDER = os.getenv("CERT_EMAIL_SENDER")


imap = imaplib.IMAP4_SSL(IMAP_DOMAIN, IMAP_PORT)
status, response = imap.login(IMAP_USERNAME, IMAP_PASSWORD)


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
                return print("No URL in Message found!")

            url = match.group(0)

            print("File URL found: " + url)
            return url


def download_pdf(url):
    r = requests.get(url, allow_redirects=True)
    open("certificate.pdf", "wb").write(r.content)


def extract_date_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        pdf_content = pdf.pages[0].extract_text()

        match = re.search(
            "([0-9A-Z]* Datum und Zeit der )(.[.0-9]+)", pdf_content)

        timestamp = match.group(2)
        print(timestamp)
        return timestamp


def intranet_login(username, password):
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = "user=" + username + "&pass=" + password + "&logintype=login"

    r = requests.post(
        "https://my.fhgr.ch/index.php?id=home", headers=headers, data=data
    )

    match = re.search("(fe_typo_user=[0-9a-z]*)", r.headers["set-cookie"])
    session_token = match.group(1)

    print("Got Session Token: " + session_token)
    return session_token


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

    print(r.status_code)


url = get_certificate_url_from_mail()
download_pdf(url)
timestamp = extract_date_from_pdf("./certificate.pdf")
session_token = intranet_login(INTRANET_USERNAME, INTRANET_PASSWORD)
upload_pdf(session_token, "2", timestamp, "1", 'certificate.pdf')


# In Funktion einbauen
status = imap.close()
print(status)
status = imap.logout()
print(status)
