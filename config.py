import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
YOUTUBE_CLIENT_SECRET_PATH = os.environ.get("YOUTUBE_CLIENT_SECRET_PATH", "client_secret.json")
YOUTUBE_TOKEN_PATH = os.environ.get("YOUTUBE_TOKEN_PATH", "token.json")
CHANNEL_NICHE = os.environ.get("CHANNEL_NICHE", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
POSTS_LOG_PATH = os.path.join(DATA_DIR, "posts_log.json")
WORKDIR = os.path.join(os.path.dirname(__file__), "workdir")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # vertical, Shorts format
TARGET_DURATION_SECONDS = 45  # sweet spot for shorts retention: 30-59s

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

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]
