#!/bin/bash

# Full environment setup for cron -- cron runs with a minimal shell
# that doesn't load .bashrc/.profile, so paths must be set explicitly.

export HOME="/home/pi"
export PATH="/usr/local/bin:/usr/bin:/bin"

REPO="/home/pi/publix"

cd "$REPO" || exit 1

# Pick up any favorites.txt (or other) changes pushed to GitHub since the last run.
# Non-fatal: if the pull fails (e.g. no network), fall through and run with what's on disk.
git pull --ff-only || echo "git pull failed, continuing with existing local copy" >&2

"$REPO/.venv/bin/python3" "$REPO/bogo.py"
