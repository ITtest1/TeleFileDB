#!/bin/bash

# Start Flask app in the background
python3 app.py > app.log 2>&1 &

# Start Telegram listener in the background
python3 telegram_listener.py > listener.log 2>&1 &

# Start Upload worker in the background (if upload_worker.py exists and is needed)
# Check if upload_worker.py exists before trying to run it
if [ -f "upload_worker.py" ]; then
    python3 upload_worker.py > worker.log 2>&1 &
fi

# Keep the container running
tail -f app.log listener.log worker.log
