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
from config import DATA_DIR, POSTS_LOG_PATH, WORKDIR

from trends import pick_topic
from script_gen import generate_script
from voiceover import generate_voiceover
from visuals import download_clips
from assemble import build_video
from upload import upload_short


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
    recent_topics = [entry["topic"] for entry in log[-60:]]

    print("[main] picking topic...")
    topic = pick_topic(recent_topics)
    print(f"[main] topic: {topic}")

    print("[main] generating script...")
    script = generate_script(topic)

    run_dir = os.path.join(WORKDIR, datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)

    print("[main] generating voiceover...")
    audio_path = os.path.join(run_dir, "narration.mp3")
    generate_voiceover(script["narration"], audio_path)

    print("[main] fetching stock clips...")
    clips_dir = os.path.join(run_dir, "clips")
    clip_paths = download_clips(script["visual_keywords"], clips_dir)

    print("[main] assembling video...")
    video_path = os.path.join(run_dir, "short.mp4")
    build_video(clip_paths, audio_path, script["caption_segments"], video_path)

    print("[main] uploading...")
    video_id = upload_short(
        video_path=video_path,
        title=script["title"],
        description=script["description"],
        tags=script["tags"],
    )

    log.append(
        {
            "video_id": video_id,
            "topic": topic,
            "title": script["title"],
            "hook": script["hook"],
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
