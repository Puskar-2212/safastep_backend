import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Twilio credentials - Load from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

# Base URL - Update this with your ngrok URL when using ngrok
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# Upload directory
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
