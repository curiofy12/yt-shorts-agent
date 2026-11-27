"""
Runs the full daily pipeline once: pick topic -> write script -> voiceover
-> stock clips -> assemble -> upload -> log.

Triggered daily by .github/workflows/daily_post.yml
"""
import json
import os
import sys
import shutil
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, DRY_RUN, POSTS_LOG_PATH, VIDEO_STYLE, WORKDIR

from trends import base_topic, pick_globe_topic, pick_topic
from stats_store import load_stats
from script_gen import generate_script
from voiceover import generate_voiceover
from visuals import download_beat_clips, download_clips
from assemble import build_video
from illustrations import IllustrationError, generate_scenes
from illustrated import build_illustrated_video
from globe import build_globe_video
from dynamic import build_dynamic_video
from upload import get_authenticated_service, get_credentials, upload_short
from engagement import after_upload


def load_log():
    if os.path.exists(POSTS_LOG_PATH):
        with open(POSTS_LOG_PATH) as f:
            return json.load(f)
    return []


def save_log(log):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POSTS_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def run():
    log = load_log()
    stats = load_stats()
    recent_topics = [entry["topic"] for entry in log]

    print("[main] picking topic...")
    if VIDEO_STYLE == "globe":
        topic = pick_globe_topic(recent_topics)
    else:
        topic = pick_topic(recent_topics, log=log, stats=stats)
    print(f"[main] topic: {topic}")

    # Every title already made for this topic, so the new one is different
    same_topic_titles = [
        e["title"] for e in log
        if base_topic(e.get("topic", "")) == base_topic(topic) and e.get("title")
    ][-40:]

    run_dir = os.path.join(WORKDIR, datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)

    style = VIDEO_STYLE
    print(f"[main] style: {style}")
    print("[main] generating script...")
    script = generate_script(topic, avoid_titles=same_topic_titles, style=style)

    image_paths = []
    if style == "illustrated":
        try:
            print(f"[main] drawing {len(script['scenes'])} scenes...")
            image_paths = generate_scenes(script["scenes"], os.path.join(run_dir, "scenes"))
        except (IllustrationError, KeyError) as e:
            # Never miss a post: fall back to the stock-footage style
            print(f"[main] illustration failed ({e}); falling back to stock footage")
            style = "stock"
            script = generate_script(topic, avoid_titles=same_topic_titles, style="stock")

    print("[main] generating voiceover...")
    audio_path = os.path.join(run_dir, "narration.mp3")
    words = generate_voiceover(script["narration"], audio_path)
    print(f"[main] got timings for {len(words)} words")

    video_path = os.path.join(run_dir, "short.mp4")
    hook_title = script.get("hook_title") or script["title"].split(":")[0][:40]

    if style == "globe":
        print("[main] assembling globe video...")
        build_globe_video(
            script["beats"], audio_path,
            words=words, hook_title=hook_title,
            narration_text=script["narration"], output_path=video_path,
        )
    elif style == "illustrated":
        print("[main] assembling illustrated video...")
        build_illustrated_video(
            image_paths, script["scenes"], audio_path,
            words=words, hook_title=hook_title,
            narration_text=script["narration"], output_path=video_path,
        )
    elif script.get("beats"):
        print("[main] fetching a stock clip for each beat...")
        clip_paths = download_beat_clips(
            [b["search"] for b in script["beats"]], os.path.join(run_dir, "clips")
        )
        print("[main] assembling dynamic stock video...")
        build_dynamic_video(
            script["beats"], clip_paths, audio_path,
            words=words, hook_title=hook_title,
            narration_text=script["narration"], output_path=video_path,
        )
    else:
        print("[main] fetching stock clips...")
        clip_paths = download_clips(script["visual_keywords"], os.path.join(run_dir, "clips"))
        print("[main] assembling video...")
        build_video(
            clip_paths,
            audio_path,
            words=words,
            hook_title=hook_title,
            narration_text=script["narration"],
            output_path=video_path,
        )

    if DRY_RUN:
        preview_dir = os.path.join(os.path.dirname(WORKDIR), "preview")
        os.makedirs(preview_dir, exist_ok=True)
        shutil.copy(video_path, os.path.join(preview_dir, "short.mp4"))
        with open(os.path.join(preview_dir, "script.json"), "w") as f:
            json.dump(script, f, indent=2)
        print(f"[main] DRY RUN: saved preview, not uploading. title: {script['title']}")
        return

    print("[main] uploading...")
    creds = get_credentials()
    youtube = get_authenticated_service(creds)
    video_id = upload_short(
        video_path=video_path,
        title=script["title"],
        description=script["description"],
        tags=script["tags"],
        youtube=youtube,
    )
    after_upload(youtube, creds, video_id, topic, script.get("comment_question"))

    log.append(
        {
            "video_id": video_id,
            "topic": topic,
            "title": script["title"],
            "hook": script["hook"],
            "style": style,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "stats": None,  # filled in by weekly_report.py
        }
    )
    save_log(log)

    # Clean up local render artifacts (they're already uploaded)
    shutil.rmtree(run_dir, ignore_errors=True)

    print(f"[main] done. video_id={video_id}")


if __name__ == "__main__":
    run()
