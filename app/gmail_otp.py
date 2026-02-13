import base64
import logging
import re
import time
from pathlib import Path
from typing import Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailOtpFetcher:
    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        otp_regex: str,
        poll_interval_seconds: int,
        max_wait_seconds: int,
        search_query_template: str,
    ) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.otp_regex = otp_regex
        self.poll_interval_seconds = poll_interval_seconds
        self.max_wait_seconds = max_wait_seconds
        self.search_query_template = search_query_template
        self._service = self._build_service()

    def _build_service(self):
        creds = None
        token_path = Path(self.token_file)
        credentials_path = Path(self.credentials_file)

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {credentials_path}. "
                        "Create OAuth Desktop credentials and save as credentials.json."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=creds)

    def wait_for_otp(self, account_email: str, started_at_epoch: float) -> str:
        deadline = time.time() + self.max_wait_seconds
        search_query = self._build_query(account_email)

        while time.time() < deadline:
            code = self._find_latest_otp(search_query, started_at_epoch)
            if code:
                return code
            time.sleep(self.poll_interval_seconds)

        raise TimeoutError(
            f"No OTP found for account {account_email} within {self.max_wait_seconds} seconds."
        )

    def _build_query(self, account_email: str) -> str:
        return self.search_query_template.replace("{account_email}", account_email)

    def _find_latest_otp(
        self, query: str, started_at_epoch: float
    ) -> Optional[str]:
        try:
            response = (
                self._service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=10,
                )
                .execute()
            )
            messages = response.get("messages", [])
            for message in messages:
                msg = (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="full")
                    .execute()
                )
                internal_date_ms = int(msg.get("internalDate", "0"))
                if internal_date_ms < int(started_at_epoch * 1000):
                    continue

                body = self._extract_message_text(msg.get("payload", {}))
                otp = self._extract_otp(body)
                if otp:
                    logging.info("OTP matched from Gmail message id=%s", message["id"])
                    return otp
        except HttpError as exc:
            logging.error("Gmail API error: %s", exc)

        return None

    def _extract_otp(self, text: str) -> Optional[str]:
        match = re.search(self.otp_regex, text)
        return match.group(1) if match else None

    def _extract_message_text(self, payload: Dict) -> str:
        chunks = []

        def walk(part: Dict) -> None:
            body = part.get("body", {})
            data = body.get("data")
            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode(
                        "utf-8", errors="ignore"
                    )
                    chunks.append(decoded)
                except Exception:
                    pass

            for sub_part in part.get("parts", []) or []:
                walk(sub_part)

        walk(payload)
        return "\n".join(chunks)
