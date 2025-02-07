import logging
import os
from typing import List, Literal
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.discovery import Resource
from googleapiclient.http import MediaFileUpload
from .logger import setup_logger

logger = setup_logger(__name__)

# Set up constants
MEOW_PATH = os.path.dirname(os.path.abspath(__name__))
CLIENT_SECRETS_FILE = os.path.join(MEOW_PATH, "google_oauth.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def get_authenticated_service() -> Resource:
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_console()
    return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


privacy_status = Literal["private", "public", "unlisted"]

def upload_video(video_file: str, title: str, description: str, tags: List[str], category_id: int = 17, privacy_status: privacy_status = "public"):

    logger.info("Starting video upload")

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            # 17 is Sports category
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    response = request.execute()
    return response
