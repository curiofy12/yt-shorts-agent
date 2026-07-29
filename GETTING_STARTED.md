# Getting Started — Complete Setup, Start to Finish

Follow these in order. Total time: ~45-60 minutes, one time only.

---

## Phase 0: What you need before starting

- A YouTube channel (create one at youtube.com if you don't have one yet —
  just needs a Google account)
- A GitHub account (free, github.com)
- A credit card for two small paid services (Anthropic API — pennies per
  video; everything else here is free)

---

## Phase 1: Get your API keys

### 1a. Anthropic API key
1. Go to https://console.anthropic.com and sign up/log in.
2. Go to **Settings → API Keys → Create Key**.
3. Copy the key (starts with `sk-ant-...`) somewhere safe — you won't be
   able to see it again.
Key: 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
4. Go to **Settings → Billing** and add a payment method + a small credit
   balance (a few dollars covers weeks of this pipeline).

### 1b. Pexels API key (free)
1. Go to https://www.pexels.com/api and click **Get Started**.
2. Log in / sign up, fill in the short form about how you'll use it.
3. Your API key appears immediately on your account page. Copy it.
Key: TQKLZD2f5QESUEJtV25KzGhsE5pgErMNPJTxT3oazOHVc86DSRyRt55e

Keep both keys in a notes file for now — you'll paste them into GitHub in Phase 4.

---

## Phase 2: Google Cloud / YouTube API access

This is the fiddliest part. Full detail is in `OAUTH_SETUP.md` inside the
project folder — here's the condensed path:

1. **console.cloud.google.com** → log in with the Google account that
   owns your YouTube channel → create a new project.
2. **APIs & Services → Library** → enable **YouTube Data API v3** and
   **YouTube Analytics API** (search and enable each separately).
3. **APIs & Services → OAuth consent screen** → User type **External** →
   fill in app name + your email → on the Test Users step, add your own
   Google account as a test user → save through to the end.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   → Application type **Desktop app** → Create → **Download JSON**.
5. Rename the downloaded file to `client_secret.json`.

(Full walkthrough with what each screen looks like: `OAUTH_SETUP.md`.)

---

## Phase 3: Set up the project on your computer

1. Download and unzip the `yt_agent.zip` project folder I provided.
2. Install Python 3.11+ if you don't have it (python.org/downloads).
3. Open a terminal in the unzipped `yt_agent` folder and run:
   ```bash
   pip install -r requirements.txt
   ```
4. Put the `client_secret.json` from Phase 2 into this same folder.
5. Run the one-time authorization:
   ```bash
   python auth_setup.py
   ```
   This opens your browser, asks you to log into your channel's Google
   account, warns "Google hasn't verified this app" (expected — click
   **Advanced → Go to [app name] (unsafe)**), and asks you to grant
   permissions. Once done, a `token.json` file appears in the folder.
6. You now have two files you'll need in Phase 4: `client_secret.json`
   and `token.json`. **Do not commit these to GitHub** — they're your
   actual credentials (the `.gitignore` already excludes them).

---

## Phase 4: Push to GitHub and add your secrets

1. On github.com, click **New repository**. Name it (e.g. `yt-shorts-agent`),
   set it to **Private**, create it.
2. Push your local `yt_agent` folder to it:
   ```bash
   cd yt_agent
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/yt-shorts-agent.git
   git push -u origin main
   ```
   (This push will NOT include `client_secret.json` or `token.json` — the
   `.gitignore` blocks them, which is correct and intentional.)
3. In the repo on GitHub: **Settings → Secrets and variables → Actions →
   New repository secret**. Add these four, one at a time:
   - `YOUTUBE_CLIENT_SECRET` → paste the entire contents of your local
     `client_secret.json` file
   - `YOUTUBE_TOKEN` → paste the entire contents of your local `token.json` file
   - `ANTHROPIC_API_KEY` → your key from Phase 1a
   - `PEXELS_API_KEY` → your key from Phase 1b

---

## Phase 5: Test run before trusting it

1. Open `src/upload.py` in the repo (GitHub's web editor is fine) and
   temporarily change `"privacyStatus": "public"` to `"privacyStatus": "private"`.
   Commit that change.
2. Go to the repo's **Actions** tab → click **Daily Short Post** in the
   left sidebar → **Run workflow** → **Run workflow** (green button).
3. Click into the running job and watch the log. This takes a few minutes
   (script generation, TTS, downloading clips, rendering, uploading).
4. If it fails, the log will tell you which step — 90% of first-run
   failures are a secret that's misnamed or has extra whitespace pasted in.
5. If it succeeds, go check the private video on your channel (YouTube
   Studio → Content) — watch it, check the captions/audio/pacing look right.

---

## Phase 6: Go live

1. Once you're happy with a test video, change `privacyStatus` back to
   `"public"` in `src/upload.py` and commit.
2. That's it — the `daily_post.yml` workflow is already scheduled
   (default: 16:00 UTC daily; edit the `cron` line in that file to change
   the time) and will now run and publish automatically.
3. The `weekly_insights.yml` workflow runs every Monday, pulling
   analytics and regenerating `dashboard.html` in your repo with
   performance data and a written insights report.

---

## Phase 7: Check on it periodically

- **Dashboard**: open `dashboard.html` from your repo (download it, or
  use GitHub Pages if you want it as a live URL) to see views, watch
  time, subs, and the latest insights report.
- **Actions tab**: shows a green check or red X for every daily/weekly run.
- **Adjust the niche**: if you want to steer topics instead of fully
  automatic trending, add a repository **variable** (not secret) called
  `CHANNEL_NICHE` with something like `"science facts, psychology, space"`.

---

## If something breaks

Paste me the failed step's log output from the Actions tab and I'll help
you debug it directly.
