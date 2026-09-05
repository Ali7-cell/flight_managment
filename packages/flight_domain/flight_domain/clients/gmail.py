import os
import logging
from typing import Any
from flight_domain.config import settings

logger = logging.getLogger("flight_domain.gmail")

class GmailClient:
    def __init__(
        self,
        service_account_json: str | None = None,
        sender_address: str | None = None,
        delegated_subject: str | None = None,
        app_password: str | None = None,
    ):
        self.service_account_json = service_account_json or settings.GMAIL_SERVICE_ACCOUNT_JSON
        self.sender_address = sender_address or settings.GMAIL_SENDER_ADDRESS
        self.delegated_subject = delegated_subject or settings.GMAIL_DELEGATED_SUBJECT
        self.app_password = app_password or settings.GMAIL_APP_PASSWORD
        self.service = None
        self._init_service()

    def _init_service(self):
        # 1. Check if direct Gmail SMTP app password is provided
        if self.app_password and self.sender_address:
            logger.info("Configured Gmail SMTP with App Password.")
            return

        # 2. Check if a Service Account JSON file is provided
        if self.service_account_json and os.path.exists(self.service_account_json):
            try:
                import json
                with open(self.service_account_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check if it's OAuth Web Client instead of a Service Account
                if "web" in data or "installed" in data:
                    logger.info(
                        "Detected OAuth 2.0 Web Client JSON. Real background email delivery requires "
                        "either a Google Service Account Key or a Gmail App Password (GMAIL_APP_PASSWORD). "
                        "Running in mock email mode for now."
                    )
                    self.service = None
                    return

                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                
                scopes = ["https://www.googleapis.com/auth/gmail.send"]
                creds = service_account.Credentials.from_service_account_file(
                    self.service_account_json, scopes=scopes
                )
                if self.delegated_subject:
                    creds = creds.with_subject(self.delegated_subject)
                self.service = build("gmail", "v1", credentials=creds)
                logger.info("Initialized Google Gmail API client with service account.")
            except Exception as e:
                logger.warning(f"Could not initialize real Gmail client: {e}. Falling back to mock sender.")
                self.service = None
        else:
            logger.info("No valid Gmail credentials found. Running in mock email mode.")

    def send(self, to: str, subject: str, body: str, metadata: dict[str, Any] | None = None) -> bool:
        """Send an email via SMTP, Gmail API, or structured log."""
        logger.info(f"[OUTBOUND EMAIL] To: {to} | Subject: {subject} | Meta: {metadata} | Body preview: {body[:100]}...")
        
        # 1. If SMTP app password is configured, send via smtplib
        if self.app_password and self.sender_address:
            try:
                import smtplib
                from email.message import EmailMessage
                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = self.sender_address
                msg["To"] = to
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(self.sender_address, self.app_password)
                    server.send_message(msg)
                logger.info(f"[GMAIL SMTP] Successfully sent email to {to}")
                return True
            except Exception as e:
                logger.error(f"[GMAIL SMTP] Failed to send email: {e}")
                return False

        # 2. If Gmail API service account is configured, send via API
        if self.service:
            try:
                import base64
                from email.message import EmailMessage
                
                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = self.sender_address
                msg["To"] = to
                
                encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                create_message = {"raw": encoded_message}
                self.service.users().messages().send(userId="me", body=create_message).execute()
                return True
            except Exception as e:
                logger.error(f"Failed to send email via Gmail API: {e}")
                return False

        # 3. Mock mode fallback (succeeds safely in development and test environments)
        return True

    def send_checkin_reminder(self, flight: dict, local_departure: Any, passenger_email: str):
        subject = f"Check-in Open: Flight {flight.get('flight_number')} to {flight.get('destination')}"
        body = (
            f"Dear Passenger,\n\n"
            f"Online check-in is now open for your flight {flight.get('flight_number')} from {flight.get('origin')} "
            f"to {flight.get('destination')}.\n"
            f"Departure Time: {local_departure.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
            f"Safe travels!"
        )
        return self.send(to=passenger_email, subject=subject, body=body, metadata={"flight_id": str(flight.get("id"))})

gmail_client = GmailClient()
