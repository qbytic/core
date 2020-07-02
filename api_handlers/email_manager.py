from smtplib import SMTP

from constants import MAIL_USERNAME, MAIL_PASS
from urllib.parse import quote


def _send(email, subject, content):
    with SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(MAIL_USERNAME, MAIL_PASS)
        message = f"Subject: {subject}\n\n{content}"
        smtp.sendmail(MAIL_USERNAME, email, message)


def get_link(t, token):
    if t == "password":
        x = "https://qbytic.com/u/-/tokens/auth/password/reset?token="
    else:
        x = "https://qbytic.com/u/-/tokens/auth/email/verify?token="
    return f"{x}{quote(token)}"


def send_email(token, t_type, email_id):
    if t_type == "password":
        subject = "Password Reset - Qbytic"
        content = f"You requested a password reset.\nYour reset link:\n{get_link(t_type,token)}"
    elif t_type == "email":
        subject = "Email Verify - Qbytic"
        content = f"Email verification requested.\nOpen this link to verify:\n{get_link(t_type,token)}"
    else:
        subject = t_type
        content = token
    return _send(email_id, subject, content)

