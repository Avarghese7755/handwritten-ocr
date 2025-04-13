"""
FILE       : vision_api.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755),
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-10
DESCRIPTION:
This module uses the Google Cloud Vision API to extract handwritten text from
uploaded images. It provides a utility function that performs OCR using the
document_text_detection endpoint.
"""


'''
    References: We have used the Google Vision API to extract text from images. The API is free to use and has a limit of 1000 requests per user
    The link to the API is given below: 
    - https://cloud.google.com/vision/docs/ocr
    - https://cloud.google.com/vision/docs/reference/rest/v1/images/annotate
'''


import os
import io
from google.cloud import vision

#  local credentials file when running locally
if os.getenv("GAE_ENV", "").startswith(""):  # Only set when running locally
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "lucid-diode-452919-p1-e5138e5e4227.json"

# FUNCTION   : extract_text
# DESCRIPTION: Extracts handwritten text from a given image using the
#              Google Cloud Vision API's document_text_detection feature.
# PARAMETERS : image_path (str) - Path to the image file to be processed
# RETURNS    : str - Extracted full text from the image

def extract_text(image_path):
    """Extracts handwritten text using Google Vision API."""
    client = vision.ImageAnnotatorClient()

    with io.open(image_path, "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise Exception(f"Vision API Error: {response.error.message}")

    return response.full_text_annotation.text
