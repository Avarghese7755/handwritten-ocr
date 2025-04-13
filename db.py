"""
FILE       : db.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755),
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-15
DESCRIPTION:
Provides a utility function to establish a PostgreSQL database connection.
Automatically switches between local and Google Cloud SQL based on environment
"""
import os
import psycopg2


# FUNCTION   : get_db_connection
# DESCRIPTION: Returns a database connection object based on the environment—
#              local development or Google Cloud Run deployment
# PARAMETERS : None
# RETURNS    : psycopg2 connection object

def get_db_connection():
    if os.getenv("K_SERVICE"):  
        return psycopg2.connect(
            dbname="handwritten_ocr",
            user="postgres",
            password="myPassword123",
            host="/cloudsql/lucid-diode-452919-p1:us-central1:ocr-postgres-db"
        )
    else:  # Running locally
        return psycopg2.connect(
            dbname="handwritten_ocr",
            user="postgres",
            password="myPassword123",
            host="127.0.0.1",
            port="5432"
        )
