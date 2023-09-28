from os import path, getenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

gmail_user = getenv("GMAIL_USER")
gmail_password = getenv("GMAIL_PASSWORD")

basepath = path.dirname(__file__)
static = path.abspath(path.join(basepath, "static"))

with open(path.join(static, "verify.html"), "r") as f:
    verify_text = f.read()


def send(to: str, subject: str, html: str):
    sent_from = gmail_user

    msg = MIMEMultipart("alternative")
    msg["From"] = sent_from
    msg["To"] = to
    msg["Subject"] = subject

    html_part = MIMEText(html, "html")
    msg.attach(html_part)

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.ehlo()
    server.login(gmail_user, gmail_password)
    server.sendmail(gmail_user, to, msg.as_string())
    server.close()


def send_verify(to: str, name: str, server: str, code: str):
    send(
        to,
        f'Verify for {server}',
        verify_text.replace("{{name}}", name)
        .replace("{{server}}", server)
        .replace("{{code}}", code),
    )
