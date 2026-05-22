import asyncio
import html
from playwright.async_api import async_playwright

BOGO_URL = "https://www.publix.com/savings/weekly-ad/bogo"

# These keywords identify true "buy X get Y free" deals in the API response.
# The WeeklyAd endpoint mixes all deal types together, so we filter here.
BOGO_KEYWORDS = ("buy 1 get 1", "buy one get one", "bogo", "get one free", "get 1 free", "buy 2 get 1")


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
        # headless=False: run a visible browser so Akamai bot-detection passes
        browser = await p.chromium.launch(
            headless=False,
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

    print(f"\nFound {len(unique_bogo)} BOGO deal(s) (from {len(all_savings)} total weekly ad items):\n")
    print(f"{'#':<4} {'Deal':<20} {'Item'}")
    print("-" * 90)

    for i, item in enumerate(unique_bogo, 1):
        deal = clean(item.get("savings", ""))
        title = clean(item.get("title", "Unknown"))
        print(f"{i:<4} {deal:<20} {title}")


if __name__ == "__main__":
    asyncio.run(fetch_bogo_items())
