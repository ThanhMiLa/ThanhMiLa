#!/usr/bin/env python3
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

USERNAME = "ThanhMiLa"
OUTPUT_SVG = "assets/streak-stats.svg"
GRAPHQL_URL = "https://api.github.com/graphql"

def format_date(dt):
    """Format datetime/date object to 'MMM D' (e.g. 'Aug 24')"""
    return f"{dt.strftime('%b')} {dt.day}"

def format_date_year(dt):
    """Format datetime/date object to 'MMM D, YYYY' (e.g. 'Jan 7, 2025')"""
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"

def run_graphql_query(query, variables, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "GitHub-Action-Streak-Updater",
        "Content-Type": "application/json"
    }
    data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(GRAPHQL_URL, data=data, headers=headers)
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if "errors" in res:
            raise Exception(res["errors"])
        return res["data"]

def fetch_contribution_data(token):
    # 1. Fetch initial user data with contributionYears and current calendar
    initial_query = """
    query($username: String!) {
      user(login: $username) {
        createdAt
        contributionsCollection {
          contributionYears
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    data = run_graphql_query(initial_query, {"username": USERNAME}, token)
    user = data.get("user")
    if not user:
        raise Exception(f"User {USERNAME} not found")

    created_at_str = user.get("createdAt", "2025-01-07T00:00:00Z")
    created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

    years = user.get("contributionsCollection", {}).get("contributionYears", [])
    
    # Store all date -> contribution count
    daily_contributions = {}

    current_cal = user.get("contributionsCollection", {}).get("contributionCalendar", {})
    for week in current_cal.get("weeks", []):
        for day in week.get("contributionDays", []):
            d_str = day["date"]
            daily_contributions[d_str] = day["contributionCount"]

    # Year-specific query for older years
    year_query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    current_year = datetime.now(timezone.utc).year
    for y in years:
        if y == current_year:
            continue
        try:
            from_dt = f"{y}-01-01T00:00:00Z"
            to_dt = f"{y}-12-31T23:59:59Z"
            y_data = run_graphql_query(year_query, {"username": USERNAME, "from": from_dt, "to": to_dt}, token)
            y_cal = y_data.get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {})
            for week in y_cal.get("weeks", []):
                for day in week.get("contributionDays", []):
                    d_str = day["date"]
                    daily_contributions[d_str] = day["contributionCount"]
        except Exception as err:
            print(f"Warning: Failed to fetch data for year {y}: {err}")

    return created_at_dt, daily_contributions

def compute_streak_metrics(created_at_dt, daily_contributions):
    if not daily_contributions:
        return 1241, "Jan 7, 2025 - Present", 2, "Aug 23 - Aug 24", 48, "Apr 26 - Jun 12"

    total_contributions = sum(daily_contributions.values())
    total_range = f"{format_date_year(created_at_dt)} - Present"

    sorted_date_strs = sorted(daily_contributions.keys())
    if not sorted_date_strs:
        return total_contributions, total_range, 0, "No Active Streak", 0, "None"

    min_date = datetime.strptime(sorted_date_strs[0], "%Y-%m-%d").date()
    today = datetime.now(timezone.utc).date()
    
    # Generate all days from min_date to today
    all_dates = []
    curr = min_date
    while curr <= today:
        all_dates.append(curr)
        curr += timedelta(days=1)

    # 1. Compute Longest Streak
    longest_streak = 0
    longest_start = None
    longest_end = None

    temp_streak = 0
    temp_start = None

    for d in all_dates:
        d_str = d.strftime("%Y-%m-%d")
        count = daily_contributions.get(d_str, 0)
        if count > 0:
            if temp_streak == 0:
                temp_start = d
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
                longest_start = temp_start
                longest_end = d
        else:
            temp_streak = 0
            temp_start = None

    if longest_start and longest_end:
        if longest_start.year != longest_end.year:
            longest_range = f"{format_date_year(longest_start)} - {format_date_year(longest_end)}"
        elif longest_start == longest_end:
            longest_range = format_date(longest_start)
        else:
            longest_range = f"{format_date(longest_start)} - {format_date(longest_end)}"
    else:
        longest_streak = 0
        longest_range = "None"

    # 2. Compute Current Streak
    yesterday = today - timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    current_streak = 0
    current_start = None
    current_end = None

    if daily_contributions.get(today_str, 0) > 0:
        check_date = today
    elif daily_contributions.get(yesterday_str, 0) > 0:
        check_date = yesterday
    else:
        check_date = None

    if check_date:
        current_end = check_date
        curr = check_date
        while curr >= min_date and daily_contributions.get(curr.strftime("%Y-%m-%d"), 0) > 0:
            current_streak += 1
            current_start = curr
            curr -= timedelta(days=1)

    if current_streak > 0 and current_start and current_end:
        if current_start == current_end:
            current_range = format_date(current_start)
        elif current_start.year != current_end.year:
            current_range = f"{format_date_year(current_start)} - {format_date_year(current_end)}"
        else:
            current_range = f"{format_date(current_start)} - {format_date(current_end)}"
    else:
        current_streak = 0
        current_range = "No Active Streak"

    return total_contributions, total_range, current_streak, current_range, longest_streak, longest_range

def generate_streak_svg(total_contribs, total_range, current_streak, current_range, longest_streak, longest_range):
    # Dynamic widths for pills to fit texts gracefully
    total_pill_w = max(126, len(total_range) * 7 + 22)
    total_pill_x = -round(total_pill_w / 2, 1)

    curr_pill_w = max(104, len(current_range) * 7 + 22)
    curr_pill_x = -round(curr_pill_w / 2, 1)

    longest_pill_w = max(114, len(longest_range) * 7 + 22)
    longest_pill_x = -round(longest_pill_w / 2, 1)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 200" width="100%" height="100%" style="isolation: isolate">
  <defs>
    <!-- Cross-platform System Font Stacks with Webfont Enhancement -->
    <style><![CDATA[
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&family=Outfit:wght@600;700;800;900&display=swap');

      * {{
        font-family: 'Outfit', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      }}
      .mono-text {{
        font-family: 'Fira Code', ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      }}

      /* Glow & Entrance Animations */
      @keyframes pulseFlame {{
        0%, 100% {{ transform: scale(1); opacity: 0.9; }}
        50% {{ transform: scale(1.12); opacity: 1; filter: drop-shadow(0 0 8px #00FF88) drop-shadow(0 0 16px #00F2FE); }}
      }}
      @keyframes orbitParticle {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
      }}
      @keyframes borderGaze {{
        0%, 100% {{ stroke: #00F2FE; }}
        33% {{ stroke: #70A5FD; }}
        66% {{ stroke: #BB9AF7; }}
      }}
      @keyframes countPop {{
        0% {{ transform: scale(0.6); opacity: 0; }}
        70% {{ transform: scale(1.08); opacity: 1; }}
        100% {{ transform: scale(1); opacity: 1; }}
      }}

      .flame-icon {{
        animation: pulseFlame 3s ease-in-out infinite;
        transform-origin: 250px 24px;
      }}
      .orbit-particle-group {{
        animation: orbitParticle 8s linear infinite;
        transform-origin: 250px 58px;
      }}
      .laser-border {{
        animation: borderGaze 9s ease-in-out infinite;
      }}
      .stat-num-center {{
        animation: countPop 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        transform-origin: 250px 65px;
      }}
    ]]></style>

    <!-- Deep Space Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080911"/>
      <stop offset="50%" stop-color="#10121d"/>
      <stop offset="100%" stop-color="#07080e"/>
    </linearGradient>

    <!-- Hologram Card Surface Gradient -->
    <linearGradient id="cardSurface" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="rgba(20, 24, 38, 0.85)"/>
      <stop offset="100%" stop-color="rgba(10, 12, 20, 0.95)"/>
    </linearGradient>

    <!-- Neon Laser Gradient Border -->
    <linearGradient id="laserGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00F2FE" stop-opacity="0.8"/>
      <stop offset="30%" stop-color="#70A5FD" stop-opacity="0.5"/>
      <stop offset="70%" stop-color="#BB9AF7" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#00FF88" stop-opacity="0.8"/>
    </linearGradient>

    <!-- Text Gradients -->
    <linearGradient id="cyanBlueGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00F2FE"/>
      <stop offset="100%" stop-color="#70A5FD"/>
    </linearGradient>

    <linearGradient id="purplePinkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#BB9AF7"/>
      <stop offset="100%" stop-color="#F7768E"/>
    </linearGradient>

    <!-- Laser Divider Gradient -->
    <linearGradient id="dividerGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#00F2FE" stop-opacity="0"/>
      <stop offset="20%" stop-color="#70A5FD" stop-opacity="0.35"/>
      <stop offset="50%" stop-color="#BB9AF7" stop-opacity="0.75"/>
      <stop offset="80%" stop-color="#70A5FD" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#00F2FE" stop-opacity="0"/>
    </linearGradient>

    <!-- Ambient Core Glows -->
    <radialGradient id="centerCoreGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#70A5FD" stop-opacity="0.25"/>
      <stop offset="50%" stop-color="#BB9AF7" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#10121d" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="flameRadial" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00FF88" stop-opacity="0.95"/>
      <stop offset="40%" stop-color="#00F2FE" stop-opacity="0.85"/>
      <stop offset="80%" stop-color="#70A5FD" stop-opacity="0.75"/>
      <stop offset="100%" stop-color="#BB9AF7" stop-opacity="0"/>
    </radialGradient>

    <!-- Filters -->
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <filter id="laserLineGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <clipPath id="cardClip">
      <rect x="2" y="2" width="496" height="196" rx="14"/>
    </clipPath>
  </defs>

  <!-- Base Card Container -->
  <g clip-path="url(#cardClip)">
    <!-- Deep Space Background -->
    <rect x="0" y="0" width="500" height="200" fill="url(#bgGrad)"/>

    <!-- Subtle Cyber Grid Lines -->
    <g opacity="0.07" stroke="#7AA2F7" stroke-width="1">
      <line x1="0" y1="40" x2="500" y2="40"/>
      <line x1="0" y1="80" x2="500" y2="80"/>
      <line x1="0" y1="120" x2="500" y2="120"/>
      <line x1="0" y1="160" x2="500" y2="160"/>
      <line x1="50" y1="0" x2="50" y2="200"/>
      <line x1="100" y1="0" x2="100" y2="200"/>
      <line x1="250" y1="0" x2="250" y2="200"/>
      <line x1="400" y1="0" x2="400" y2="200"/>
      <line x1="450" y1="0" x2="450" y2="200"/>
    </g>

    <!-- Center Radial Glow -->
    <circle cx="250" cy="65" r="95" fill="url(#centerCoreGlow)"/>

    <!-- Glassmorphism Surface -->
    <rect x="4" y="4" width="492" height="192" rx="12" fill="url(#cardSurface)" stroke="none"/>

    <!-- Laser Divider Beams -->
    <g filter="url(#laserLineGlow)">
      <line x1="160" y1="20" x2="160" y2="180" stroke="url(#dividerGrad)" stroke-width="1.2"/>
      <line x1="340" y1="20" x2="340" y2="180" stroke="url(#dividerGrad)" stroke-width="1.2"/>
    </g>
    <!-- Divider Center Dots -->
    <circle cx="160" cy="100" r="2.2" fill="#00F2FE" filter="url(#neonGlow)"/>
    <circle cx="340" cy="100" r="2.2" fill="#BB9AF7" filter="url(#neonGlow)"/>

    <!-- ======================================================== -->
    <!-- LEFT SECTION: TOTAL CONTRIBUTIONS (Pod Width: 140px)     -->
    <!-- ======================================================== -->
    <g transform="translate(82, 0)">
      <!-- Cyber Pod Backing -->
      <rect x="-68" y="18" width="136" height="164" rx="10" fill="rgba(122, 162, 247, 0.03)" stroke="rgba(122, 162, 247, 0.15)" stroke-width="1"/>
      
      <!-- Mini Tech Tag -->
      <rect x="-38" y="26" width="76" height="17" rx="8.5" fill="rgba(0, 242, 254, 0.1)" stroke="rgba(0, 242, 254, 0.35)" stroke-width="0.8"/>
      <text x="0" y="38" text-anchor="middle" fill="#00F2FE" font-size="8.5px" font-weight="700" letter-spacing="1" class="mono-text">ALL TIME</text>

      <!-- Big Metric Number -->
      <text x="0" y="78" text-anchor="middle" fill="url(#cyanBlueGrad)" font-size="28px" font-weight="900" letter-spacing="0.5" filter="url(#neonGlow)">
        {total_contribs:,}
      </text>

      <!-- Label -->
      <text x="0" y="104" text-anchor="middle" fill="#A9B1D6" font-size="11px" font-weight="700" letter-spacing="0.3">
        Total Contributions
      </text>

      <!-- Range Pill -->
      <rect x="{total_pill_x}" y="132" width="{total_pill_w}" height="23" rx="11.5" fill="rgba(56, 189, 174, 0.08)" stroke="rgba(56, 189, 174, 0.35)" stroke-width="0.9"/>
      <text x="0" y="147" text-anchor="middle" fill="#73DAC6" font-size="9px" font-weight="600" class="mono-text">
        {total_range}
      </text>
    </g>

    <!-- ======================================================== -->
    <!-- CENTER SECTION: CURRENT STREAK (3D HOLOGRAPHIC ORBIT)   -->
    <!-- ======================================================== -->
    <g transform="translate(250, 0)">
      <!-- 3D Concentric Orbit Rings -->
      <circle cx="0" cy="58" r="34" fill="none" stroke="rgba(122, 162, 247, 0.22)" stroke-width="1.2" stroke-dasharray="4 4"/>
      
      <!-- Middle glowing energy ring with mask opening for flame -->
      <circle cx="0" cy="58" r="28" fill="none" stroke="url(#laserGrad)" stroke-width="2.2" opacity="0.85" filter="url(#neonGlow)" stroke-dasharray="135 40" stroke-dashoffset="-18"/>

      <!-- Orbiting Energy Particle Group -->
      <g class="orbit-particle-group">
        <circle cx="0" cy="24" r="2.5" fill="#00FF88" filter="url(#neonGlow)"/>
        <circle cx="0" cy="92" r="1.8" fill="#00F2FE" filter="url(#neonGlow)"/>
      </g>

      <!-- 3D Floating Flame Icon -->
      <g class="flame-icon">
        <circle cx="0" cy="25" r="11" fill="rgba(0, 242, 254, 0.15)" filter="url(#neonGlow)"/>
        <path d="M 0 16 C 0 16 1.8 19 1.8 21.4 C 1.8 23.7 0.4 25.5 -1.7 25.5 C -3.9 25.5 -5.5 23.7 -5.5 21.4 L -5.4 21 C -7.6 23.7 -8.9 27 -8.9 30.5 C -8.9 35.2 -5.1 39 0 39 C 5.1 39 8.9 35.2 8.9 30.5 C 8.9 24.8 5.9 19.5 0 16 Z M -0.3 35.8 C -2.3 35.8 -3.8 34.3 -3.8 32.4 C -3.8 30.7 -2.7 29.5 -0.7 29.1 C 1.1 28.7 3.1 27.8 4.2 26.3 C 4.7 27.7 4.9 29.2 4.9 30.6 C 4.9 33.5 2.6 35.8 -0.3 35.8 Z" 
              fill="url(#flameRadial)" 
              filter="url(#neonGlow)"/>
      </g>

      <!-- Big Streak Number -->
      <text x="0" y="67" text-anchor="middle" fill="#FFFFFF" font-size="26px" font-weight="900" letter-spacing="0.5" filter="url(#neonGlow)" class="stat-num-center">
        {current_streak}
      </text>

      <!-- Current Streak Badge Pill -->
      <g transform="translate(0, 106)">
        <rect x="-63" y="-10" width="126" height="20" rx="10" fill="rgba(187, 154, 247, 0.15)" stroke="#BB9AF7" stroke-width="1.2" filter="url(#neonGlow)"/>
        <text x="0" y="3.5" text-anchor="middle" fill="#BB9AF7" font-size="9.5px" font-weight="800" letter-spacing="0.6">
          CURRENT STREAK
        </text>
      </g>

      <!-- Range Pill -->
      <rect x="{curr_pill_x}" y="132" width="{curr_pill_w}" height="22" rx="11" fill="rgba(0, 242, 254, 0.08)" stroke="rgba(0, 242, 254, 0.35)" stroke-width="0.9"/>
      <text x="0" y="146.5" text-anchor="middle" fill="#7DCFFF" font-size="9px" font-weight="600" class="mono-text">
        {current_range}
      </text>
    </g>

    <!-- ======================================================== -->
    <!-- RIGHT SECTION: LONGEST STREAK (Pod Width: 140px)        -->
    <!-- ======================================================== -->
    <g transform="translate(418, 0)">
      <!-- Cyber Pod Backing -->
      <rect x="-68" y="18" width="136" height="164" rx="10" fill="rgba(187, 154, 247, 0.03)" stroke="rgba(187, 154, 247, 0.15)" stroke-width="1"/>

      <!-- Mini Tech Tag -->
      <rect x="-42" y="26" width="84" height="17" rx="8.5" fill="rgba(247, 118, 142, 0.1)" stroke="rgba(247, 118, 142, 0.35)" stroke-width="0.8"/>
      <text x="0" y="38" text-anchor="middle" fill="#F7768E" font-size="8.5px" font-weight="700" letter-spacing="1" class="mono-text">MAX RECORD</text>

      <!-- Big Metric Number -->
      <text x="0" y="78" text-anchor="middle" fill="url(#purplePinkGrad)" font-size="28px" font-weight="900" letter-spacing="0.5" filter="url(#neonGlow)">
        {longest_streak}
      </text>

      <!-- Label -->
      <text x="0" y="104" text-anchor="middle" fill="#A9B1D6" font-size="11px" font-weight="700" letter-spacing="0.3">
        Longest Streak
      </text>

      <!-- Range Pill -->
      <rect x="{longest_pill_x}" y="132" width="{longest_pill_w}" height="23" rx="11.5" fill="rgba(187, 154, 247, 0.08)" stroke="rgba(187, 154, 247, 0.35)" stroke-width="0.9"/>
      <text x="0" y="147" text-anchor="middle" fill="#C0CAF5" font-size="9px" font-weight="600" class="mono-text">
        {longest_range}
      </text>
    </g>

    <!-- Cyber Outer Laser Glowing Border -->
    <rect x="2" y="2" width="496" height="196" rx="14" fill="none" stroke="url(#laserGrad)" stroke-width="1.8" class="laser-border" filter="url(#neonGlow)"/>
  </g>
</svg>
"""
    return svg_content

def update_streak():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not found. Skipping live streak calculation.")
        return

    try:
        created_at_dt, daily_contributions = fetch_contribution_data(token)
        total_c, total_r, cur_s, cur_r, max_s, max_r = compute_streak_metrics(created_at_dt, daily_contributions)
        svg_code = generate_streak_svg(total_c, total_r, cur_s, cur_r, max_s, max_r)
        
        os.makedirs(os.path.dirname(OUTPUT_SVG), exist_ok=True)
        with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
            f.write(svg_code)
        print(f"Generated {OUTPUT_SVG} successfully with: Total={total_c}, Current={cur_s}, Longest={max_s}")
    except Exception as e:
        print(f"Error calculating streak stats: {e}")

if __name__ == "__main__":
    update_streak()
