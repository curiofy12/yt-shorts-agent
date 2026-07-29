"""
Run this ONCE, locally, on your own computer (not in GitHub Actions).
It opens a browser window, you log into the Google account that owns the
YouTube channel, and it saves a reusable refresh token to token.json.

Usage:
    python auth_setup.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from config import YOUTUBE_CLIENT_SECRET_PATH, YOUTUBE_TOKEN_PATH, YOUTUBE_SCOPES


def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        YOUTUBE_CLIENT_SECRET_PATH, YOUTUBE_SCOPES
    )
    creds = flow.run_local_server(port=0)

    with open(YOUTUBE_TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"Saved credentials to {YOUTUBE_TOKEN_PATH}")
    print("Add the contents of this file as the YOUTUBE_TOKEN GitHub secret.")


if __name__ == "__main__":
    main()
