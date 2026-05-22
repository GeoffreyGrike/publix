#!/bin/bash

# Full environment setup for cron — macOS cron runs with a minimal shell
# that doesn't load .zshrc or .bash_profile, so paths must be set explicitly.

export HOME="/Users/geoffreygrike"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

REPO="/Users/geoffreygrike/Documents/IT/github/GeoffreyGrike/publix"

cd "$REPO" && "$REPO/.venv/bin/python3" "$REPO/bogo.py"
