"""Email notification support."""

import smtplib
from email.message import EmailMessage


class EmailNotifier:
    """Send job alerts using an SMTP server."""

    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send_message(self, recipient: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
