"""
FILE       : config.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755),
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-15
DESCRIPTION:
This configuration file sets up constants for file uploads, allowed image types,
and the database connection string for the Handwritten OCR Flask application
"""
import os

UPLOAD_FOLDER = "static/uploads/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
DATABASE_URL = "postgresql+psycopg2://postgres:myPassword123@/handwritten_ocr?host=/cloudsql/lucid-diode-452919-p1:us-central1:ocr-postgres-db"



if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)