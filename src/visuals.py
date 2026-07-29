"""
Fetches free-to-use stock video clips from Pexels matching the script's
visual keywords. Pexels footage is free for commercial use including
monetized YouTube content (see pexels.com/license).
"""
import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PEXELS_API_KEY

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


def fetch_clip_for_keyword(keyword: str, orientation="portrait", min_duration=3):
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "orientation": orientation, "per_page": 5}

    resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])

    for video in videos:
        if video.get("duration", 0) < min_duration:
            continue
        # pick the highest-res portrait file available
        files = sorted(
            video["video_files"],
            key=lambda f: f.get("height", 0),
            reverse=True,
        )
        for f in files:
            if f.get("width", 9999) <= f.get("height", 0):  # portrait-ish
                return f["link"]
        if files:
            return files[0]["link"]

    return None


def download_clips(keywords: list, out_dir: str) -> list:
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    for i, kw in enumerate(keywords):
        url = fetch_clip_for_keyword(kw)
        if not url:
            print(f"[visuals] no clip found for '{kw}', skipping")
            continue

        path = os.path.join(out_dir, f"clip_{i}.mp4")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        paths.append(path)
        print(f"[visuals] downloaded clip for '{kw}' -> {path}")

    return paths


if __name__ == "__main__":
    clips = download_clips(["ocean waves aerial", "city timelapse night"], "test_clips")
    print(clips)
