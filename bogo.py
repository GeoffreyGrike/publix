import asyncio
import csv
import html
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from pyanylist import AnyListClient

load_dotenv(Path(__file__).parent / ".env")  # loads ANYLIST_EMAIL, ANYLIST_PASSWORD, ANYLIST_LIST_NAME from .env

BOGO_URL = "https://www.publix.com/savings/weekly-ad/bogo"

# These keywords identify true "buy X get Y free" deals in the API response.
# The WeeklyAd endpoint mixes all deal types together, so we filter here.
BOGO_KEYWORDS = ("buy 1 get 1", "buy one get one", "bogo", "get one free", "get 1 free", "buy 2 get 1")

# Items to mark as favorites — matched case-insensitively against the item title
FAVORITES = (
    "Fresh Express Salad Blends",
    "Tomato Medley",
    "Sabra Hummus",
    "Cabot Cheese Bar",
    "Nutty & Fruity Mango",
    "Calbee Harvest Snaps Snacks",
    "Pretzilla Soft Pretzel Bites",
    "12-Pack Landshark Island Style Lager",
    "6-Pack Shock Top",
)


def is_favorite(title: str) -> bool:
    """Return True if the item title matches any entry in FAVORITES."""
    title_lower = title.lower()
    return any(fav.lower() in title_lower for fav in FAVORITES)


def is_bogo(item: dict) -> bool:
    """Return True if the item is a true BOGO deal."""
    combined = " ".join([
        (item.get("savings") or ""),
        (item.get("title") or ""),
        (item.get("description") or ""),
    ]).lower()
    return any(kw in combined for kw in BOGO_KEYWORDS)


def clean(text: str) -> str:
    """Decode HTML entities (e.g. &reg; → ®) and strip whitespace."""
    return html.unescape(text or "").strip()


async def fetch_bogo_items():
    all_savings = []

    async with async_playwright() as p:
        # headless=True: run without a visible browser window
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        # Hide the webdriver flag that sites use to detect automation
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        # Capture every response from the weekly ad savings API.
        # The browser automatically sends a `publixstore` header with the store number,
        # which is what unlocks the full weekly ad data (vs. just digital coupons).
        async def handle_response(response):
            if "api/v4/savings" in response.url and "WeeklyAd" in response.url:
                try:
                    data = await response.json()
                    batch = data.get("Savings", [])
                    if batch:
                        all_savings.extend(batch)
                        print(f"  Captured {len(batch)} items (total so far: {len(all_savings)})")
                except Exception:
                    pass

        page.on("response", handle_response)

        print(f"Loading {BOGO_URL} ...")
        try:
            await page.goto(BOGO_URL, wait_until="domcontentloaded", timeout=90000)
        except Exception:
            pass  # continue even if the load event times out

        # Dismiss Club Publix popup if it appears
        await asyncio.sleep(2)
        try:
            close_btn = page.locator("button[aria-label='Close']").first
            if await close_btn.is_visible(timeout=3000):
                await close_btn.click()
        except Exception:
            pass

        # Scroll slowly so the page triggers lazy-loaded API calls for each batch
        print("Scrolling to load all items...")
        for _ in range(30):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)

        await asyncio.sleep(3)
        await browser.close()

    if not all_savings:
        print("No data captured — the site may be down or the page structure changed.")
        return

    # Filter down to true BOGO deals
    bogo_items = [s for s in all_savings if is_bogo(s)]

    # De-duplicate by title in case multiple scroll events returned the same item
    seen = set()
    unique_bogo = []
    for item in bogo_items:
        key = item.get("title", "")
        if key not in seen:
            seen.add(key)
            unique_bogo.append(item)

    # Load previous run's items to detect what's new this week
    downloads_dir = Path(__file__).parent / "downloads"
    previous_items = set()
    previous_files = sorted(downloads_dir.glob("publix_bogo_*.csv"))
    if previous_files:
        with open(previous_files[-1], newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                previous_items.add(row.get("Item", "").strip())
        print(f"Comparing against previous run: {previous_files[-1].name}")

    # Sort: favorites first, then alphabetically by department
    unique_bogo.sort(key=lambda x: (
        not is_favorite(clean(x.get("title", ""))),
        clean(x.get("department", "")).lower()
    ))

    print(f"\nFound {len(unique_bogo)} BOGO deal(s) (from {len(all_savings)} total weekly ad items):\n")
    print(f"{'Item':<45} {'Department':<25} {'Fav':<5} {'New':<5} {'Save Up To':<12} {'Valid'}")
    print("-" * 115)

    for item in unique_bogo:
        title = clean(item.get("title", "Unknown"))
        save_up_to = clean(item.get("additionalDealInfo", "")).replace("SAVE UP TO ", "").replace("Save Up To ", "")
        valid = f"{item.get('wa_startDateFormatted', '')} - {item.get('wa_endDateFormatted', '')}"
        fav = "★" if is_favorite(title) else ""
        department = clean(item.get("department", ""))
        # Mark as new if no previous file existed or item wasn't in previous run
        new = "🆕" if previous_items and title not in previous_items else ""
        print(f"{title:<45} {department:<25} {fav:<5} {new:<5} {save_up_to:<12} {valid}")

    # Save results to a CSV in the repo's downloads folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = downloads_dir / f"publix_bogo_{timestamp}.csv"
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        # QUOTE_ALL ensures every field is quoted, so spreadsheet apps parse columns correctly
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Item", "Department", "Favorite", "New", "Save Up To", "Valid"])
        for item in unique_bogo:
            title = clean(item.get("title", "Unknown"))
            save_up_to = clean(item.get("additionalDealInfo", "")).replace("SAVE UP TO ", "").replace("Save Up To ", "")
            valid = f"{item.get('wa_startDateFormatted', '')} - {item.get('wa_endDateFormatted', '')}"
            department = clean(item.get("department", ""))
            new = "Yes" if previous_items and title not in previous_items else ""
            writer.writerow([title, department, "Yes" if is_favorite(title) else "", new, save_up_to, valid])

    print(f"\nSaved to {output_path}")

    # Add new favorite BOGO items to AnyList automatically
    await sync_favorites_to_anylist(unique_bogo, previous_items)


async def sync_favorites_to_anylist(items: list, previous_items: set):
    """Add new favorite BOGO items to AnyList.

    Only adds items that are both a favorite AND new this week (not in the
    previous run), so the list isn't flooded with duplicates on every run.
    On the very first run (no previous file), all current favorites are added.
    """
    email = os.getenv("ANYLIST_EMAIL")
    password = os.getenv("ANYLIST_PASSWORD")
    list_name = os.getenv("ANYLIST_LIST_NAME", "Groceries")

    if not email or not password:
        print("\nAnyList credentials not set — skipping AnyList sync.")
        print("Add ANYLIST_EMAIL and ANYLIST_PASSWORD to .env to enable.")
        return

    # Collect favorites that are new this week, keeping the full item dict for details
    to_add = [
        item for item in items
        if is_favorite(clean(item.get("title", "")))
        and (not previous_items or clean(item.get("title", "")) not in previous_items)
    ]

    if not to_add:
        print("\nNo new favorite BOGO items to add to AnyList.")
        return

    print(f"\nSyncing {len(to_add)} new favorite(s) to AnyList list '{list_name}'...")
    try:
        client = AnyListClient.login(email, password)
        try:
            grocery_list = client.get_list_by_name(list_name)
        except Exception:
            grocery_list = client.create_list(list_name)
            print(f"  Created new AnyList list: '{list_name}'")

        # Get names already on the list to avoid duplicates
        existing = {i.name.lower() for i in grocery_list.items}

        for item in to_add:
            title = clean(item.get("title", ""))
            save_up_to = clean(item.get("additionalDealInfo", "")).replace("SAVE UP TO ", "").replace("Save Up To ", "")
            valid = f"{item.get('wa_startDateFormatted', '')} - {item.get('wa_endDateFormatted', '')}"
            # Note added to the item so it's clearly identifiable as a BOGO in the grocery list
            note = f"BOGO – {save_up_to} | Valid {valid}"

            if title.lower() in existing:
                print(f"  Skipped (already on list): {title}")
            else:
                client.add_item_with_details(grocery_list.id, title, details=note)
                print(f"  Added: {title} ({note})")

    except Exception as e:
        print(f"  AnyList sync failed: {e}")


if __name__ == "__main__":
    asyncio.run(fetch_bogo_items())
