from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    account_email: str
    login_username: str
    login_password: str
    profile_directory: str
