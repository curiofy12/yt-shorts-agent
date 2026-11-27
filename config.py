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
TARGET_DURATION_SECONDS = 36  # shorter = more people finish it; scripts tend to run a little long

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

# "Every Second on Earth" style: NASA world map + Fluent 3D emoji icons
MAP_DIR = os.path.join(os.path.dirname(__file__), "assets", "map")
ICONS_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")

# Background music: drop royalty-free tracks (mp3/wav/m4a) into music/ and
# one is picked at random per video. 0.35 = noticeable, narration dominant.
MUSIC_DIR = os.path.join(os.path.dirname(__file__), "music")
MUSIC_VOLUME = 0.35
# Music "ducks" to this fraction of MUSIC_VOLUME while the narrator talks,
# and rises to PAUSE_BOOST x MUSIC_VOLUME in pauses and at the end.
DUCK_RATIO = 0.6
PAUSE_BOOST = 1.3

# Sound effects (currently off: the sfx/ folder was removed). To turn them
# back on, add a sfx/ folder with files starting "whoosh" (played on scene
# cuts) and/or one starting "pop" (played as the hook title appears).
SFX_DIR = os.path.join(os.path.dirname(__file__), "sfx")
SFX_VOLUME = 0.5

# Needed for playlists and posting comments. auth_setup.py asks for it;
# tokens made before it was added simply skip those two features.
MANAGE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"

YOUTUBE_SCOPES = [
    MANAGE_SCOPE,
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]
