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
from config import (
    DUCK_RATIO, FONTS_DIR, MUSIC_DIR, MUSIC_VOLUME, PAUSE_BOOST, SFX_DIR, SFX_VOLUME,
    VIDEO_HEIGHT, VIDEO_WIDTH,
)
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


def _normalize_clip(path, w, h):
    """
    Re-encode a downloaded stock clip into a clean, vertical, 30fps video
    with only a picture track. Some Pexels files carry extra timecode/data
    tracks that moviepy can't parse; this strips them. Pre-cropping here
    also makes the moviepy pass faster.
    """
    out = os.path.splitext(path)[0] + "_clean.mp4"
    if os.path.exists(out):
        return out
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,setsar=1"
    cmd = [
        _ffmpeg_binary(), "-y", "-loglevel", "error",
        "-i", path,
        "-map", "0:v:0", "-an", "-sn", "-dn",
        "-map_metadata", "-1", "-map_chapters", "-1",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        out,
    ]
    subprocess.run(cmd, check=True)
    return out


def _prep_clip(path, target_duration, w, h, zoom_in):
    clip = _fit_vertical(VideoFileClip(_normalize_clip(path, w, h), audio=False), w, h)
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


def _music_envelope(words, total_duration):
    """
    Music volume over time: dips under the voice, rises a little in pauses
    and swells at the very end. Returns a function of t (seconds, array ok).
    """
    step = 0.02
    grid = np.arange(0, total_duration + step, step)
    speaking = np.zeros_like(grid, dtype=bool)
    for w in words or []:
        a = max(int((w["start"] - 0.08) / step), 0)
        b = int((w["end"] + 0.25) / step) + 1
        speaking[a:b] = True
    target = np.where(speaking, MUSIC_VOLUME * DUCK_RATIO, MUSIC_VOLUME * PAUSE_BOOST)
    # Swell over the last 1.2 seconds as the narration wraps up
    tail = grid > total_duration - 1.2
    target[tail] = np.maximum(target[tail], MUSIC_VOLUME * PAUSE_BOOST)
    # Smooth the changes (~200 ms) so it never sounds like a switch
    k = int(0.2 / step)
    kernel = np.ones(k) / k
    smooth = np.convolve(np.pad(target, (k, k), mode="edge"), kernel, mode="same")[k:-k]

    def env(t):
        return np.interp(t, grid, smooth)
    return env


def _sfx_clips(cut_times, hook_shown):
    """Whooshes on scene cuts and a pop as the hook card appears."""
    if not os.path.isdir(SFX_DIR):
        return []
    files = os.listdir(SFX_DIR)
    whooshes = [os.path.join(SFX_DIR, f) for f in files if f.lower().startswith("whoosh")]
    pops = [os.path.join(SFX_DIR, f) for f in files if f.lower().startswith("pop")]
    clips = []
    for i, t in enumerate(cut_times):
        if whooshes and t > 0.3:
            # Start slightly before the cut so the swoosh peaks on it
            clip = AudioFileClip(whooshes[i % len(whooshes)]).with_effects([MultiplyVolume(SFX_VOLUME)])
            clips.append(clip.with_start(max(t - 0.25, 0)))
    if pops and hook_shown:
        clips.append(AudioFileClip(pops[0]).with_effects([MultiplyVolume(SFX_VOLUME)]).with_start(0.05))
    return clips


def _sfx_from_events(events):
    """events: list of (time, kind) with kind 'pop' or 'whoosh'."""
    if not os.path.isdir(SFX_DIR):
        return []
    files = sorted(os.listdir(SFX_DIR))
    by_kind = {
        kind: [os.path.join(SFX_DIR, f) for f in files
               if f.lower().startswith(kind) and f.lower().endswith((".mp3", ".wav", ".ogg"))]
        for kind in ("pop", "whoosh")
    }
    clips, counts = [], {"pop": 0, "whoosh": 0}
    for t, kind in events:
        pool = by_kind.get(kind) or []
        if not pool:
            continue
        path = pool[counts[kind] % len(pool)]
        counts[kind] += 1
        # whooshes start a little early so they peak on the cut
        start = max(t - (0.3 if kind == "whoosh" else 0.0), 0)
        clips.append(AudioFileClip(path).with_effects([MultiplyVolume(SFX_VOLUME)]).with_start(start))
    return clips


def _build_audio(narration, total_duration, words=None, cut_times=(), hook_shown=True, sfx_events=None):
    layers = [narration]

    music_path = _pick_music_track()
    if music_path:
        print(f"[assemble] mixing in background music: {os.path.basename(music_path)}")
        music = AudioFileClip(music_path)
        music = music.with_effects([AudioLoop(duration=total_duration)]).subclipped(0, total_duration)
        env = _music_envelope(words, total_duration)

        def duck(get_frame, t):
            frame = get_frame(t)
            vol = env(np.asarray(t, dtype=float))
            return frame * (vol[:, None] if np.ndim(vol) else vol)

        layers.append(music.transform(duck))
    else:
        print("[assemble] no music in music/, using narration only.")

    if sfx_events is not None:
        layers += _sfx_from_events(sfx_events)
    else:
        layers += _sfx_clips(cut_times, hook_shown)
    if len(layers) == 1:
        return narration
    return CompositeAudioClip(layers).with_duration(total_duration)


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

    # Check which clips can actually be used before dividing up the time,
    # so one bad download can't sink the whole video.
    usable = []
    for p in clip_paths:
        try:
            with VideoFileClip(_normalize_clip(p, VIDEO_WIDTH, VIDEO_HEIGHT), audio=False) as c:
                if c.duration and c.duration > 0.5:
                    usable.append(p)
        except Exception as e:
            print(f"[assemble] skipping unusable clip {os.path.basename(p)}: {e}")
    if not usable:
        raise ValueError("None of the downloaded stock clips could be used.")

    per_clip = total_duration / len(usable)
    prepped = [
        _prep_clip(p, per_clip, VIDEO_WIDTH, VIDEO_HEIGHT, zoom_in=(i % 2 == 0))
        for i, p in enumerate(usable)
    ]
    video = concatenate_videoclips(prepped, method="chain").with_duration(total_duration)
    cut_times = [i * per_clip for i in range(1, len(usable))]
    video = video.with_audio(
        _build_audio(narration, total_duration, words=words, cut_times=cut_times, hook_shown=bool(hook_title))
    )

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
