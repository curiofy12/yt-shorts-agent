"""
Fetches free-to-use stock video clips from Pexels matching the script's
visual keywords. Pexels footage is free for commercial use including
monetized YouTube content (see pexels.com/license).
"""
import os
import random
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PEXELS_API_KEY

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


TARGET_HEIGHT = 1920  # our output height; anything bigger just slows rendering


def _best_file(files):
    """
    Pick the smallest portrait file that's still at least full-HD tall.
    4K files look no better in a 1080x1920 Short but render several times
    slower, so we avoid them.
    """
    portrait = [f for f in files if f.get("height", 0) >= f.get("width", 1)]
    pool = portrait or files
    big_enough = [f for f in pool if f.get("height", 0) >= TARGET_HEIGHT]
    if big_enough:
        return min(big_enough, key=lambda f: f.get("height", 0))
    return max(pool, key=lambda f: f.get("height", 0)) if pool else None


def fetch_clip_for_keyword(keyword: str, used_ids: set, orientation="portrait", min_duration=3):
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "orientation": orientation, "per_page": 10}

    resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    top = videos[:5]
    random.shuffle(top)  # a little variety between videos on similar topics
    videos = top + videos[5:]

    for video in videos:
        if video.get("duration", 0) < min_duration or video.get("id") in used_ids:
            continue
        f = _best_file(video.get("video_files", []))
        if f:
            used_ids.add(video.get("id"))
            return f["link"]

    return None


def download_clips(keywords: list, out_dir: str) -> list:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    used_ids = set()

    for i, kw in enumerate(keywords):
        url = fetch_clip_for_keyword(kw, used_ids)
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


def download_beat_clips(searches: list, out_dir: str) -> list:
    """
    One clip per beat, in order. Returns a list the same length as
    `searches`; a beat whose search found nothing gets None (the assembler
    then reuses a neighbouring clip).
    """
    os.makedirs(out_dir, exist_ok=True)
    used_ids, paths = set(), []
    for i, kw in enumerate(searches):
        path = None
        try:
            url = fetch_clip_for_keyword(kw, used_ids)
            if not url:
                # Try a simpler search: the last two words usually name the subject
                url = fetch_clip_for_keyword(" ".join(kw.split()[-2:]), used_ids)
            if url:
                path = os.path.join(out_dir, f"clip_{i:02d}.mp4")
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                with open(path, "wb") as f:
                    f.write(r.content)
                print(f"[visuals] beat {i + 1}: '{kw}'")
            else:
                print(f"[visuals] beat {i + 1}: nothing found for '{kw}'")
        except requests.RequestException as e:
            print(f"[visuals] beat {i + 1}: download failed ({e})")
            path = None
        paths.append(path)
    return paths
