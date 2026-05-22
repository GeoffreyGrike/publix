# Publix BOGO Scraper

Fetches the current week's Buy One Get One (BOGO) deals from the Publix weekly ad, saves them to a CSV file, and automatically adds new favorite items to an AnyList grocery list.

---

## What it does

Each time the script runs it:

1. Opens a headless Chromium browser (invisible — no window appears)
2. Navigates to the Publix weekly ad BOGO page
3. Captures the API response that the page fetches in the background — this includes all 730+ weekly ad items for the configured store
4. Filters that list down to true BOGO deals (Buy 1 Get 1 Free, Buy 2 Get 1 Free, etc.)
5. Removes duplicates and sorts results — favorites first (alphabetically by department), then the rest (alphabetically by department)
6. Compares results against the most recent previous CSV to identify new items
7. Automatically adds any new favorite items to an AnyList grocery list with a BOGO note
8. Prints the results to the terminal
9. Saves a timestamped CSV file to the `downloads/` folder

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
| New | "Yes" if the item was not present in the previous run's CSV |
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
pip install playwright pyanylist python-dotenv

# 3. Install the Chromium browser
playwright install chromium

# 4. Create your .env file (see AnyList Integration below)
cp .env.example .env
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

---

## AnyList Integration

When a new favorite BOGO item appears (i.e. it wasn't in the previous run's CSV), the script automatically adds it to your AnyList grocery list. Each item includes a note with the savings amount and valid dates so it's easy to identify as a BOGO deal:

```
Fresh Express Salad Blends
BOGO – $5.65 | Valid 5/21 - 5/27
```

### Setup

Copy `.env.example` to `.env` and fill in your credentials:

```
ANYLIST_EMAIL=your@email.com
ANYLIST_PASSWORD=yourpassword
ANYLIST_LIST_NAME=Groceries
```

- `ANYLIST_EMAIL` / `ANYLIST_PASSWORD` — your AnyList login credentials
- `ANYLIST_LIST_NAME` — the name of the list to add items to (must already exist in AnyList)

The `.env` file is excluded from git so your credentials are never committed.

If credentials are not set, the script skips the AnyList sync and prints a reminder.

---

## Schedule

The script runs automatically every day at **9:00 AM ET** via a cron job installed on this machine:

```
0 9 * * * cd /path/to/publix && .venv/bin/python3 bogo.py >> downloads/bogo.log 2>&1
```

Each run compares its results against the most recent CSV in `downloads/`. Any item that wasn't in the previous run is marked **New = Yes**, making it easy to spot deals that just started. Logs from each run are appended to `downloads/bogo.log`.

To view or edit the cron schedule:

```bash
crontab -e
```
