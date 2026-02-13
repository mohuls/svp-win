import shutil
import time
from pathlib import Path
from typing import Callable, Dict, Tuple

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from app.models import Account


class BrowserAutomation:
    def __init__(self, config: Dict):
        self.config = config

    def profile_exists(self, user_data_dir: str, profile_directory: str) -> bool:
        profile_path = Path(user_data_dir) / profile_directory
        return profile_path.exists() and profile_path.is_dir()

    def run_login_and_otp(
        self,
        account: Account,
        otp_provider: Callable[[str, float], str],
    ) -> Tuple[bool, str]:
        driver = None
        try:
            driver = self._create_driver(account.profile_directory)
            wait = WebDriverWait(
                driver, self.config["selenium"].get("element_wait_seconds", 20)
            )
            flow_cfg = self.config["login_flow"]

            driver.get(flow_cfg["login_url"])

            wait.until(
                ec.visibility_of_element_located(
                    (By.CSS_SELECTOR, flow_cfg["username_selector"])
                )
            ).send_keys(account.login_username)
            driver.find_element(By.CSS_SELECTOR, flow_cfg["password_selector"]).send_keys(
                account.login_password
            )
            driver.find_element(By.CSS_SELECTOR, flow_cfg["submit_selector"]).click()

            otp_started_at = time.time()
            wait.until(
                ec.visibility_of_element_located(
                    (By.CSS_SELECTOR, flow_cfg["otp_selector"])
                )
            )
            otp_code = otp_provider(account.account_email, otp_started_at)
            driver.find_element(By.CSS_SELECTOR, flow_cfg["otp_selector"]).send_keys(
                otp_code
            )
            driver.find_element(By.CSS_SELECTOR, flow_cfg["otp_submit_selector"]).click()

            return True, "Login + OTP submitted."
        except FileNotFoundError as exc:
            return False, f"Profile copy error: {exc}"
        except TimeoutException as exc:
            return False, f"Timeout waiting for page element: {exc}"
        except SessionNotCreatedException as exc:
            return (
                False,
                "Chrome session could not start with the automation profile copy. "
                f"Details: {exc}",
            )
        except Exception as exc:
            return False, f"Automation error: {exc}"
        finally:
            if driver:
                driver.quit()

    def _create_driver(self, profile_directory: str):
        selenium_cfg = self.config["selenium"]
        launch_user_data_dir = self._resolve_launch_user_data_dir(profile_directory)

        options = Options()
        options.page_load_strategy = selenium_cfg.get("page_load_strategy", "eager")
        options.add_argument(f"--user-data-dir={launch_user_data_dir}")
        options.add_argument(f"--profile-directory={profile_directory}")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        if selenium_cfg.get("headless", False):
            options.add_argument("--headless=new")

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(selenium_cfg.get("implicit_wait_seconds", 5))
        driver.set_page_load_timeout(selenium_cfg.get("page_load_timeout_seconds", 45))
        return driver

    def _resolve_launch_user_data_dir(self, profile_directory: str) -> str:
        chrome_cfg = self.config["chrome"]
        source_user_data_dir = Path(chrome_cfg["user_data_dir"])

        if not chrome_cfg.get("use_local_profile_cache", True):
            return str(source_user_data_dir)

        cache_root = Path(chrome_cfg.get("automation_user_data_dir", "automation_chrome_data"))
        cache_root.mkdir(parents=True, exist_ok=True)

        source_profile = source_user_data_dir / profile_directory
        if not source_profile.exists():
            raise FileNotFoundError(f"Source profile does not exist: {source_profile}")

        cached_profile = cache_root / profile_directory
        refresh = chrome_cfg.get("refresh_cached_profile_each_run", False)
        if refresh and cached_profile.exists():
            shutil.rmtree(cached_profile, ignore_errors=True)

        if not cached_profile.exists():
            shutil.copytree(source_profile, cached_profile)

        return str(cache_root.resolve())
