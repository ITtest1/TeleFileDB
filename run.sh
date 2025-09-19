#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")"

# Graceful shutdown function
cleanup() {
    echo "Received stop signal, shutting down Flask app..."
    # The trap will propagate the signal to the exec'd process
    exit 0
}

trap cleanup SIGTERM SIGINT

echo "Starting Flask application..."
exec python3 app.py
