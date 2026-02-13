from pathlib import Path
from typing import List

from app.models import Account


def load_accounts(accounts_file: str) -> List[Account]:
    path = Path(accounts_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Accounts file not found: {path}. Copy accounts.example.txt to accounts.txt and update it."
        )

    accounts: List[Account] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 4:
                raise ValueError(
                    f"Invalid accounts line {line_number}. Expected 4 comma-separated values."
                )

            account_email, login_username, login_password, profile_directory = parts
            accounts.append(
                Account(
                    account_email=account_email,
                    login_username=login_username,
                    login_password=login_password,
                    profile_directory=profile_directory,
                )
            )

    return accounts
