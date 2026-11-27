"""
Dynamic stock-footage Shorts: one clip per beat, cut exactly when the
narration moves on, with motion-graphics touches borrowed from the big
"facts" channels:

- punch-in zooms and fast whip-slide transitions between clips
- a 3D icon that pops on screen when the narration mentions something
- huge numbers that fly in when a beat states a figure, with a snap zoom
- optional sound effects: a pop when an icon or number lands, a whoosh on
  whip transitions (drop files named pop*/whoosh* into sfx/)

Voice, captions, hook title, progress bar and music are shared with the
other styles.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter
from moviepy import AudioFileClip, VideoClip, VideoFileClip

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ICONS_DIR, VIDEO_HEIGHT as H, VIDEO_WIDTH as W
from assemble import _build_audio, _burn_captions, _normalize_clip
from captions import build_ass
from illustrated import scene_times
from voiceover import estimate_word_timings

FPS = 30
PUNCH_SECONDS = 0.30   # punch-in: starts zoomed in, eases back out
WHIP_SECONDS = 0.22    # whip: old clip slides out, new slides in, blurred
ICON_SIZE = 300
ICON_IN = 0.35         # icon pops in this long after its beat starts
NUMBER_IN = 0.30       # matches the big-number timing in captions


def _ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def _ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def _zoom_crop(img, zoom, dx=0.0):
    """Zoom into the centre of a W x H frame (zoom >= 1), shifted by dx px."""
    if zoom <= 1.001 and abs(dx) < 0.5:
        return img
    cw, ch = W / zoom, H / zoom
    left = (W - cw) / 2 + dx
    left = min(max(left, 0), W - cw)
    top = (H - ch) / 2
    return img.resize((W, H), Image.BILINEAR, box=(left, top, left + cw, top + ch))


def _pop_scale(q):
    """0 -> overshoot -> 1 over q in [0, 1]."""
    if q >= 1:
        return 1.0
    if q < 0.65:
        return 1.22 * _ease_out(q / 0.65)
    return 1.22 - 0.22 * _ease((q - 0.65) / 0.35)


def build_dynamic_video(beats, clip_paths, audio_path, words, hook_title,
                        narration_text, output_path):
    narration = AudioFileClip(audio_path)
    total = narration.duration
    if not words:
        print("[dynamic] no word timings from TTS, estimating them instead.")
        words = estimate_word_timings(narration_text, total)

    # Clean every clip (vertical 1080x1920, 30fps, picture only); a beat
    # with no usable clip borrows the nearest one that worked.
    readers = []
    for p in clip_paths:
        clip = None
        if p:
            try:
                clip = VideoFileClip(_normalize_clip(p, W, H), audio=False)
                if not clip.duration or clip.duration < 0.5:
                    clip = None
            except Exception as e:
                print(f"[dynamic] skipping unusable clip {os.path.basename(p)}: {e}")
        readers.append(clip)
    if not any(readers):
        raise ValueError("None of the downloaded stock clips could be used.")
    for i in range(len(readers)):
        if readers[i] is None:
            near = sorted(range(len(readers)), key=lambda k: abs(k - i))
            readers[i] = next(readers[k] for k in near if readers[k] is not None)

    times = scene_times(beats, words, total)
    icon_cache = {}

    def icon_img(name):
        if name not in icon_cache:
            path = os.path.join(ICONS_DIR, f"{name}.webp")
            icon_cache[name] = (
                Image.open(path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                if os.path.exists(path) else None
            )
        return icon_cache[name]

    plan = []
    plain_cuts = 0
    for i, b in enumerate(beats):
        start, end = times[i]
        if i == 0:
            transition = None
        elif b.get("whoosh"):
            transition = "whip"      # big scene change: whip-slide + whoosh
        else:
            plain_cuts += 1          # ordinary cuts alternate punch-in / straight cut
            transition = "punch" if plain_cuts % 2 == 1 else None
        plan.append({
            "start": start, "end": end, "clip": readers[i],
            "transition": transition,
            "zoom_in": i % 2 == 0,
            "icon": b.get("icon") or "",
            "icon_side": -1 if i % 2 == 0 else 1,
            "number": bool(b.get("big_number")),
        })

    def clip_frame(p, t):
        """The beat's own footage at time t, with its slow push and number snap."""
        clip = p["clip"]
        local = (t - p["start"]) % max(clip.duration - 0.05, 0.1)
        frame = Image.fromarray(clip.get_frame(local))
        prog = (t - p["start"]) / max(p["end"] - p["start"], 0.1)
        zoom = 1.0 + 0.08 * (_ease(prog) if p["zoom_in"] else 1 - _ease(prog))
        if p["transition"] == "punch":
            k = (t - p["start"]) / PUNCH_SECONDS
            if k < 1:
                zoom += 0.22 * (1 - _ease_out(k))
        if p["number"]:
            k = (t - p["start"] - NUMBER_IN) / 0.45
            if 0 <= k < 1:
                zoom += 0.06 * math.sin(math.pi * min(k * 1.6, 1.0)) * (1 - k)
        return _zoom_crop(frame, zoom)

    def make_frame(t):
        i = next((k for k, p in enumerate(plan) if t < p["end"]), len(plan) - 1)
        p = plan[i]
        frame = clip_frame(p, t)

        # Whip: previous clip slides out left, new clip slides in from the right
        k = (t - p["start"]) / WHIP_SECONDS
        if p["transition"] == "whip" and k < 1 and i > 0:
            prev = clip_frame(plan[i - 1], t)
            e = _ease(k)
            blur = ImageFilter.GaussianBlur(radius=10 * math.sin(math.pi * e) + 0.5)
            canvas = Image.new("RGB", (W, H))
            canvas.paste(prev.filter(blur), (int(-W * e), 0))
            canvas.paste(frame.filter(blur), (int(W * (1 - e)), 0))
            frame = canvas

        frame = frame.convert("RGBA")

        # Icon pops in, bobs gently, shrinks away at the end of its beat
        if p["icon"]:
            img = icon_img(p["icon"])
            t_in = p["start"] + ICON_IN
            if img is not None and t >= t_in:
                s = _pop_scale((t - t_in) / 0.3)
                out = (p["end"] - t) / 0.15
                if out < 1:
                    s *= max(out, 0)
                size = int(ICON_SIZE * s)
                if size > 4:
                    icon = img if size == ICON_SIZE else img.resize((size, size), Image.BILINEAR)
                    # first beat shares the top with the hook title, so sit lower
                    cy = int(H * (0.44 if p["start"] < 2.8 else 0.27)) + int(10 * math.sin((t - t_in) * 3.2))
                    cx = int(W / 2 + p["icon_side"] * W * 0.25)
                    frame.alpha_composite(icon, (cx - size // 2, cy - size // 2))

        return np.asarray(frame.convert("RGB"))

    # Sound effect cues: whoosh on whips, pop when an icon lands
    sfx = []
    for p in plan:
        if p["transition"] == "whip":
            sfx.append((p["start"], "whoosh"))
        if p["icon"]:
            sfx.append((p["start"] + ICON_IN, "pop"))

    video = VideoClip(make_frame, duration=total).with_fps(FPS)
    video = video.with_audio(
        _build_audio(narration, total, words=words, sfx_events=sfx)
    )

    run_dir = os.path.dirname(os.path.abspath(output_path))
    base_path = os.path.join(run_dir, "base.mp4")
    ass_path = os.path.join(run_dir, "captions.ass")

    print("[dynamic] rendering clips and motion graphics...")
    video.write_videofile(
        base_path, fps=FPS, codec="libx264", audio_codec="aac",
        preset="veryfast", ffmpeg_params=["-crf", "16"], threads=4, logger=None,
    )

    big = [(p["start"] + NUMBER_IN, p["end"] - 0.05, b.get("big_number", ""))
           for p, b in zip(plan, beats)]
    print("[dynamic] burning in captions and numbers...")
    build_ass(words, hook_title, total, ass_path, big_numbers=big)
    _burn_captions(base_path, ass_path, output_path)
    return output_path
