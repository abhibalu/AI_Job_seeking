"""Test script: Create a folder inside OtooCV on Google Drive."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.google_docs import get_credentials
from googleapiclient.discovery import build

OTOOCV_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "16AQxe1HlSRl_8HjX69PYuR0Je5YUzbGK")

creds = get_credentials()
if not creds:
    print("Auth failed")
    sys.exit(1)

drive = build('drive', 'v3', credentials=creds)

# Create a test folder inside OtooCV
folder_metadata = {
    'name': 'Test Company Folder',
    'mimeType': 'application/vnd.google-apps.folder',
    'parents': [OTOOCV_FOLDER_ID]
}

folder = drive.files().create(body=folder_metadata, fields='id,name,webViewLink').execute()
print(f"Created folder: {folder['name']}")
print(f"ID: {folder['id']}")
print(f"Link: {folder.get('webViewLink', 'N/A')}")
