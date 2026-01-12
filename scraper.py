
# scraper.py
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from config import CONFIG

load_dotenv()

SITE_URL = os.getenv("SITE_URL")
LOGIN_URL = os.getenv("LOGIN_URL", SITE_URL)
QUEUES_PAGE_URL = os.getenv("QUEUES_PAGE_URL", SITE_URL)
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Persist session data so subsequent runs reuse cookies (helps avoid re-login)
USER_DATA_DIR = os.path.join(os.getcwd(), ".user_data")

def _try_login(page, username: Optional[str], password: Optional[str]) -> None:
    """
    Attempt login only if username/password were provided.
    Assumes a classic login form; adjust selectors in config.py.
    """
    if not username or not password:
        return  # No credentials provided; rely on existing session

    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=CONFIG["page_load_timeout_ms"])

    # Fill the login form
    try:
        page.fill(CONFIG["login"]["username_selector"], username)
        page.fill(CONFIG["login"]["password_selector"], password)
        page.click(CONFIG["login"]["submit_selector"])
    except PlaywrightTimeoutError:
        pass

    # Wait for post-login indicator (optional)
    try:
        page.wait_for_selector(
            CONFIG["login"]["post_login_check_selector"],
            timeout=CONFIG["login"]["login_timeout_ms"]
        )
    except PlaywrightTimeoutError:
        # Even if we didn't find the indicator, we may still be logged in
        pass

def _ensure_authenticated(page, username: Optional[str], password: Optional[str]) -> None:
    """
    If reaching queues page redirects to login, try logging in.
    If already authenticated, this is fast.
    """
    try:
        page.goto(QUEUES_PAGE_URL, wait_until="domcontentloaded", timeout=CONFIG["page_load_timeout_ms"])
    except PlaywrightTimeoutError:
        # Try site root as a fallback
        page.goto(SITE_URL, wait_until="domcontentloaded", timeout=CONFIG["page_load_timeout_ms"])

    # If the queues page still shows login form, attempt login
    # We detect presence of username field to decide
    try:
        login_field_count = page.locator(CONFIG["login"]["username_selector"]).count()
    except Exception:
        login_field_count = 0

    if login_field_count > 0:
        _try_login(page, username, password)
        page.goto(QUEUES_PAGE_URL, wait_until="domcontentloaded", timeout=CONFIG["page_load_timeout_ms"])

    page.wait_for_timeout(CONFIG["network_idle_timeout_ms"])

def _click_queue_tab(page, queue_name: str) -> None:
    """
    Click the tab whose text matches queue_name (case-insensitive).
    """
    container = page.locator(CONFIG["queue_tab_container_selector"])
    if container.count() == 0:
        raise RuntimeError("Queue tab container not found. Verify 'queue_tab_container_selector' in config.py.")

    tabs = container.locator(CONFIG["queue_tab_item_selector"])
    count = tabs.count()
    if count == 0:
        raise RuntimeError("No queue tabs found. Adjust 'queue_tab_item_selector' in config.py.")

    for i in range(count):
        label = tabs.nth(i).inner_text().strip()
        if label.lower() == queue_name.lower():
            tabs.nth(i).click()
            page.wait_for_timeout(CONFIG["network_idle_timeout_ms"])
            return

    raise RuntimeError(f"Queue tab '{queue_name}' not found.")

def _read_table_page(page) -> List[Dict]:
    """
    Read current table rows and return list of dicts using the header mapping.
    """
    table = page.locator(CONFIG["table_selector"])
    if table.count() == 0:
        # Try a short wait for lazy-loaded content
        page.wait_for_timeout(500)
    if table.count() == 0:
        raise RuntimeError("Queue table not found. Check 'table_selector' in config.py.")

    headers = []
    header_els = page.locator(CONFIG["table_header_selector"])
    for i in range(header_els.count()):
        headers.append(header_els.nth(i).inner_text().strip())

    rows_data = []
    rows = page.locator(CONFIG["table_row_selector"])
    for r in range(rows.count()):
        cells = rows.nth(r).locator(CONFIG["table_cell_selector"])
        row_map = {}
        for c in range(cells.count()):
            # Use header name if available, otherwise generic name
            header = headers[c] if c < len(headers) else f"col_{c}"
            key = CONFIG["columns_map"].get(header, header)  # normalize column names
            val = cells.nth(c).inner_text().strip()
            row_map[key] = val
        rows_data.append(row_map)

    return rows_data

def _click_next_if_available(page) -> bool:
    """
    Click 'Next' pagination button when available.
    Use disabled class or text content checks.
    """
    next_btns = page.locator(CONFIG["next_button_selector"])
    if next_btns.count() == 0:
        return False

    # Prefer disabled-class check
    for i in range(next_btns.count()):
        btn = next_btns.nth(i)
        cls = (btn.get_attribute("class") or "").lower()
        text = btn.inner_text().strip()
        if CONFIG["next_button_disabled_class"] in cls:
            continue
        if CONFIG["next_button_texts"] and text not in CONFIG["next_button_texts"]:
            continue
        btn.click()
        page.wait_for_timeout(CONFIG["network_idle_timeout_ms"])
        return True

    return False

def fetch_queue_records(queue_name: str,
                        username: Optional[str] = None,
                        password: Optional[str] = None) -> List[Dict]:
    """
    Main entry: open site, ensure authenticated (using supplied creds only if needed),
    open the selected queue tab, and read all pages.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=HEADLESS,
            args=["--no-sandbox"],
        )
        page = browser.new_page()

        _ensure_authenticated(page, username, password)
        _click_queue_tab(page, queue_name)

        all_rows = []
        while True:
            page_rows = _read_table_page(page)
            all_rows.extend(page_rows)
            if not _click_next_if_available(page):
                break

        browser.close()

    return all_rows

def apply_filters(rows: List[Dict],
                  category: Optional[str],
                  subcategory: Optional[str]) -> List[Dict]:
    """
    Filter by category and subcategory if provided (exact, case-insensitive).
    """
    def match(val: Optional[str], needle: Optional[str]) -> bool:
        if not needle:
            return True
        return (val or "").strip().lower() == needle.strip().lower()

    filtered = []
    for r in rows:
        if match(r.get("category"), category) and match(r.get("subcategory"), subcategory):
            filtered.append(r)
    return filtered
