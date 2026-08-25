#!/usr/bin/env python3
import os
import re
import html
import urllib.request
import json
from datetime import datetime, timezone

USERNAME = "ThanhMiLa"
README_PATH = "README.md"
SVG_OUTPUT_PATH = "assets/recent-activity.svg"
MAX_ITEMS = 4

def time_ago(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        elif seconds < 604800:
            return f"{seconds // 86400}d ago"
        else:
            return dt.strftime("%b %d")
    except Exception:
        return ""

def fetch_events():
    url = f"https://api.github.com/users/{USERNAME}/events/public"
    headers = {
        "User-Agent": "GitHub-Action-Activity-Updater",
        "Accept": "application/vnd.github.v3+json"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching events: {e}")
        return []

def get_commit_info(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}"
    headers = {
        "User-Agent": "GitHub-Action-Activity-Updater",
        "Accept": "application/vnd.github.v3+json"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            msg = data.get("commit", {}).get("message", "").split("\n")[0]
            date = data.get("commit", {}).get("author", {}).get("date", "")
            html_url = data.get("html_url", f"https://github.com/{repo}/commit/{sha}")
            return msg, date, html_url
    except Exception:
        return None, None, None

def get_commit_icon(msg):
    m = msg.lower()
    if m.startswith("feat"):
        return "✨"
    elif m.startswith("fix"):
        return "🐛"
    elif m.startswith("docs"):
        return "📝"
    elif m.startswith("perf") or m.startswith("opt"):
        return "⚡"
    elif m.startswith("refactor"):
        return "🔨"
    elif m.startswith("style"):
        return "🎨"
    elif m.startswith("test"):
        return "🧪"
    elif m.startswith("chore"):
        return "🔧"
    return "📦"

def extract_activities(events):
    results = []
    seen_keys = set()

    for ev in events:
        ev_type = ev.get("type")
        repo = ev.get("repo", {}).get("name", "")
        payload = ev.get("payload", {})

        if ev_type == "PushEvent":
            head = payload.get("head")
            if head and head not in seen_keys:
                seen_keys.add(head)
                msg, date, commit_url = get_commit_info(repo, head)
                if msg:
                    short_sha = head[:7]
                    ago = time_ago(date)
                    icon = get_commit_icon(msg)
                    results.append({
                        "icon": icon,
                        "sha": short_sha,
                        "msg": msg,
                        "repo": repo,
                        "time": ago,
                        "url": commit_url
                    })

        elif ev_type == "PullRequestEvent":
            pr = payload.get("pull_request", {})
            pr_title = pr.get("title", "").split("\n")[0]
            pr_url = pr.get("html_url", f"https://github.com/{repo}")
            pr_num = pr.get("number", "")
            action = payload.get("action")
            created = ev.get("created_at", "")
            ago = time_ago(created)

            key = f"pr_{repo}_{pr_num}_{action}"
            if key not in seen_keys:
                seen_keys.add(key)
                if action == "closed" and pr.get("merged"):
                    results.append({
                        "icon": "🚀",
                        "sha": f"PR#{pr_num}",
                        "msg": f"Merged: {pr_title}",
                        "repo": repo,
                        "time": ago,
                        "url": pr_url
                    })
                elif action == "opened":
                    results.append({
                        "icon": "🔀",
                        "sha": f"PR#{pr_num}",
                        "msg": f"Opened: {pr_title}",
                        "repo": repo,
                        "time": ago,
                        "url": pr_url
                    })

        if len(results) >= MAX_ITEMS:
            break

    if not results:
        results.append({
            "icon": "⚡",
            "sha": "init",
            "msg": "Building and shipping new backend features",
            "repo": "ThanhMiLa/ThanhMiLa",
            "time": "recent",
            "url": "https://github.com/ThanhMiLa"
        })

    return results

def generate_svg(activities):
    rows_svg = []
    # 4 rows at y = 46, 82, 118, 154
    y_positions = [46, 82, 118, 154]

    for i, act in enumerate(activities[:4]):
        y = y_positions[i]
        icon = act.get("icon", "📦")
        sha = act.get("sha", "code")
        raw_msg = act.get("msg", "")
        # Truncate message cleanly if it's too long
        display_msg = raw_msg if len(raw_msg) <= 42 else f"{raw_msg[:39]}..."
        safe_msg = html.escape(display_msg)
        
        repo_full = act.get("repo", "")
        repo_short = html.escape(repo_full.split("/")[-1])
        time_str = html.escape(act.get("time", ""))
        tag_text = f"{repo_short} • {time_str}" if time_str else repo_short

        row = f"""    <!-- Activity Row {i+1} -->
    <g transform="translate(18, {y})">
      <rect x="0" y="0" width="464" height="29" rx="7" fill="rgba(18, 23, 38, 0.7)" stroke="rgba(122, 162, 247, 0.16)" stroke-width="0.8"/>
      <!-- Icon -->
      <text x="16" y="19.5" font-size="13px" text-anchor="middle">{icon}</text>
      <!-- SHA Pill -->
      <rect x="32" y="5.5" width="56" height="18" rx="4" fill="rgba(0, 242, 254, 0.1)" stroke="rgba(0, 242, 254, 0.35)" stroke-width="0.8"/>
      <text x="60" y="18" text-anchor="middle" fill="#7DCFFF" font-size="9.5px" font-weight="700" class="mono-text">{sha}</text>
      <!-- Commit Message -->
      <text x="96" y="18.5" fill="#f0f6fc" font-size="10px" font-weight="600">{safe_msg}</text>
      <!-- Right Tag (Repo & Time) -->
      <text x="452" y="18.5" text-anchor="end" fill="#7AA2F7" font-size="9px" font-weight="600" class="mono-text">{tag_text}</text>
    </g>"""
        rows_svg.append(row)

    rows_block = "\n".join(rows_svg)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 200" width="100%" height="100%" style="isolation: isolate">
  <defs>
    <!-- Fonts & Animations -->
    <style><![CDATA[
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&family=Outfit:wght@600;700;800;900&display=swap');
      * {{
        font-family: 'Outfit', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }}
      .mono-text {{
        font-family: 'Fira Code', ui-monospace, 'SF Mono', monospace;
      }}
      @keyframes borderGaze {{
        0%, 100% {{ stroke: #00F2FE; }}
        33% {{ stroke: #70A5FD; }}
        66% {{ stroke: #BB9AF7; }}
      }}
      @keyframes livePulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.35; transform: scale(0.85); }}
      }}
      .laser-border {{
        animation: borderGaze 9s ease-in-out infinite;
      }}
      .live-dot {{
        animation: livePulse 2s ease-in-out infinite;
        transform-origin: 405px 25px;
      }}
    ]]></style>

    <!-- Deep Space Background Gradient -->
    <linearGradient id="spaceBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080911"/>
      <stop offset="50%" stop-color="#10121d"/>
      <stop offset="100%" stop-color="#07080e"/>
    </linearGradient>

    <!-- Hologram Glass Surface Gradient -->
    <linearGradient id="cardSurface" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="rgba(20, 24, 38, 0.85)"/>
      <stop offset="100%" stop-color="rgba(10, 12, 20, 0.95)"/>
    </linearGradient>

    <!-- Laser Border Gradient -->
    <linearGradient id="laserGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00F2FE" stop-opacity="0.8"/>
      <stop offset="30%" stop-color="#70A5FD" stop-opacity="0.5"/>
      <stop offset="70%" stop-color="#BB9AF7" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#00FF88" stop-opacity="0.8"/>
    </linearGradient>

    <!-- Title Gradient -->
    <linearGradient id="titleGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="50%" stop-color="#70A5FD"/>
      <stop offset="100%" stop-color="#00F2FE"/>
    </linearGradient>

    <clipPath id="cardClip">
      <rect x="2" y="2" width="496" height="196" rx="14"/>
    </clipPath>
  </defs>

  <!-- Base Card Container -->
  <g clip-path="url(#cardClip)">
    <!-- Deep Space Background -->
    <rect x="0" y="0" width="500" height="200" fill="url(#spaceBg)"/>

    <!-- Subtle Cyber Grid Lines -->
    <g opacity="0.07" stroke="#7AA2F7" stroke-width="1">
      <line x1="0" y1="40" x2="500" y2="40"/>
      <line x1="0" y1="80" x2="500" y2="80"/>
      <line x1="0" y1="120" x2="500" y2="120"/>
      <line x1="0" y1="160" x2="500" y2="160"/>
      <line x1="100" y1="0" x2="100" y2="200"/>
      <line x1="250" y1="0" x2="250" y2="200"/>
      <line x1="400" y1="0" x2="400" y2="200"/>
    </g>

    <!-- Glassmorphism Surface -->
    <rect x="4" y="4" width="492" height="192" rx="12" fill="url(#cardSurface)" stroke="none"/>

    <!-- ==================== HEADER ==================== -->
    <g transform="translate(24, 15)">
      <!-- Mini Glowing Cyber Indicator -->
      <circle cx="4" cy="11" r="4" fill="#00FF88"/>
      <circle cx="4" cy="11" r="1.8" fill="#FFFFFF"/>

      <!-- Title Text -->
      <text x="16" y="16" fill="url(#titleGrad)" font-size="15px" font-weight="800" letter-spacing="0.6">
        Recent Activity Feed
      </text>

      <!-- Right HUD Live Tag -->
      <g transform="translate(452, 2)">
        <rect x="-86" y="0" width="86" height="18" rx="9" fill="rgba(0, 255, 136, 0.08)" stroke="rgba(0, 255, 136, 0.35)" stroke-width="0.9"/>
        <circle cx="-74" cy="9" r="2.5" fill="#00FF88" class="live-dot"/>
        <text x="-38" y="13" text-anchor="middle" fill="#73DAC6" font-size="8.5px" font-weight="700" letter-spacing="0.8" class="mono-text">
          LIVE SYNC
        </text>
      </g>
    </g>

    <!-- ==================== ACTIVITY ROWS ==================== -->
{rows_block}

    <!-- Cyber Outer Laser Glowing Border -->
    <rect x="2" y="2" width="496" height="196" rx="14" fill="none" stroke="url(#laserGrad)" stroke-width="2" class="laser-border"/>
  </g>
</svg>"""
    return svg_content

def update_all():
    events = fetch_events()
    if not events:
        print("No events fetched.")
        return

    activities = extract_activities(events)
    svg_code = generate_svg(activities)

    # Write SVG card
    os.makedirs(os.path.dirname(SVG_OUTPUT_PATH), exist_ok=True)
    with open(SVG_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_code)
    print(f"Generated {SVG_OUTPUT_PATH} successfully!")

if __name__ == "__main__":
    update_all()
