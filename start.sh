#!/bin/bash

APP_PID_FILE="app.pid"
LISTENER_PID_FILE="listener.pid"
WORKER_PID_FIRE="worker.pid"
LOG_FILE="app_start.log"


# --------------------------------
# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi


#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Clear old log files
echo "Clearing old log files..."
rm -f app.log app_start.log listener.log worker.log
echo "Logs cleared."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt



echo "Starting TeleFileDB..." | tee -a $LOG_FILE

# Start the Flask web application in the background
if [ -f $APP_PID_FILE ]; then
    echo "Web application is already running." | tee -a $LOG_FILE
else
    nohup python3 app.py > app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > $APP_PID_FILE
    echo "Web application started. PID: $APP_PID. Log file: app.log" | tee -a $LOG_FILE
fi

# Start the Telegram listener in the background
if [ -f $LISTENER_PID_FILE ]; then
    echo "Telegram listener is already running." | tee -a $LOG_FILE
else
    nohup python3 run_listener.py > listener.log 2>&1 &
    LISTENER_PID=$!
    echo $LISTENER_PID > $LISTENER_PID_FILE
    echo "Telegram listener started. PID: $LISTENER_PID. Log file: listener.log" | tee -a $LOG_FILE
fi


# Start the Telegram worker in the background
if [ -f $WORKER_PID_FIRE ]; then
    echo "Telegram worker is already running." | tee -a $LOG_FILE
else
    nohup python3 upload_worker.py > worker.log 2>&1 &
    WORKER_PID=$!
    echo $WORKER_PID > $WORKER_PID_FIRE
    echo "Telegram worker started. PID: $WORKER_PID. Log file: worker.log" | tee -a $LOG_FILE
fi

echo "TeleFileDB startup complete." | tee -a $LOG_FILE


