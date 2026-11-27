"""
After a video is uploaded:
1. Adds it to a topic playlist (creating the playlist the first time), so
   viewers who like one video can binge more like it.
2. Posts a question as a comment to get the comments going.

Both need the "manage your YouTube account" permission
(youtube.force-ssl). If the saved token doesn't include it yet, this
module skips quietly: re-run auth_setup.py and update the YOUTUBE_TOKEN
secret to switch it on. Nothing here can stop a video from posting.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MANAGE_SCOPE
from trends import base_topic

# First matching rule wins, so more specific themes come first.
PLAYLISTS = [
    ("Ocean Mysteries", ["ocean", "sea", "underwater", "deep-sea"],
     "The strangest things hiding in the deep."),
    ("Space & Physics", ["space", "universe", "black hole", "light or time", "physics", "speed, time"],
     "Mind-bending facts about the universe and how it works."),
    ("Ancient Secrets & Lost Civilizations", ["ancient", "lost civilization", "decoding", "how old"],
     "Lost worlds, ancient tech and mysteries that took centuries to solve."),
    ("History's Strangest Stories", ["histor", "war", "cold war", "day in history", "near-disaster", "decision saved"],
     "True stories from history that sound made up."),
    ("Animal Oddities", ["animal"],
     "Animal abilities and behaviors that sound fake but are real."),
    ("Mind & Body", ["brain", "psycholog", "cognitive", "memory", "sleep", "human body", "sense", "survival"],
     "Surprising facts about how your brain and body really work."),
    ("Science Surprises", ["scien", "invention", "technology", "mathemat", "pattern", "phenomenon", "theory", "natural event"],
     "Discoveries, inventions and science that sound impossible."),
]
DEFAULT_PLAYLIST = ("Weird World Facts", "Strange but true facts about our world.")


def playlist_for(topic: str):
    t = base_topic(topic).lower()
    for title, keywords, desc in PLAYLISTS:
        if any(k in t for k in keywords):
            return title, desc
    return DEFAULT_PLAYLIST


def has_manage_permission(creds) -> bool:
    return MANAGE_SCOPE in (creds.scopes or [])


def _find_or_create_playlist(youtube, title, description):
    page_token = None
    while True:
        resp = youtube.playlists().list(
            part="snippet", mine=True, maxResults=50, pageToken=page_token
        ).execute()
        for item in resp.get("items", []):
            if item["snippet"]["title"] == title:
                return item["id"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    created = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    print(f"[engagement] created playlist '{title}'")
    return created["id"]


def after_upload(youtube, creds, video_id, topic, question):
    if not has_manage_permission(creds):
        print(
            "[engagement] skipped playlist + comment: the YouTube token doesn't "
            "have permission yet (re-run auth_setup.py and update YOUTUBE_TOKEN)."
        )
        return

    try:
        title, desc = playlist_for(topic)
        playlist_id = _find_or_create_playlist(youtube, title, desc)
        youtube.playlistItems().insert(
            part="snippet",
            body={"snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }},
        ).execute()
        print(f"[engagement] added to playlist '{title}'")
    except Exception as e:
        print(f"[engagement] playlist step failed (video is still posted): {e}")

    if question:
        try:
            youtube.commentThreads().insert(
                part="snippet",
                body={"snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": question[:300]}},
                }},
            ).execute()
            print("[engagement] posted question comment")
        except Exception as e:
            print(f"[engagement] comment step failed (video is still posted): {e}")
