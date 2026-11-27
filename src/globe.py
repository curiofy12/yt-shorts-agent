"""
"Every Second on Earth" style: a satellite world map where the camera flies
between regions in time with the narration, 3D icons pop onto the map
(on land, or at sea for fish, whales, ships...), and each beat's statistic
flies in as a huge number. Everything here is free: NASA's Blue Marble map
and Microsoft's Fluent 3D emoji are bundled in assets/.

Voice, captions, hook title, progress bar and music are shared with the
other styles.
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw
from moviepy import AudioFileClip, VideoClip

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ICONS_DIR, MAP_DIR, VIDEO_HEIGHT as H, VIDEO_WIDTH as W
from assemble import _build_audio, _burn_captions
from captions import build_ass
from globe_data import IMPACT_ICONS, REGIONS, SEA_ICONS
from illustrated import scene_times
from voiceover import estimate_word_timings

FPS = 30
FLY_SECONDS = 0.7      # camera flight between regions at the start of a beat
ICON_SIZE = 145        # on-screen icon size in px
POP_SECONDS = 0.25


def _ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


class WorldMap:
    def __init__(self):
        base = Image.open(os.path.join(MAP_DIR, "blue_marble.jpg")).convert("RGB")
        self.mw, self.mh = base.size
        # Pad a quarter-map on each side so views near the date line wrap
        self.pad = self.mw // 4
        ext = Image.new("RGB", (self.mw + 2 * self.pad, self.mh))
        ext.paste(base.crop((self.mw - self.pad, 0, self.mw, self.mh)), (0, 0))
        ext.paste(base, (self.pad, 0))
        ext.paste(base.crop((0, 0, self.pad, self.mh)), (self.pad + self.mw, 0))
        self.image = ext
        mask = Image.open(os.path.join(MAP_DIR, "water_mask.png")).convert("L")
        self.water = np.asarray(mask) > 128
        self.sky = Image.open(os.path.join(MAP_DIR, "night_sky.png")).convert("RGB")

    def lonlat_to_px(self, lon, lat):
        return (lon + 180) / 360 * self.mw, (90 - lat) / 180 * self.mh

    def is_water(self, x, y):
        xm = int((x % self.mw) / self.mw * self.water.shape[1]) % self.water.shape[1]
        ym = min(max(int(y / self.mh * self.water.shape[0]), 0), self.water.shape[0] - 1)
        return bool(self.water[ym, xm])

    def window(self, cx, cy, zoom):
        """Crop box (in map px, unpadded) for a camera at (cx, cy, zoom)."""
        ch = self.mh / max(zoom, 1.0)  # can't zoom out past the full map height
        cw = ch * W / H
        cy = min(max(cy, ch / 2), self.mh - ch / 2)
        cx = min(max(cx, cw / 2 - self.pad), self.mw + self.pad - cw / 2)
        return (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


class Earth3D:
    """A shaded, slowly rotating globe drawn from the Blue Marble texture."""

    def __init__(self, world, radius=430):
        tex = world.image.crop((world.pad, 0, world.pad + world.mw, world.mh)).resize((2048, 1024))
        self.tex = np.asarray(tex).astype(np.float32)
        self.r = radius
        yy, xx = np.mgrid[-radius:radius, -radius:radius].astype(np.float32) / radius
        d2 = xx ** 2 + yy ** 2
        self.mask = d2 <= 1.0
        z = np.sqrt(np.clip(1 - d2, 0, 1))
        tilt = math.radians(18)
        # tilt the globe towards the viewer a little
        y_t = yy * math.cos(tilt) - z * math.sin(tilt)
        z_t = yy * math.sin(tilt) + z * math.cos(tilt)
        self.lat = np.arcsin(np.clip(-y_t, -1, 1))
        self.lon = np.arctan2(xx, z_t)
        light = np.array([-0.55, -0.35, 0.76])
        light /= np.linalg.norm(light)
        shade = np.clip(xx * light[0] + yy * light[1] + z * light[2], 0, 1)
        self.shade = (0.18 + 0.95 * shade)[..., None]
        # soft blue atmosphere ring just outside the globe
        d = np.sqrt(d2)
        glow = np.clip(1 - (d - 1) / 0.12, 0, 1) * (d > 1)
        self.glow = (glow ** 2 * 170).astype(np.uint8)

    def render(self, t):
        h, w = self.tex.shape[:2]
        lon = self.lon + t * 0.12 - 0.6
        u = ((lon / (2 * math.pi) + 0.5) % 1.0) * (w - 1)
        v = (0.5 - self.lat / math.pi) * (h - 1)
        rgb = self.tex[v.astype(np.int32), u.astype(np.int32)] * self.shade
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        size = 2 * self.r
        out = np.zeros((size, size, 4), dtype=np.uint8)
        out[..., :3] = np.where(self.mask[..., None], rgb, np.array([110, 170, 255], np.uint8))
        out[..., 3] = np.where(self.mask, 255, self.glow)
        return Image.fromarray(out, "RGBA")


def _camera_for(world, view):
    lon, lat, zoom = REGIONS.get(view, REGIONS["world"])
    x, y = world.lonlat_to_px(lon, lat)
    return (x, y, zoom)


def _scatter(world, box, n, sea, rng):
    """n points inside box (map px) on land, or at sea for sea icons."""
    left, top, right, bottom = box
    # keep icons clear of the hook card, captions and the bottom UI
    top_m = top + (bottom - top) * 0.22
    bottom_m = top + (bottom - top) * 0.80
    left_m = left + (right - left) * 0.08
    right_m = right - (right - left) * 0.08
    min_gap = (right - left) * 0.10
    pts, tries = [], 0
    while len(pts) < n and tries < n * 80:
        tries += 1
        x, y = rng.uniform(left_m, right_m), rng.uniform(top_m, bottom_m)
        if world.is_water(x, y) != sea and tries < n * 60:
            continue
        if all((x - px) ** 2 + (y - py) ** 2 > min_gap ** 2 for px, py in pts) or tries > n * 60:
            pts.append((x, y))
    return pts


class IconBank:
    def __init__(self):
        self.cache = {}

    def get(self, name):
        if name not in self.cache:
            path = os.path.join(ICONS_DIR, f"{name}.webp")
            img = Image.open(path).convert("RGBA") if os.path.exists(path) else None
            if img is not None:
                img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
            self.cache[name] = img
        return self.cache[name]


def _vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    alpha = np.clip((d - 0.55) / 0.9, 0, 1) ** 1.6 * 150
    v = np.zeros((H, W, 4), dtype=np.uint8)
    v[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


def build_globe_video(beats, audio_path, words, hook_title, narration_text, output_path):
    narration = AudioFileClip(audio_path)
    total = narration.duration
    if not words:
        print("[globe] no word timings from TTS, estimating them instead.")
        words = estimate_word_timings(narration_text, total)

    world = WorldMap()
    earth = Earth3D(world)
    icons = IconBank()
    vignette = _vignette()
    times = scene_times(beats, words, total)
    rng = random.Random(7)

    # Plan each beat: camera target, icon positions and pop-in times
    plan = []
    prev_cam = None
    for i, b in enumerate(beats):
        start, end = times[i]
        space = b.get("view") == "space"
        cam = _camera_for(world, "world" if space else b.get("view", "world"))
        if prev_cam is None:
            prev_cam = (cam[0], cam[1], max(cam[2] * 0.85, 1.0))  # open with a slow push in
        box = world.window(*cam)
        n = int(b.get("count") or 0) if b.get("icon") else 0
        sea = b.get("icon") in SEA_ICONS
        pts = _scatter(world, box, n, sea, rng) if n else []
        wants_ripples = b.get("effect") == "ripples" and (not b.get("icon") or b.get("icon") in IMPACT_ICONS)
        ripple_pts = pts[:3] if wants_ripples else []
        if wants_ripples and not ripple_pts:
            # No icons to anchor the ripples: put them near the view's centre
            ripple_pts = _scatter(world, box, 2, False, rng) or [(cam[0], cam[1])]
        span = max((end - start) * 0.55 - FLY_SECONDS * 0.5, 0.3)
        stagger = min(0.12, span / max(n, 1))
        appear = [start + FLY_SECONDS * 0.5 + k * stagger for k in range(len(pts))]
        sizes = [rng.uniform(0.8, 1.15) for _ in pts]
        plan.append({
            "start": start, "end": end, "from": prev_cam, "to": cam, "space": space,
            "icon": b.get("icon"), "pts": pts, "appear": appear, "sizes": sizes,
            "ripples": wants_ripples, "ripple_pts": ripple_pts,
        })
        prev_cam = cam

    def camera_at(p, t):
        k = (t - p["start"]) / FLY_SECONDS
        fx, fy, fz = p["from"]
        tx, ty, tz = p["to"]
        e = _ease(k)
        x, y = fx + (tx - fx) * e, fy + (ty - fy) * e
        z = math.exp(math.log(fz) + (math.log(tz) - math.log(fz)) * e)
        drift = (t - p["start"] - FLY_SECONDS) / max(p["end"] - p["start"], 0.1)
        z *= 1 + 0.05 * _ease(max(drift, 0))
        return x, y, z

    def make_frame(t):
        i = next((k for k, p in enumerate(plan) if t < p["end"]), len(plan) - 1)
        p = plan[i]

        if p["space"]:
            sw, sh = world.sky.size
            ch = sh * 0.8
            cw = ch * W / H
            dx = (t - p["start"]) * 12
            box = ((sw - cw) / 2 + dx, (sh - ch) / 2, (sw + cw) / 2 + dx, (sh + ch) / 2)
            frame = world.sky.resize((W, H), Image.BICUBIC, box=box)
            frame = Image.eval(frame, lambda v: min(255, int(v * 2.2)))  # brighter stars
            frame = frame.convert("RGBA")
            globe_img = earth.render(t)
            grow = 0.85 + 0.15 * _ease((t - p["start"]) / 1.2)
            gs = int(globe_img.width * grow)
            globe_img = globe_img.resize((gs, gs), Image.BILINEAR)
            frame.alpha_composite(globe_img, ((W - gs) // 2, int(H * 0.47 - gs / 2)))
            # points were planned on the world view; map them to the screen proportionally
            view_box = world.window(*p["to"])
        else:
            cx, cy, z = camera_at(p, t)
            view_box = world.window(cx, cy, z)
            l, tp, r, b = view_box
            frame = world.image.resize((W, H), Image.BICUBIC,
                                       box=(l + world.pad, tp, r + world.pad, b))
        frame = frame.convert("RGBA")
        frame.alpha_composite(vignette)

        l, tp, r, b = view_box
        sx = W / (r - l)
        sy = H / (b - tp)

        if p["ripples"] and p["ripple_pts"]:
            d = ImageDraw.Draw(frame)
            for (mx, my) in p["ripple_pts"]:
                x0, y0 = (mx - l) * sx, (my - tp) * sy
                for k in range(3):
                    ph = ((t - p["start"]) * 0.8 + k / 3) % 1.0
                    rr = 30 + ph * 260
                    a = int(220 * (1 - ph))
                    d.ellipse([x0 - rr, y0 - rr, x0 + rr, y0 + rr],
                              outline=(255, 60, 60, a), width=7)

        icon = icons.get(p["icon"]) if p["icon"] else None
        if icon is not None:
            for (mx, my), t0, sz in zip(p["pts"], p["appear"], p["sizes"]):
                if t < t0:
                    continue
                q = (t - t0) / POP_SECONDS
                pop = 1.0 if q >= 1 else (1.25 * _ease(q / 0.7) if q < 0.7 else 1.25 - 0.25 * _ease((q - 0.7) / 0.3))
                s = max(int(ICON_SIZE * sz * pop), 2)
                img = icon if s == ICON_SIZE else icon.resize((s, s), Image.BILINEAR)
                x0 = int((mx - l) * sx - s / 2)
                y0 = int((my - tp) * sy - s / 2)
                # Draw only the part of the icon that's on screen
                cl, ct = max(0, -x0), max(0, -y0)
                cr, cb = min(s, W - x0), min(s, H - y0)
                if cr > cl and cb > ct:
                    part = img if (cl, ct, cr, cb) == (0, 0, s, s) else img.crop((cl, ct, cr, cb))
                    frame.alpha_composite(part, (x0 + cl, y0 + ct))

        return np.asarray(frame.convert("RGB"))

    video = VideoClip(make_frame, duration=total).with_fps(FPS)
    cut_times = [p["start"] for p in plan[1:]]
    video = video.with_audio(
        _build_audio(narration, total, words=words, cut_times=cut_times, hook_shown=bool(hook_title))
    )

    run_dir = os.path.dirname(os.path.abspath(output_path))
    base_path = os.path.join(run_dir, "base.mp4")
    ass_path = os.path.join(run_dir, "captions.ass")

    print("[globe] rendering map animation...")
    video.write_videofile(
        base_path, fps=FPS, codec="libx264", audio_codec="aac",
        preset="veryfast", ffmpeg_params=["-crf", "16"], threads=4, logger=None,
    )

    big = [(p["start"] + 0.3, p["end"] - 0.05, b.get("big_number", ""))
           for p, b in zip(plan, beats)]
    print("[globe] burning in captions and numbers...")
    build_ass(words, hook_title, total, ass_path, big_numbers=big)
    _burn_captions(base_path, ass_path, output_path)
    return output_path
