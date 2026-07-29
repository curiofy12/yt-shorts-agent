"""
Stitches downloaded stock clips into a vertical video, overlays the
narration audio, and burns in caption text synced to roughly even
time segments across the narration's duration.

Written against moviepy 2.x (method names differ from moviepy 1.x --
e.g. resized/cropped/subclipped/with_start instead of resize/crop/
subclip/set_start).

Note: captions are timed by even division across the audio length, not
word-level forced alignment. That's good enough for short punchy phrases;
if you want word-perfect sync later, swap in a Whisper-based aligner.
"""
import os
import sys
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    concatenate_videoclips,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VIDEO_WIDTH, VIDEO_HEIGHT, FONT_PATH


def _prep_clip(path, target_duration, w, h):
    clip = VideoFileClip(path)
    # crop/resize to fill vertical frame
    clip_ratio = clip.w / clip.h
    target_ratio = w / h
    if clip_ratio > target_ratio:
        new_width = int(clip.h * target_ratio)
        clip = clip.cropped(x_center=clip.w / 2, width=new_width)
    else:
        new_height = int(clip.w / target_ratio)
        clip = clip.cropped(y_center=clip.h / 2, height=new_height)
    clip = clip.resized((w, h))

    if clip.duration < target_duration:
        loops = int(target_duration // clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops)
    return clip.subclipped(0, target_duration)


def build_video(clip_paths, audio_path, caption_segments, output_path):
    if not FONT_PATH:
        raise RuntimeError(
            "No font file found for captions. Set the FONT_PATH env var to "
            "a .ttf file, or install one (e.g. `apt install fonts-dejavu-core` "
            "on Ubuntu / GitHub Actions runners)."
        )

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    if not clip_paths:
        raise ValueError("No stock clips available to assemble video.")

    per_clip_duration = total_duration / len(clip_paths)
    prepped = [
        _prep_clip(p, per_clip_duration, VIDEO_WIDTH, VIDEO_HEIGHT)
        for p in clip_paths
    ]
    video = concatenate_videoclips(prepped, method="compose").with_duration(total_duration)

    # Burn in captions, evenly spaced across the narration
    caption_clips = []
    if caption_segments:
        seg_duration = total_duration / len(caption_segments)
        for i, text in enumerate(caption_segments):
            start = i * seg_duration
            txt_clip = (
                TextClip(
                    font=FONT_PATH,
                    text=text,
                    font_size=70,
                    color="white",
                    stroke_color="black",
                    stroke_width=3,
                    method="caption",
                    size=(int(VIDEO_WIDTH * 0.85), None),
                )
                .with_position(("center", "center"))
                .with_start(start)
                .with_duration(seg_duration)
            )
            caption_clips.append(txt_clip)

    final = CompositeVideoClip([video] + caption_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    final = final.with_audio(audio)

    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )
    return output_path
