"""
Uploads a rendered short to YouTube using the authenticated channel's
OAuth token (produced once by auth_setup.py).
"""
import os
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import YOUTUBE_TOKEN_PATH


def get_credentials():
    # Use the permissions the token actually has (from token.json). Asking
    # for more than it was granted would make the refresh fail.
    creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(YOUTUBE_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def get_authenticated_service(creds=None):
    return build("youtube", "v3", credentials=creds or get_credentials())


def upload_short(video_path, title, description, tags, category_id="27", youtube=None):
    """category_id 27 = Education (fits a facts channel); 22 = People & Blogs."""
    youtube = youtube or get_authenticated_service()

    # Ensure "#Shorts" is present so YouTube classifies it correctly
    if "#shorts" not in description.lower() and "#shorts" not in title.lower():
        description = f"{description}\n\n#Shorts"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "public",  # set to "private" while testing
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[upload] {int(status.progress() * 100)}% uploaded")

    video_id = response["id"]
    print(f"[upload] done: https://youtube.com/shorts/{video_id}")
    return video_id
