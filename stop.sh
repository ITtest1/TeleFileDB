#!/bin/bash

APP_PID_FILE="app.pid"
LISTENER_PID_FILE="listener.pid"
WORKER_PID_FIRE="worker.pid"
# Stop the Flask web application
if [ -f $APP_PID_FILE ]; then
    APP_PID=$(cat $APP_PID_FILE)
    echo "Stopping web application with PID: $APP_PID"
    kill $APP_PID
    rm $APP_PID_FILE
    echo "Web application stopped."
else
    echo "Web application not running (no PID file found)."
fi

# Stop the Telegram listener
if [ -f $LISTENER_PID_FILE ]; then
    LISTENER_PID=$(cat $LISTENER_PID_FILE)
    echo "Stopping Telegram listener with PID: $LISTENER_PID"
    kill $LISTENER_PID
    rm $LISTENER_PID_FILE
    echo "Telegram listener stopped."
else
    echo "Telegram listener not running (no PID file found)."
fi

echo "TeleFileDB shutdown complete."

# Stop the Telegram worker
if [ -f $WORKER_PID_FIRE ]; then
    WORKER_PID=$(cat $WORKER_PID_FIRE)
    echo "Stopping Telegram listener with PID: $WORKER_PID"
    kill $WORKER_PID
    rm $WORKER_PID_FIRE
    echo "Telegram worker stopped."
else
    echo "Telegram worker not running (no PID file found)."
fi

echo "TeleFileDB shutdown complete."

