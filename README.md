Handwritten OCR | Capstone Project 2025

This project is a web-based Handwritten OCR system developed as a capstone project by students from the Software Engineering Technology program. The system allows users to upload handwritten image files and extract text using Google Cloud Vision API. It supports multiple features including text translation, editing, download options, history tracking, user feedback, and account management.

The frontend is styled using Tailwind CSS with support for dark/light mode. The backend is built with Flask and uses PostgreSQL as the database. The application is deployed on Google Cloud Run using Docker.

Project Features

- Upload handwritten images (multiple formats)
- Extract handwritten text using Google Cloud Vision API
- Edit extracted text using CKEditor
- Translate extracted text into different languages using Google Translate API
- Copy text to clipboard
- Download as .txt, .pdf, or .docx
- Track upload and translation history
- User authentication with email verification
- Enable or disable 2FA
- View session logs and activity
- Submit feedback via star rating and comments
- Settings page for analytics, language preferences, and notifications
- Responsive design with dark mode toggle

Prerequisites

To run the application locally, you must have:

- Python 3.9 or later
- PostgreSQL installed and running
- pip and virtualenv installed
- Google Cloud SDK (for deployment)
- A Google Cloud project with the following APIs enabled:
  - Google Cloud Vision API
  - Google Cloud Run Admin API
  - Cloud SQL Admin API
  - Artifact Registry API
  - IAM & Service Accounts API
  - Cloud Build API
  - Cloud Logging API

Local Setup Instructions

1. Clone the Repository

git clone https://github.com/Avarghese7755/handwritten-ocr.git
cd handwritten-ocr

2. Create a PostgreSQL Database

Start PostgreSQL and create a database named handwritten_ocr.

CREATE DATABASE handwritten_ocr;

Then run the following script to create necessary tables:

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    gmail TEXT UNIQUE NOT NULL,
    verified INTEGER DEFAULT 0
);

CREATE TABLE history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    image TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    analytics INTEGER,
    notifications INTEGER,
    language TEXT
);

CREATE TABLE user_2fa (
    user_id INTEGER PRIMARY KEY,
    enabled INTEGER,
    secret TEXT
);

CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id TEXT,
    ip_address TEXT,
    device_info TEXT,
    last_active TIMESTAMP
);

CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    rating INTEGER,
    comment TEXT
);

3. Set up the Python Virtual Environment

python -m venv venv
venv\Scripts\activate        (For Windows)
source venv/bin/activate     (For macOS/Linux)

pip install -r requirements.txt

4. Add Google Vision Credentials

Place your service account JSON file (e.g. lucid-diode-452919-p1-e5138e5e4227.json) in the project root and set the environment variable:

GOOGLE_APPLICATION_CREDENTIALS=lucid-diode-452919-p1-e5138e5e4227.json

5. Run the App Locally

flask run

Then open your browser and go to:

http://127.0.0.1:5000/

Deployment Instructions (Google Cloud Run)

The app is containerized using Docker and deployed to Google Cloud Run using Google Cloud Build.

1. Build the Docker Image

gcloud builds submit --tag us-central1-docker.pkg.dev/lucid-diode-452919-p1/ocr-app-repo/ocr-app

2. Deploy to Google Cloud Run

gcloud run deploy ocr-app --image=us-central1-docker.pkg.dev/lucid-diode-452919-p1/ocr-app-repo/ocr-app:latest --platform=managed --region=us-central1 --allow-unauthenticated --add-cloudsql-instances=lucid-diode-452919-p1:us-central1:ocr-postgres-db --memory=2Gi

Make sure you configure your app to use Unix socket connection for Google Cloud SQL when running in Cloud Run.

API Services Used

The following Google APIs and services are used in this project:

- Google Cloud Vision API - for extracting handwritten text from images
- Google Translate API - for translating extracted text
- Google Cloud Run - serverless deployment of the web app
- Google Cloud Build - container image build and push
- Google Artifact Registry - storage for container images
- Google Cloud SQL - managed PostgreSQL instance
- Identity and Access Management (IAM) - service account permissions
- Cloud Logging - centralized logging for app activities


Authors


Alen Varghese (Student ID: 8827755)
Bhuwan Shrestha (Student ID: 8892146)
Shubh Soni (Student ID: 8887735)
Dev Patel (Student ID: 8866936)

Course: Systems Project
Program: Software Engineering Technology
Institution: Conestoga College
Year: 2025

License

This project is developed for educational purposes as part of an academic capstone
