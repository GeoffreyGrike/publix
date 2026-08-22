# Publix BOGO Scraper

Fetches the current week's Buy One Get One (BOGO) deals from the Publix weekly ad, saves them to a CSV file, and syncs your favorite items to an AnyList grocery list.

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
8. Syncs every current favorite BOGO item to an AnyList grocery list (see [AnyList Integration](#anylist-integration))

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

To mark items as favorites (they appear at the top of the list with a ★), edit `favorites.txt` — one item per line:

```text
Fresh Express Salad Blends
Tomato Medley
Sabra Hummus
# add more items here...
```

Lines starting with `#` are treated as comments and ignored. Matching is case-insensitive and partial — `"Shock Top"` will match `"6-Pack Shock Top Beer"`.

Changes to `favorites.txt` take effect immediately on the next run — no script edits needed.

---

## AnyList Integration

Every run, the script syncs **all current favorite BOGO items** (not just newly-appeared ones) to your AnyList grocery list. For each favorite item still on BOGO this week, one of three things happens:

| State on AnyList | Action |
|---|---|
| Not on the list | Added, with a note of `BOGO` so it's easy to spot |
| On the list, active | Left alone |
| On the list, crossed off | Un-checked, so it shows back up as active |

The un-check behavior handles the common case where you buy something, cross it off in AnyList, and it's still on BOGO the following week(s) — the item comes back automatically instead of staying stuck as crossed-off, or getting duplicated if you'd deleted it.

Note: the AnyList library this script uses (`pyanylist`) can't read or write item photos, and can't update an existing item's note in place. So un-checking an item preserves any photo/category you attached to it, but its note stays exactly as it was set when first added — which is why the note is just the static text `BOGO` rather than that week's price/dates (those would go stale the first time an item got revived from crossed-off).

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

Publix's weekly ad refreshes on Thursdays, so the script runs automatically every **Thursday at 7:00 AM** via a cron job installed on this machine:

```
0 7 * * 4 /home/pi/publix/run_bogo.sh >> /home/pi/publix/downloads/bogo.log 2>&1
```

Cron runs jobs with a minimal shell that doesn't load `.bashrc`/`.profile`, so `run_bogo.sh` explicitly sets `HOME`, `PATH`, and the repo path before invoking `bogo.py` with the venv's Python. Logs from each run are appended to `downloads/bogo.log`.

You can also run `./run_bogo.sh` manually any time — e.g. to pick up favorites you crossed off or deleted in AnyList — since every run re-syncs the full current favorites list, not just newly-appeared items.

To view or edit the cron schedule:

```bash
crontab -e
```
