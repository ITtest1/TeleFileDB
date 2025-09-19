#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")"

# --- Step 1: Virtual Environment and Dependencies ---
echo "Step 1: Setting up virtual environment and installing dependencies..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# --- Step 2: Docker Services ---
echo "Step 2: Starting MySQL and Adminer services..."

cd mysql_docker
# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null
then
    # Check if docker compose (with a space) is available
    if ! command -v docker compose &> /dev/null
    then
        echo "Error: Neither 'docker-compose' nor 'docker compose' could be found."
        echo "Please install Docker Compose and try again."
        exit 1
    fi
    # Use "docker compose" syntax
    docker compose up -d
else
    # Use "docker-compose" syntax
    docker-compose up -d
fi
cd ..

# --- Step 3: Wait for MySQL to be ready ---
echo "Step 3: Waiting for MySQL database to be ready..."

# Read .env file to get database credentials
set -o allexport
source .env
set +o allexport

retries=30
while ! mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD -e "SELECT 1" &> /dev/null; do
    retries=$((retries-1))
    if [ $retries -eq 0 ]; then
        echo "Error: MySQL database is not ready after 30 seconds. Please check the docker logs in the mysql_docker directory."
        exit 1
    fi
    echo "Waiting for MySQL... ($retries retries left)"
    sleep 1
done

echo "MySQL is ready."

# --- Step 4: Initialize Database and Create Admin ---
echo "Step 4: Initializing database schema and creating admin user..."

flask init-db
flask create-admin

# --- Completion ---
echo "
Setup Complete!

Next Steps:
1. The MySQL database and Adminer are running in the background.
2. You can now start the main application by running: ./run.sh
3. Access the web application at http://<your_server_ip>:5000
4. Access the Adminer database manager at http://<your_server_ip>:8080
"