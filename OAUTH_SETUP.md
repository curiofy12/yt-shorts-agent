# Google Cloud / YouTube API Setup — Detailed Walkthrough

This is the fiddliest part of the whole setup, but it's a one-time process.
Budget ~20 minutes.

---

## Step 1: Create a Google Cloud project

1. Go to https://console.cloud.google.com
2. Log in with the **same Google account that owns your YouTube channel**
   (this matters — you can't authorize a channel you don't own).
3. Top-left, click the project dropdown → **New Project**.
4. Name it something like `yt-shorts-agent` → **Create**.
5. Wait a few seconds for it to finish, then select it from the project dropdown.

## Step 2: Enable the two APIs you need

1. In the left sidebar (or search bar at top), go to **APIs & Services → Library**.
2. Search for **"YouTube Data API v3"** → click it → **Enable**.
3. Go back to the Library, search for **"YouTube Analytics API"** → click it → **Enable**.

## Step 3: Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. User Type: choose **External** → Create.
3. Fill in the required fields:
   - App name: anything, e.g. "YT Shorts Agent"
   - User support email: your email
   - Developer contact email: your email
4. Click through **Save and Continue** on the Scopes page (you don't need to
   add scopes here — the script requests them directly).
5. On the **Test users** page, click **Add Users** and add the Gmail address
   of the account that owns your YouTube channel. This is required while
   the app is in "Testing" mode (it will be — that's fine, you don't need
   to publish it publicly, since you're the only user).
6. Save and continue through to the summary, then **Back to Dashboard**.

## Step 4: Create OAuth credentials

1. Go to **APIs & Services → Credentials**.
2. Click **+ Create Credentials → OAuth client ID**.
3. Application type: **Desktop app**.
4. Name: anything, e.g. "yt-agent-desktop".
5. Click **Create**. A popup shows your Client ID and Secret — click
   **Download JSON**.
6. Rename the downloaded file to `client_secret.json` and put it in the
   root of your `yt_agent` project folder (same level as `README.md`).

## Step 5: Run the local authorization

1. On your own computer (not GitHub Actions — this step needs a real browser):
   ```bash
   cd yt_agent
   pip install -r requirements.txt
   python auth_setup.py
   ```
2. A browser window opens asking you to log in. Use the same Google account
   that owns the channel.
3. You'll see a warning screen: **"Google hasn't verified this app"**. This
   is expected — it's your own app, in Testing mode. Click **Advanced** →
   **"Go to yt-shorts-agent (unsafe)"**. ("Unsafe" here just means Google
   hasn't reviewed it; you wrote it, so this is fine.)
4. Grant all the requested permissions (upload videos, read analytics, etc).
5. The browser will show "The authentication flow has completed" — you can
   close the tab. Back in your terminal, you'll see:
   ```
   Saved credentials to token.json
   ```
6. A `token.json` file now exists in your project folder. **This is the
   file that lets the automation act as you without logging in again.**

## Step 6: Add both files as GitHub secrets

1. Push your `yt_agent` folder to a new GitHub repository (private repo
   recommended, since these are your credentials' downstream artifacts —
   though the actual secret *values* only ever live in GitHub Secrets, never
   in the repo files themselves — see the warning below).
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**.
3. Create secret `YOUTUBE_CLIENT_SECRET` — paste the **entire contents** of
   your local `client_secret.json` file as the value.
4. Create secret `YOUTUBE_TOKEN` — paste the **entire contents** of your
   local `token.json` file as the value.
5. Also add `ANTHROPIC_API_KEY` and `PEXELS_API_KEY` as secrets the same way.

## ⚠️ Important: don't commit the actual credential files

`client_secret.json` and `token.json` contain live credentials to your
YouTube channel. Add them to `.gitignore` so you never accidentally push
them to the repo in plaintext:

```bash
echo "client_secret.json" >> .gitignore
echo "token.json" >> .gitignore
echo ".env" >> .gitignore
```

The GitHub Actions workflows recreate these files at runtime *from your
encrypted secrets*, so the repo itself never needs to contain them.

## Step 7: Test it

Before trusting the daily cron:
1. Go to your repo's **Actions** tab.
2. Click **Daily Short Post** in the left list → **Run workflow** (this
   uses the `workflow_dispatch` trigger already in the yml) → **Run workflow**.
3. Watch the run log. If it fails, the error will point to which step
   (script generation, TTS, clip fetching, or upload) needs attention —
   most first-run failures are a missing/misnamed secret.

## Token expiry note

The refresh token in `token.json` doesn't expire from time alone, but Google
can invalidate it if: you revoke access in your Google Account security
settings, you change your account password, or the app sits unused for
6+ months while still in "Testing" (unpublished) mode. If uploads start
failing with an auth error after a long gap, just re-run `auth_setup.py`
and update the `YOUTUBE_TOKEN` secret.
