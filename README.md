# Faceless YouTube Shorts Agent

An automated pipeline that, once a day:
1. Finds a trending topic
2. Writes a short script + title/description/tags
3. Generates an AI voiceover
4. Pulls matching stock video clips
5. Assembles a captioned vertical Short
6. Uploads it to your channel
7. Logs performance over time and writes you a weekly "what's working" report

It runs on GitHub Actions on a schedule — no computer left running.

---

## Architecture

```
trends.py      -> pick today's topic
script_gen.py  -> Claude writes hook/script/title/description/tags
voiceover.py   -> free TTS (edge-tts) renders narration.mp3
visuals.py     -> Pexels API pulls stock clips matching keywords
assemble.py    -> moviepy stitches clips + audio + burned-in captions -> short.mp4
upload.py      -> YouTube Data API v3 uploads the video
analytics.py   -> pulls views/watch time/(revenue if monetized) for past uploads
insights.py    -> Claude reads the performance log and writes recommendations
main.py        -> runs steps 1-6 daily
weekly_report.py -> runs analytics + insights weekly
```

All state (what's been posted, how it performed) lives in `data/posts_log.json`,
which is committed back to the repo by the GitHub Action so the agent has memory
across runs.

---

## One-time setup (you do this once, ~30-45 min)

### 1. Google Cloud / YouTube API
See **OAUTH_SETUP.md** for a full detailed walkthrough. Short version:
1. Go to console.cloud.google.com, create a project.
2. Enable **YouTube Data API v3** and **YouTube Analytics API**.
3. Create OAuth 2.0 credentials (Desktop app type). Download the JSON as `client_secret.json`.
4. Run `python auth_setup.py` locally once — it opens a browser, you log into the
   YouTube channel's Google account, and it saves a refresh token to `token.json`.
   This refresh token is what the automation uses forever after (no more browser logins).
5. Note: while your app is in "Testing" mode in Google Cloud, only test users you
   add can authorize it — add your own Google account as a test user.

### 2. Pexels API key (free)
Sign up at pexels.com/api — free, no cost, generous limits. Used for stock video clips.

### 3. Anthropic API key
console.anthropic.com — used for script writing and the insights report.
Budget: a 40-60s script + weekly insights report is a small number of tokens;
expect well under $1/day at typical usage.

### 4. GitHub repo secrets
Push this folder to a new GitHub repo, then under
**Settings → Secrets and variables → Actions**, add:
- `YOUTUBE_CLIENT_SECRET` (contents of client_secret.json)
- `YOUTUBE_TOKEN` (contents of token.json, from auth_setup.py)
- `PEXELS_API_KEY`
- `ANTHROPIC_API_KEY`

The workflows in `.github/workflows/` handle the rest.

---

## Costs & limits to know about

- **YouTube API quota**: 10,000 units/day by default. One upload costs ~1,600 units,
  so you can comfortably post several times a day, but don't try to post dozens.
- **Copyright**: `visuals.py` only pulls from Pexels, which is free-to-use stock
  footage — safe for monetization. Don't swap in scraped footage from other creators.
- **Monetization gate**: revenue data will read "N/A" until you hit the YouTube
  Partner Program thresholds (1,000 subs + 10M Shorts views/90 days, or 4,000
  public watch hours/12 months + 1,000 subs).
- **This is a starting pipeline, not a guarantee**: nothing can promise views.
  The feedback loop (insights.py) is designed to help you iterate faster, not
  to bypass the fact that content quality and audience fit still matter most.

## Running it manually (testing before you automate)

```bash
pip install -r requirements.txt
python auth_setup.py          # one-time
python src/main.py            # runs the full daily pipeline once
python src/weekly_report.py   # pulls analytics + writes insights
```
