# Publix BOGO Scraper

Fetches the current week's Buy One Get One (BOGO) deals from the Publix weekly ad and saves them to a CSV file.

---

## What it does

Each time the script runs it:

1. Opens a headless Chromium browser (invisible — no window appears)
2. Navigates to the Publix weekly ad BOGO page
3. Captures the API response that the page fetches in the background — this includes all 730+ weekly ad items for the configured store
4. Filters that list down to true BOGO deals (Buy 1 Get 1 Free, Buy 2 Get 1 Free, etc.)
5. Removes duplicates and sorts results — favorites first (alphabetically by department), then the rest (alphabetically by department)
6. Prints the results to the terminal
7. Saves a timestamped CSV file to the `downloads/` folder

---

## Why a browser instead of a direct API call

The Publix weekly ad API (`services.publix.com`) is protected by Akamai bot detection. Direct HTTP requests (e.g. with `curl` or Python `requests`) are blocked with a 403. A real Chromium browser passes that check automatically and also sends the required `publixstore` header that unlocks store-specific weekly ad data.

---

## Output

### Terminal
```
Item                                          Department                Fav   Save Up To   Valid
---------------------------------------------------------------------------------------------------------
Tomato Medley                                 Produce                   ★     $5.15        5/21 - 5/27
Fresh Express Salad Blends                    Produce                   ★     $5.65        5/21 - 5/27
Mt. Olive Pickles                             Pickles & Olives                $4.75        5/21 - 5/27
...
```

### CSV
Saved to `downloads/publix_bogo_YYYY-MM-DD_HH-MM-SS.csv` with columns:

| Column | Description |
|--------|-------------|
| Item | Product name |
| Department | Store section (e.g. Produce, Meat, Deli) |
| Favorite | "Yes" if the item is in your favorites list |
| Save Up To | Maximum savings amount |
| Valid | Deal date range (e.g. 5/21 - 5/27) |

A new file is created on every run so previous results are never overwritten.

---

## Setup

**Requirements:** Python 3.x, pip

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install playwright

# 3. Install the Chromium browser
playwright install chromium
```

---

## Usage

```bash
source .venv/bin/activate
python3 bogo.py
```

---

## Favorites

To mark items as favorites (they appear at the top of the list with a ★), edit the `FAVORITES` list near the top of `bogo.py`:

```python
FAVORITES = (
    "Fresh Express Salad Blends",
    "Tomato Medley",
    "Sabra Hummus",
    # add more items here...
)
```

Matching is case-insensitive and partial — `"Shock Top"` will match `"6-Pack Shock Top Beer"`.
