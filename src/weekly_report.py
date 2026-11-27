"""
Runs weekly: refreshes stats for all logged videos, writes an insights
report, and regenerates the HTML dashboard.

Triggered by .github/workflows/weekly_insights.yml
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, POSTS_LOG_PATH

from analytics import get_analytics_service, get_video_stats, get_channel_totals
from insights import generate_insights_report
from stats_store import load_stats, save_stats, with_stats

REPORT_PATH = os.path.join(DATA_DIR, "latest_insights.md")
DASHBOARD_PATH = os.path.join(os.path.dirname(DATA_DIR), "dashboard.html")


def load_log():
    if os.path.exists(POSTS_LOG_PATH):
        with open(POSTS_LOG_PATH) as f:
            return json.load(f)
    return []


def refresh_stats(log):
    """Fetches lifetime stats for every logged video into video_stats.json."""
    stats = load_stats()
    service = get_analytics_service()
    ok = 0
    for entry in log:
        vid = entry.get("video_id")
        if not vid:
            continue
        try:
            result = get_video_stats(vid, entry.get("posted_at"), service)
            if "error" not in result:
                stats[vid] = result
                ok += 1
        except Exception as e:
            print(f"[weekly_report] couldn't fetch stats for {vid}: {e}")
    print(f"[weekly_report] refreshed stats for {ok} of {len(log)} videos")
    save_stats(stats)
    return with_stats(log, stats)


def render_dashboard(log, channel_totals, insights_text):
    rows = ""
    for entry in sorted(log, key=lambda e: e.get("posted_at", ""), reverse=True):
        stats = entry.get("stats") or {}
        rows += f"""
        <tr>
          <td>{entry.get('posted_at', '')[:10]}</td>
          <td>{entry.get('title', '')}</td>
          <td>{entry.get('topic', '')}</td>
          <td>{stats.get('views', '-')}</td>
          <td>{stats.get('average_view_duration_sec', '-')}</td>
          <td>{stats.get('average_view_percentage', '-')}</td>
          <td>{stats.get('subscribers_gained', '-')}</td>
          <td>{stats.get('estimated_revenue_usd', '-')}</td>
        </tr>"""

    insights_html = insights_text.replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Channel Dashboard</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; }}
  .totals {{ display: flex; gap: 24px; margin: 20px 0 30px; }}
  .totals div {{ background: #f4f4f5; border-radius: 10px; padding: 14px 18px; }}
  .totals .num {{ font-size: 22px; font-weight: 700; }}
  .totals .label {{ font-size: 12px; color: #666; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; }}
  th {{ color: #666; font-weight: 600; }}
  .insights {{ margin-top: 40px; background: #fafafa; border-radius: 10px; padding: 20px; line-height: 1.6; }}
  .updated {{ color: #999; font-size: 12px; }}
</style>
</head>
<body>
  <h1>Channel Dashboard</h1>
  <p class="updated">Last updated: {datetime.now(timezone.utc).isoformat()}</p>

  <div class="totals">
    <div><div class="num">{channel_totals.get('views', 0)}</div><div class="label">Views (30d)</div></div>
    <div><div class="num">{channel_totals.get('subscribers_gained', 0)}</div><div class="label">Subs gained (30d)</div></div>
    <div><div class="num">{channel_totals.get('estimated_minutes_watched', 0)}</div><div class="label">Minutes watched (30d)</div></div>
  </div>

  <table>
    <tr><th>Date</th><th>Title</th><th>Topic</th><th>Views</th><th>Avg view (s)</th><th>Avg % watched</th><th>Subs gained</th><th>Est. revenue</th></tr>
    {rows}
  </table>

  <div class="insights">
    <h2>Latest insights</h2>
    {insights_html}
  </div>
</body>
</html>"""

    with open(DASHBOARD_PATH, "w") as f:
        f.write(html)


def run():
    log = load_log()
    if not log:
        print("[weekly_report] no posts logged yet, nothing to report.")
        return

    print("[weekly_report] refreshing per-video stats...")
    log = refresh_stats(log)

    print("[weekly_report] pulling channel totals...")
    try:
        channel_totals = get_channel_totals()
    except Exception as e:
        print(f"[weekly_report] couldn't fetch channel totals: {e}")
        channel_totals = {}

    print("[weekly_report] generating insights...")
    # Recent posts plus the all-time top 10, so the analysis sees both
    # what's happening now and what has worked best overall.
    recent = log[-30:]
    recent_ids = {e.get("video_id") for e in recent}
    top = sorted(
        (e for e in log if isinstance(e.get("stats"), dict) and e.get("video_id") not in recent_ids),
        key=lambda e: e["stats"].get("views", 0),
        reverse=True,
    )[:10]
    insights_text = generate_insights_report(top + recent)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(insights_text)

    print("[weekly_report] rendering dashboard...")
    render_dashboard(log, channel_totals, insights_text)

    print("[weekly_report] done.")


if __name__ == "__main__":
    run()
