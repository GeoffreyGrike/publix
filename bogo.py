import html      # standard library: converts HTML entities like &amp; → &
import requests  # third-party: makes HTTP requests (like a browser fetching a URL)

# The Publix internal API endpoint that powers the weekly ad savings page.
# Query parameters:
#   smImg / enImg      - image sizes to return (we don't use images, but required)
#   page / pageSize    - pagination; pageSize=0 returns all items at once
#   getSavingType=BOGO - filters the response to the BOGO/coupons section
API_URL = (
    "https://services.publix.com/api/v4/savings"
    "?smImg=235&enImg=368&fallbackImg=false&isMobile=false"
    "&page=1&pageSize=0&includePersonalizedDeals=false"
    "&languageID=1&isWeb=true&getSavingType=BOGO"
)

# HTTP headers sent with the request so the Publix server treats us like a browser.
#   User-Agent - identifies the "browser" making the request
#   Referer    - tells the server which page we're "coming from"
#   Accept     - tells the server we want JSON back, not HTML
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.publix.com/savings/weekly-ad/bogo",
    "Accept": "application/json",
}

# The API returns ALL savings types (coupons, spend-and-save, etc.) mixed in together.
# These keywords help us identify the true "buy X get Y free" deals.
BOGO_KEYWORDS = ("buy 1 get 1", "buy one get one", "bogo", "get one free", "get 1 free")


def is_bogo(item: dict) -> bool:
    """Return True if any BOGO keyword appears anywhere in the item's text fields."""
    # Combine all text fields into one lowercase string so we only need one search pass
    combined = " ".join([
        (item.get("savings") or ""),      # e.g. "Buy 1 Get 1 Free"
        (item.get("title") or ""),        # e.g. "Coca-Cola 20oz"
        (item.get("description") or ""),  # longer deal description
    ]).lower()
    return any(kw in combined for kw in BOGO_KEYWORDS)


def clean(text: str) -> str:
    """Decode HTML entities and strip whitespace from a string.

    The API returns raw HTML in some fields, e.g. "Alani Nu&reg;" instead of "Alani Nu®".
    html.unescape() converts those back to readable characters.
    """
    return html.unescape(text or "").strip()


def main():
    print("Fetching Publix BOGO deals...")

    # Make the GET request; raise_for_status() will throw an error if the
    # server returns anything other than a 200 OK (e.g. 404, 500)
    resp = requests.get(API_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    # The JSON response looks like: { "Savings": [ {...}, {...}, ... ] }
    savings = resp.json().get("Savings", [])

    # Filter the full list down to only the true BOGO deals
    bogo_items = [s for s in savings if is_bogo(s)]

    if not bogo_items:
        print("No BOGO items found — the page may have changed.")
        return

    print(f"\nFound {len(bogo_items)} BOGO deal(s) (of {len(savings)} total savings):\n")

    # Print a fixed-width table; the numbers in :<4 and :<20 set column widths
    print(f"{'#':<4} {'Deal':<20} {'Item'}")
    print("-" * 90)

    for i, item in enumerate(bogo_items, 1):
        deal = clean(item.get("savings", ""))   # short label, e.g. "Buy 1 Get 1 Free"
        title = clean(item.get("title", "Unknown"))  # item name
        print(f"{i:<4} {deal:<20} {title}")


# Only run main() when this file is executed directly (not when imported as a module)
if __name__ == "__main__":
    main()
