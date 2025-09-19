#!/bin/bash
# This script cleans the project directory for public release.
# WARNING: This will permanently delete session files, logs, and the database.

echo "--- Cleaning project for release ---"

# Get the directory of the script itself
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR" || exit

echo "Removing Telegram session files (main and journal)..."
rm -f *.session*

echo "Removing database file..."
rm -f files.db

echo "Removing instance folder..."
rm -rf instance/*
touch instance/.gitignore

echo "Removing log files..."
rm -f *.log
rm -rf logs/*
touch logs/.gitignore

echo "Clearing file cache..."
# Keep the directory, but remove its contents. Add a .gitignore to keep the empty dir in git.
rm -rf cache/*
touch cache/.gitignore

echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

echo
echo "Cleanup complete. Your project is now cleaner for distribution."
echo "=================================================================="
echo "IMPORTANT:"
echo "1. Your personal .env file has NOT been touched, but make sure you DO NOT include it in your release package."
echo "2. Use the .env.example file as a template for new users."
echo "3. If you use Git, double-check your commit history for any accidentally committed sensitive data."
echo "=================================================================="
