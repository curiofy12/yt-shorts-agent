"""
Builds the final Short in two passes:

1. moviepy: crops each stock clip to vertical, adds a slow zoom (alternating
   in and out so nothing feels static), stitches clips together, and mixes
   narration with optional background music.
2. ffmpeg + libass: burns in the animated captions, hook title card and
   progress bar from captions.py. libass renders text far faster and
   sharper than moviepy's TextClip, so this pass also keeps renders quick.

Written against moviepy 2.x.
"""
import os
import random
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import AudioLoop, MultiplyVolume

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FONTS_DIR, MUSIC_DIR, MUSIC_VOLUME, VIDEO_HEIGHT, VIDEO_WIDTH
from captions import build_ass
from voiceover import estimate_word_timings

ZOOM_AMOUNT = 0.12  # each clip zooms 12% over its duration


def _fit_vertical(clip, w, h):
    """Crop/resize a clip so it fills the vertical frame."""
    clip_ratio = clip.w / clip.h
    target_ratio = w / h
    if clip_ratio > target_ratio:
        clip = clip.cropped(x_center=clip.w / 2, width=int(clip.h * target_ratio))
    else:
        clip = clip.cropped(y_center=clip.h / 2, height=int(clip.w / target_ratio))
    return clip.resized((w, h))


def _ken_burns(clip, zoom_in: bool):
    """Slow zoom in or out, drifting slightly so it doesn't feel mechanical."""
    w, h = clip.w, clip.h
    dur = max(clip.duration, 0.01)
    drift_x = random.uniform(-0.03, 0.03)
    drift_y = random.uniform(-0.03, 0.03)

    def effect(get_frame, t):
        p = min(max(t / dur, 0.0), 1.0)
        p = p * p * (3 - 2 * p)  # ease in/out
        scale = 1 + ZOOM_AMOUNT * (p if zoom_in else 1 - p)
        cw, ch = w / scale, h / scale
        cx = w / 2 + drift_x * w * p
        cy = h / 2 + drift_y * h * p
        left = min(max(cx - cw / 2, 0), w - cw)
        top = min(max(cy - ch / 2, 0), h - ch)
        img = Image.fromarray(get_frame(t))
        img = img.resize((w, h), Image.BILINEAR, box=(left, top, left + cw, top + ch))
        return np.asarray(img)

    return clip.transform(effect)


def _prep_clip(path, target_duration, w, h, zoom_in):
    clip = _fit_vertical(VideoFileClip(path, audio=False), w, h)
    if clip.duration < target_duration:
        loops = int(target_duration // clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops)
    clip = clip.subclipped(0, target_duration)
    return _ken_burns(clip, zoom_in)


def _pick_music_track():
    if not os.path.isdir(MUSIC_DIR):
        return None
    tracks = [
        f for f in os.listdir(MUSIC_DIR)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac"))
    ]
    return os.path.join(MUSIC_DIR, random.choice(tracks)) if tracks else None


def _build_audio(narration, total_duration):
    music_path = _pick_music_track()
    if not music_path:
        print("[assemble] no music in music/, using narration only.")
        return narration
    print(f"[assemble] mixing in background music: {os.path.basename(music_path)}")
    music = AudioFileClip(music_path)
    music = music.with_effects([AudioLoop(duration=total_duration)])
    music = music.subclipped(0, total_duration).with_effects([MultiplyVolume(MUSIC_VOLUME)])
    return CompositeAudioClip([narration, music])


def _ffmpeg_binary():
    """System ffmpeg is needed for caption rendering (it includes libass)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise RuntimeError(
        "ffmpeg not found. On GitHub Actions it's installed by the workflow; "
        "locally, install ffmpeg and make sure it's on your PATH."
    )


def _burn_captions(base_path, ass_path, output_path):
    run_dir = os.path.dirname(os.path.abspath(ass_path))
    fonts_dir = os.path.abspath(FONTS_DIR)
    vf = f"ass={os.path.basename(ass_path)}:fontsdir={fonts_dir}"
    cmd = [
        _ffmpeg_binary(), "-y", "-loglevel", "error",
        "-i", os.path.abspath(base_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        os.path.abspath(output_path),
    ]
    subprocess.run(cmd, check=True, cwd=run_dir)


def build_video(clip_paths, audio_path, words, hook_title, narration_text, output_path):
    if not clip_paths:
        raise ValueError("No stock clips available to assemble video.")

    narration = AudioFileClip(audio_path)
    total_duration = narration.duration

    if not words:
        print("[assemble] no word timings from TTS, estimating them instead.")
        words = estimate_word_timings(narration_text, total_duration)

    per_clip = total_duration / len(clip_paths)
    prepped = [
        _prep_clip(p, per_clip, VIDEO_WIDTH, VIDEO_HEIGHT, zoom_in=(i % 2 == 0))
        for i, p in enumerate(clip_paths)
    ]
    video = concatenate_videoclips(prepped, method="chain").with_duration(total_duration)
    video = video.with_audio(_build_audio(narration, total_duration))

    run_dir = os.path.dirname(os.path.abspath(output_path))
    base_path = os.path.join(run_dir, "base.mp4")
    ass_path = os.path.join(run_dir, "captions.ass")

    print("[assemble] rendering base video...")
    video.write_videofile(
        base_path, fps=30, codec="libx264", audio_codec="aac",
        preset="veryfast", ffmpeg_params=["-crf", "16"], threads=4, logger=None,
    )

    print("[assemble] burning in animated captions...")
    build_ass(words, hook_title, total_duration, ass_path)
    _burn_captions(base_path, ass_path, output_path)
    return output_path
