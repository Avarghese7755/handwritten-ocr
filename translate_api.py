"""
FILE       : translate_api.py
PROJECT    : Handwritten OCR | Capstone Project 2025
PROGRAMMER : Bhuwan Shrestha (8892146), Alen Varghese (8827755),
             Shubh Soni (8887735), Dev Patel (8866936)
DATE       : 2025-03-10
DESCRIPTION:
This module provides a helper function to translate text into different languages
using the Google Translate API through the `googletrans` library.
"""


'''
    References: We have used the Google Translate API to translate the text. The API is free to use and has a limit of 1000 requests per user. 
    The link to the API is given below: 
    - https://github.com/googletrans/googletrans
    - https://github.com/google/translate-python
'''
from googletrans import Translator

translator = Translator()


# FUNCTION   : translate_text
# DESCRIPTION: Translates the given text to the specified target language using
#              the Google Translate API via `googletrans`.
# PARAMETERS : text (str)         - The text to be translated
#              target_lang (str)  - Language code to translate into (default: "es")
# RETURNS    : str - Translated text or error message

def translate_text(text, target_lang="es"):
    """Translate text using Google Translate."""
    try:
        translated = translator.translate(text, dest=target_lang)
        return translated.text
    except Exception as e:
        return f"Translation Error: {str(e)}"
