"""
Builds an illustrated-style Short: one AI illustration per scene, each
shown with a slow camera move (push in, pull out, or pan) and cut exactly
when the narration moves on to the next scene. Optional particles (snow,
rain, dust, embers, bubbles, stars) drift over each scene, and place/date
labels like "CHICAGO, 1930" fade in where the script asks for them.

Voice, animated captions, hook title and progress bar are shared with the
stock-footage style (see assemble.py and captions.py).
"""
import math
import os
import random
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from moviepy import AudioFileClip, VideoClip

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VIDEO_HEIGHT as H, VIDEO_WIDTH as W
from assemble import _build_audio, _burn_captions
from captions import build_ass
from voiceover import estimate_word_timings

FPS = 30
CAMERA_MOVES = ["push_in", "pan_right", "pull_out", "pan_left"]


# --------------------------------------------------------------------------
# Timing
# --------------------------------------------------------------------------
def scene_times(scenes, words, total_duration):
    """Start/end seconds for each scene, based on when its words are spoken."""
    counts = [len(re.findall(r"[\w'’-]+", s.get("text", ""))) for s in scenes]
    if not words or sum(counts) == 0:
        step = total_duration / len(scenes)
        return [(i * step, (i + 1) * step) for i in range(len(scenes))]

    # Scale scene word counts to the TTS word list (they can differ slightly)
    scale = len(words) / sum(counts)
    starts, cum = [], 0.0
    for c in counts:
        idx = min(int(round(cum * scale)), len(words) - 1)
        starts.append(0.0 if not starts else words[idx]["start"])
        cum += c
    times = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else total_duration
        times.append((s, max(e, s + 0.5)))
    return times


# --------------------------------------------------------------------------
# Camera
# --------------------------------------------------------------------------
def _ease(p):
    return p * p * (3 - 2 * p)


def _crop_box(img_w, img_h, move, p):
    """The part of the illustration on screen at progress p (0..1)."""
    target = W / H
    # Largest 9:16 window that fits the image
    if img_w / img_h > target:
        base_h, base_w = img_h, img_h * target
    else:
        base_w, base_h = img_w, img_w / target

    p = _ease(p)
    zoom, cx = 1.0, 0.5
    if move == "push_in":
        zoom = 1.0 + 0.16 * p
    elif move == "pull_out":
        zoom = 1.16 - 0.16 * p
    elif move == "pan_right":
        zoom, cx = 1.04, 0.2 + 0.6 * p
    elif move == "pan_left":
        zoom, cx = 1.04, 0.8 - 0.6 * p

    cw, ch = base_w / zoom, base_h / zoom
    # cx in 0..1 = how far across the image's spare width the window sits
    left = (img_w - cw) * cx if move.startswith("pan") else (img_w - cw) / 2
    top = (img_h - ch) / 2
    return (left, top, left + cw, top + ch)


# --------------------------------------------------------------------------
# Particles
# --------------------------------------------------------------------------
PARTICLE_STYLES = {
    #          count  size       speed(px/s)  color              drift
    "snow":    (90,  (3, 8),    (60, 140),   (255, 255, 255, 200), 25),
    "rain":    (140, (2, 3),    (900, 1300), (200, 215, 255, 120), 60),
    "dust":    (60,  (2, 5),    (8, 25),     (255, 225, 170, 110), 15),
    "embers":  (45,  (3, 7),    (-90, -40),  (255, 150, 60, 210),  30),
    "bubbles": (40,  (6, 18),   (-110, -50), (210, 240, 255, 150), 20),
    "stars":   (110, (2, 5),    (0, 0),      (255, 255, 255, 220), 0),
}


class Particles:
    def __init__(self, kind, seed):
        self.kind = kind if kind in PARTICLE_STYLES else "none"
        rng = random.Random(seed)
        if self.kind == "none":
            self.items = []
            return
        count, (smin, smax), (vmin, vmax), self.color, drift = PARTICLE_STYLES[self.kind]
        self.items = [
            {
                "x": rng.uniform(0, W), "y": rng.uniform(0, H),
                "r": rng.uniform(smin, smax), "v": rng.uniform(vmin, vmax),
                "drift": rng.uniform(-drift, drift), "phase": rng.uniform(0, 6.28),
            }
            for _ in range(count)
        ]

    def draw(self, frame: Image.Image, t: float) -> Image.Image:
        if not self.items:
            return frame
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        r0, g0, b0, a0 = self.color
        for p in self.items:
            x = (p["x"] + p["drift"] * t + 12 * math.sin(t * 1.3 + p["phase"])) % W
            y = (p["y"] + p["v"] * t) % H
            r = p["r"]
            if self.kind == "rain":
                d.line([(x, y), (x - 6, y + 34)], fill=self.color, width=int(r))
            elif self.kind == "bubbles":
                d.ellipse([x - r, y - r, x + r, y + r], outline=self.color, width=2)
            elif self.kind == "stars":
                a = int(a0 * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 2.2 + p["phase"]))))
                d.ellipse([x - r, y - r, x + r, y + r], fill=(r0, g0, b0, a))
            else:
                d.ellipse([x - r, y - r, x + r, y + r], fill=self.color)
        return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build_illustrated_video(image_paths, scenes, audio_path, words, hook_title,
                            narration_text, output_path):
    narration = AudioFileClip(audio_path)
    total = narration.duration
    if not words:
        print("[illustrated] no word timings from TTS, estimating them instead.")
        words = estimate_word_timings(narration_text, total)

    times = scene_times(scenes, words, total)
    images = [Image.open(p).convert("RGB") for p in image_paths]
    moves = [CAMERA_MOVES[i % len(CAMERA_MOVES)] for i in range(len(scenes))]
    particles = [
        Particles((s.get("particles") or "none").strip().lower(), seed=i)
        for i, s in enumerate(scenes)
    ]

    def make_frame(t):
        i = next((k for k, (s, e) in enumerate(times) if t < e), len(times) - 1)
        start, end = times[i]
        p = min(max((t - start) / max(end - start, 0.01), 0.0), 1.0)
        img = images[i]
        box = _crop_box(img.width, img.height, moves[i], p)
        frame = img.resize((W, H), Image.BICUBIC, box=box)
        frame = particles[i].draw(frame, t - start)
        return np.asarray(frame)

    video = VideoClip(make_frame, duration=total).with_fps(FPS)
    cut_times = [s for s, _ in times[1:]]
    video = video.with_audio(
        _build_audio(narration, total, words=words, sfx_events=[])  # no sound effects in this style
    )

    run_dir = os.path.dirname(os.path.abspath(output_path))
    base_path = os.path.join(run_dir, "base.mp4")
    ass_path = os.path.join(run_dir, "captions.ass")

    print("[illustrated] rendering scenes...")
    video.write_videofile(
        base_path, fps=FPS, codec="libx264", audio_codec="aac",
        preset="veryfast", ffmpeg_params=["-crf", "16"], threads=4, logger=None,
    )

    labels = [(times[i][0] + 0.2, s.get("label", "")) for i, s in enumerate(scenes)]
    print("[illustrated] burning in captions and labels...")
    build_ass(words, hook_title, total, ass_path, labels=labels)
    _burn_captions(base_path, ass_path, output_path)
    return output_path
