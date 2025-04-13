# Use the official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed by psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first 
COPY requirements.txt .

# Install Python dependencies (like psycopg2-binary)
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the full app after dependencies
COPY . .

# Remove unwanted folders
RUN rm -rf user_logs uploads tests

# Set environment variable
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run the application
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
