import argparse
import logging
from datetime import datetime
from pathlib import Path

from app.account_loader import load_accounts
from app.browser_automation import BrowserAutomation
from app.config_loader import load_config
from app.gmail_otp import GmailOtpFetcher
from app.logging_utils import setup_logging


def append_result(results_file: Path, account_email: str, status: str, detail: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp} | {account_email} | {status} | {detail}\n"
    with results_file.open("a", encoding="utf-8") as f:
        f.write(line)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Selenium multi-account login automation with Gmail OTP."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config JSON (default: config.json)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config["files"]["logs_dir"])

    results_file = Path(config["files"]["results_file"])
    results_file.parent.mkdir(parents=True, exist_ok=True)

    accounts = load_accounts(config["files"]["accounts_file"])
    if not accounts:
        print("No accounts found in accounts file.")
        logging.warning("No accounts found in accounts file.")
        return

    browser = BrowserAutomation(config)
    otp_fetcher = GmailOtpFetcher(
        credentials_file=config["gmail"]["credentials_file"],
        token_file=config["gmail"]["token_file"],
        otp_regex=config["gmail"]["otp_regex"],
        poll_interval_seconds=config["gmail"]["poll_interval_seconds"],
        max_wait_seconds=config["gmail"]["max_wait_seconds"],
        search_query_template=config["gmail"]["search_query_template"],
    )

    user_data_dir = config["chrome"]["user_data_dir"]
    for account in accounts:
        if not browser.profile_exists(user_data_dir, account.profile_directory):
            message = (
                f"Profile not found: '{account.profile_directory}' for {account.account_email}"
            )
            print(message)
            logging.error(message)
            append_result(results_file, account.account_email, "ERROR", message)
            continue

        print(
            f"Processing account: {account.account_email} with profile {account.profile_directory}"
        )
        logging.info(
            "Processing account=%s profile=%s",
            account.account_email,
            account.profile_directory,
        )

        success, detail = browser.run_login_and_otp(account, otp_fetcher.wait_for_otp)
        status = "SUCCESS" if success else "ERROR"
        print(f"{account.account_email} -> {status}: {detail}")
        logging.info("%s -> %s: %s", account.account_email, status, detail)
        append_result(results_file, account.account_email, status, detail)


if __name__ == "__main__":
    main()
