# Selenium + Gmail OTP Automation (Basic Version)

This is a starter Python application that:

- Reads multiple account entries from `accounts.txt`
- Opens each account using its specified Chrome profile
- Logs in with Selenium
- Waits for OTP input screen
- Fetches OTP from one Gmail inbox (shared for all accounts) using Gmail API
- Populates OTP and submits
- Prints per-account success/error in terminal
- Saves detailed logs and per-account results to files

## 1. Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Create Config Files

1. Copy `config.example.json` to `config.json`
2. Copy `accounts.example.txt` to `accounts.txt`
3. Update both files with your real values

## 3. Gmail API Setup (One Shared Gmail for OTP)

1. Go to Google Cloud Console
2. Create/select a project
3. Enable Gmail API
4. Configure OAuth consent screen
5. Create OAuth Client ID of type `Desktop app`
6. Download the JSON file and save it as `credentials.json` in project root

On first run, browser auth will open for Gmail. After successful login, `token.json` is created and reused.

## 4. Accounts File Format

`accounts.txt` format (one account per line):

```text
account_email,login_username,login_password,profile_directory
```

Example:

```text
user1@example.com,user1@example.com,password123,Default
user2@example.com,user2@example.com,password456,Profile 1
```

`profile_directory` must exist under `chrome.user_data_dir`.
If missing, terminal output and result file will contain `Profile not found`.

## 5. Run

```powershell
python main.py --config config.json
```

## 6. Output Files

- Logs: `logs/app.log`
- Per-account result summary: `run_results.txt`

## 7. Important Notes for Basic Version

- You must set the correct CSS selectors in `config.json -> login_flow`.
- OTP extraction uses regex from `gmail.otp_regex` (default captures 6 digits).
- Gmail query is configurable via `gmail.search_query_template`.
- If needed, include `{account_email}` in query template to filter per account context.
- By default, Selenium launches from `chrome.automation_user_data_dir` using cached copies of selected profiles.
  This avoids common Windows `DevToolsActivePort` crashes with the default Chrome data directory.
