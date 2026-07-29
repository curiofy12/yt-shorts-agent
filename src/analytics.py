"""
Pulls per-video performance from the YouTube Analytics API: views, watch
time, average view duration, subscribers gained, and estimated revenue
(only populated once the channel is monetized — otherwise these fields
come back as 0/absent and we report them as "N/A").
"""
import sys
import os
from datetime import date, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import YOUTUBE_TOKEN_PATH, YOUTUBE_SCOPES


def get_analytics_service():
    creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_PATH, YOUTUBE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtubeAnalytics", "v2", credentials=creds)


def get_video_stats(video_id, days_back=7):
    yt_analytics = get_analytics_service()
    end = date.today()
    start = end - timedelta(days=days_back)

    metrics = "views,estimatedMinutesWatched,averageViewDuration,subscribersGained"
    try:
        report = yt_analytics.reports().query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics=metrics,
            filters=f"video=={video_id}",
        ).execute()
    except Exception as e:
        print(f"[analytics] core metrics query failed: {e}")
        return {"video_id": video_id, "error": str(e)}

    row = report.get("rows", [[0, 0, 0, 0]])[0]
    result = {
        "video_id": video_id,
        "views": row[0],
        "estimated_minutes_watched": row[1],
        "average_view_duration_sec": row[2],
        "subscribers_gained": row[3],
        "estimated_revenue_usd": "N/A (not monetized or data delayed)",
    }

    # Revenue query separately — will legitimately fail/zero-out for
    # non-monetized channels, so we don't let it break the whole report.
    try:
        rev_report = yt_analytics.reports().query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics="estimatedRevenue",
            filters=f"video=={video_id}",
        ).execute()
        rev_rows = rev_report.get("rows")
        if rev_rows:
            result["estimated_revenue_usd"] = rev_rows[0][0]
    except Exception:
        pass  # expected for non-monetized channels

    return result


def get_channel_totals(days_back=30):
    yt_analytics = get_analytics_service()
    end = date.today()
    start = end - timedelta(days=days_back)

    report = yt_analytics.reports().query(
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost",
    ).execute()

    row = report.get("rows", [[0, 0, 0, 0]])[0]
    return {
        "period_days": days_back,
        "views": row[0],
        "estimated_minutes_watched": row[1],
        "subscribers_gained": row[2],
        "subscribers_lost": row[3],
    }
