"""
Draws one illustration per scene with Cloudflare Workers AI's FLUX schnell
model. Cloudflare's free tier (10,000 "neurons" a day) covers roughly 170
images a day, so this costs nothing at our volume.

Every prompt gets the same style description appended, so the scenes in a
video look like one consistent series.
"""
import base64
import os
import sys
import time

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN

MODEL = "@cf/black-forest-labs/flux-1-schnell"
STEPS = 8  # schnell's maximum; better detail, still well inside the free tier

# The house style. Edit this to change the look of every illustrated video.
STYLE = (
    "flat 2D vector illustration, simple cartoon characters with large round "
    "heads and small bodies, clean geometric shapes, smooth flat colors, "
    "subtle soft shading, muted moody palette with warm glowing accent lights, "
    "cinematic composition with the main subject in the center of the frame, "
    "storybook explainer animation style, high quality, "
    "no text, no words, no letters, no captions, no watermark"
)


class IllustrationError(RuntimeError):
    pass


def available() -> bool:
    return bool(CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN)


def _generate(prompt: str, out_path: str, retries: int = 2):
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"
    )
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    body = {"prompt": f"{prompt}. {STYLE}", "steps": STEPS}

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=90)
            if resp.status_code == 200:
                data = resp.json()
                image_b64 = (data.get("result") or {}).get("image")
                if image_b64:
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(image_b64))
                    return out_path
                last_err = f"no image in response: {str(data)[:300]}"
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
                if resp.status_code in (401, 403):
                    break  # bad key or permissions -- retrying won't help
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(3 * (attempt + 1))
    raise IllustrationError(last_err)


def generate_scenes(scenes, out_dir):
    """Returns one image path per scene, in order."""
    if not available():
        raise IllustrationError(
            "CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN are not set."
        )
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, scene in enumerate(scenes):
        path = os.path.join(out_dir, f"scene_{i:02d}.jpg")
        _generate(scene["image_prompt"], path)
        print(f"[illustrations] drew scene {i + 1}/{len(scenes)}")
        paths.append(path)
    return paths
