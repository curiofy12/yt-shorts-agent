import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()

# "stock" = Pexels footage, "illustrated" = AI cartoon scenes.
# The workflow sets this per scheduled slot.
VIDEO_STYLE = os.environ.get("VIDEO_STYLE", "stock").strip() or "stock"
# Set to "1" to render without uploading (for test runs).
DRY_RUN = os.environ.get("DRY_RUN", "") == "1"
YOUTUBE_CLIENT_SECRET_PATH = os.environ.get("YOUTUBE_CLIENT_SECRET_PATH", "client_secret.json")
YOUTUBE_TOKEN_PATH = os.environ.get("YOUTUBE_TOKEN_PATH", "token.json")
CHANNEL_NICHE = os.environ.get("CHANNEL_NICHE", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
POSTS_LOG_PATH = os.path.join(DATA_DIR, "posts_log.json")
# Per-video stats live in their own file (written only by the weekly
# report) so daily posts and the weekly report never edit the same file.
STATS_PATH = os.path.join(DATA_DIR, "video_stats.json")
WORKDIR = os.path.join(os.path.dirname(__file__), "workdir")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # vertical, Shorts format
TARGET_DURATION_SECONDS = 38  # shorter = more people finish it; finish rate drives Shorts reach

# moviepy 2.x renders captions via PIL and needs an actual font FILE path
# (not a font name string like "Arial-Bold" as older moviepy allowed).
FONT_PATH = os.environ.get("FONT_PATH")
if not FONT_PATH:
    _candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Ubuntu/GitHub Actions
        "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
    ]
    for _c in _candidates:
        if os.path.exists(_c):
            FONT_PATH = _c
            break

# Fonts used by the animated captions (Anton, OFL licensed, bundled in repo)
FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")

# Background music: drop royalty-free tracks (mp3/wav/m4a) into music/ and
# one is picked at random per video. 0.35 = noticeable, narration dominant.
MUSIC_DIR = os.path.join(os.path.dirname(__file__), "music")
MUSIC_VOLUME = 0.35

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]
