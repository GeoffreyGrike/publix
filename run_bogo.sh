#!/bin/bash

# Full environment setup for cron -- cron runs with a minimal shell
# that doesn't load .bashrc/.profile, so paths must be set explicitly.

export HOME="/home/pi"
export PATH="/usr/local/bin:/usr/bin:/bin"

REPO="/home/pi/publix"

cd "$REPO" && "$REPO/.venv/bin/python3" "$REPO/bogo.py"
