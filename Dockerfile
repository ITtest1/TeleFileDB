
# Use an official Python runtime as a parent image
FROM python:3.9-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies, build, and cleanup in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libssl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove build-essential libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

# Make the entrypoint script executable
RUN chmod +x run.sh

# Expose the port the app runs on
EXPOSE 5000

# Define environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the application
CMD ["./run.sh"]
