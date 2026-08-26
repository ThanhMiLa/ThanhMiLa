#!/usr/bin/env python3
import os
import json
import math
import urllib.request

USERNAME = "Thanh_MiLa"
OUTPUT_SVG = "assets/leetcode-stats.svg"
GRAPHQL_URL = "https://leetcode.com/graphql"

def fetch_leetcode_graphql():
    query = """
    query userProblemsSolved($username: String!) {
      allQuestionsCount {
        difficulty
        count
      }
      matchedUser(username: $username) {
        submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
        profile {
          ranking
        }
      }
    }
    """
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": {"username": USERNAME}}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        data = res.get("data", {})
        matched_user = data.get("matchedUser")
        if not matched_user:
            raise Exception("LeetCode user not found")
        
        all_counts = {item["difficulty"]: item["count"] for item in data.get("allQuestionsCount", [])}
        ac_counts = {item["difficulty"]: item["count"] for item in matched_user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])}
        
        ranking = matched_user.get("profile", {}).get("ranking", 2300000)
        
        return {
            "ranking": ranking,
            "total_solved": ac_counts.get("All", 63),
            "total_questions": all_counts.get("All", 4000),
            "easy_solved": ac_counts.get("Easy", 59),
            "easy_total": all_counts.get("Easy", 961),
            "med_solved": ac_counts.get("Medium", 3),
            "med_total": all_counts.get("Medium", 2105),
            "hard_solved": ac_counts.get("Hard", 1),
            "hard_total": all_counts.get("Hard", 967)
        }

def fetch_leetcode_fallback():
    url = f"https://leetcode-stats-api.herokuapp.com/{USERNAME}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if res.get("status") != "success":
            raise Exception("Fallback API response error")
        return {
            "ranking": res.get("ranking", 2300000),
            "total_solved": res.get("totalSolved", 63),
            "total_questions": res.get("totalQuestions", 4000),
            "easy_solved": res.get("easySolved", 59),
            "easy_total": res.get("totalEasy", 961),
            "med_solved": res.get("mediumSolved", 3),
            "med_total": res.get("totalMedium", 2105),
            "hard_solved": res.get("hardSolved", 1),
            "hard_total": res.get("totalHard", 967)
        }

def generate_svg(stats):
    ranking_str = f"#{stats['ranking']:,}"
    rank_pill_w = max(106, len(ranking_str) * 7.5 + 24)
    rank_pill_x = -rank_pill_w
    rank_text_x = round(-rank_pill_w / 2, 1)

    total_solved = stats["total_solved"]
    total_q = stats["total_questions"]

    # Gauge arc calculation (circumference = 2 * pi * 42 ~= 263.89)
    gauge_circ = 263.89
    gauge_percent = min(1.0, max(0.02, total_solved / max(1, total_q)))
    # Display amplified arc length for visual appeal while keeping ratio proportional
    arc_length = round(gauge_percent * 240 + 25, 1)
    dash_space = round(gauge_circ - arc_length, 1)

    # Progress bars width (max 292px)
    max_bar_w = 292
    easy_pct = stats["easy_solved"] / max(1, stats["easy_total"])
    med_pct = stats["med_solved"] / max(1, stats["med_total"])
    hard_pct = stats["hard_solved"] / max(1, stats["hard_total"])

    easy_bar_w = max(12, min(max_bar_w, round(easy_pct * max_bar_w)))
    med_bar_w = max(10, min(max_bar_w, round(med_pct * max_bar_w)))
    hard_bar_w = max(8, min(max_bar_w, round(hard_pct * max_bar_w)))

    easy_dot_x = 14 + easy_bar_w
    med_dot_x = 14 + med_bar_w
    hard_dot_x = 14 + hard_bar_w

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

      /* Glow & Animation Effects */
      @keyframes borderGaze {{
        0%, 100% {{ stroke: #00F2FE; }}
        33% {{ stroke: #70A5FD; }}
        66% {{ stroke: #BB9AF7; }}
      }}
      @keyframes pulseMeter {{
        0%, 100% {{ transform: scale(1); opacity: 0.9; }}
        50% {{ transform: scale(1.04); opacity: 1; }}
      }}
      @keyframes shimmerBar {{
        0% {{ transform: translateX(-60px); opacity: 0; }}
        50% {{ opacity: 0.7; }}
        100% {{ transform: translateX(320px); opacity: 0; }}
      }}

      .laser-border {{
        animation: borderGaze 9s ease-in-out infinite;
      }}
      .shimmer-effect {{
        animation: shimmerBar 4s ease-in-out infinite;
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
      <stop offset="0%" stop-color="#00F2FE" stop-opacity="0.85"/>
      <stop offset="30%" stop-color="#70A5FD" stop-opacity="0.55"/>
      <stop offset="70%" stop-color="#BB9AF7" stop-opacity="0.75"/>
      <stop offset="100%" stop-color="#00FF88" stop-opacity="0.85"/>
    </linearGradient>

    <!-- Title Gradient -->
    <linearGradient id="titleGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="60%" stop-color="#F0F6FC"/>
      <stop offset="100%" stop-color="#70A5FD"/>
    </linearGradient>

    <!-- Progress Bar Gradients -->
    <linearGradient id="easyGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00FF88"/>
      <stop offset="100%" stop-color="#38BDAE"/>
    </linearGradient>

    <linearGradient id="medGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFD166"/>
      <stop offset="100%" stop-color="#FF9E64"/>
    </linearGradient>

    <linearGradient id="hardGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF5D8F"/>
      <stop offset="100%" stop-color="#DC382D"/>
    </linearGradient>

    <!-- LeetCode Logo Gradient -->
    <linearGradient id="lcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFA116"/>
      <stop offset="100%" stop-color="#FF6B00"/>
    </linearGradient>

    <!-- Ambient Core Glow -->
    <radialGradient id="meterGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FFA116" stop-opacity="0.25"/>
      <stop offset="60%" stop-color="#FF6B00" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#10121d" stop-opacity="0"/>
    </radialGradient>

    <!-- Filters -->
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%">
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
    <rect x="0" y="0" width="500" height="200" fill="url(#spaceBg)"/>

    <!-- Subtle Cyber Grid Lines -->
    <g opacity="0.07" stroke="#7AA2F7" stroke-width="1">
      <line x1="0" y1="40" x2="500" y2="40"/>
      <line x1="0" y1="80" x2="500" y2="80"/>
      <line x1="0" y1="120" x2="500" y2="120"/>
      <line x1="0" y1="160" x2="500" y2="160"/>
      <line x1="50" y1="0" x2="50" y2="200"/>
      <line x1="140" y1="0" x2="140" y2="200"/>
      <line x1="250" y1="0" x2="250" y2="200"/>
      <line x1="375" y1="0" x2="375" y2="200"/>
      <line x1="450" y1="0" x2="450" y2="200"/>
    </g>

    <!-- Glassmorphism Surface -->
    <rect x="4" y="4" width="492" height="192" rx="12" fill="url(#cardSurface)" stroke="none"/>

    <!-- Ambient Core Glow behind circular gauge -->
    <circle cx="85" cy="116" r="60" fill="url(#meterGlow)"/>

    <!-- ======================================================== -->
    <!-- HEADER: LEETCODE LOGO & USERNAME & RANK                  -->
    <!-- ======================================================== -->
    <g transform="translate(30, 20)">
      <!-- LeetCode Cyber Icon -->
      <g transform="translate(0, 0)">
        <path d="M 14 3 L 5 12 L 14 21" fill="none" stroke="url(#lcGrad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#neonGlow)"/>
        <line x1="6" y1="12" x2="22" y2="12" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="22" cy="12" r="2" fill="#FFA116" filter="url(#neonGlow)"/>
      </g>

      <!-- Username -->
      <text x="32" y="16.5" fill="url(#titleGrad)" font-size="16.5px" font-weight="900" letter-spacing="0.6" filter="url(#softGlow)">
        {USERNAME}
      </text>

      <!-- Global Rank Badge -->
      <g transform="translate(440, 2)">
        <rect x="{rank_pill_x}" y="0" width="{rank_pill_w}" height="20" rx="10" fill="rgba(122, 162, 247, 0.08)" stroke="rgba(122, 162, 247, 0.3)" stroke-width="0.9"/>
        <text x="{rank_text_x}" y="14" text-anchor="middle" fill="#A9B1D6" font-size="10px" font-weight="700" letter-spacing="0.5" class="mono-text">
          {ranking_str}
        </text>
      </g>
    </g>

    <!-- ======================================================== -->
    <!-- LEFT: CIRCULAR TOTAL SOLVED GAUGE (Center: 85, 120)      -->
    <!-- ======================================================== -->
    <g transform="translate(85, 120)">
      <!-- Outer Track Ring -->
      <circle cx="0" cy="0" r="42" fill="none" stroke="#161928" stroke-width="6"/>
      <circle cx="0" cy="0" r="42" fill="none" stroke="rgba(122, 162, 247, 0.15)" stroke-width="6" stroke-dasharray="3 5"/>

      <!-- Active Progress Arc -->
      <circle cx="0" cy="0" r="42" fill="none" stroke="url(#lcGrad)" stroke-width="6" stroke-linecap="round" stroke-dasharray="{arc_length} {dash_space}" stroke-dashoffset="10" filter="url(#neonGlow)"/>

      <!-- Indicator Dot on Arc -->
      <circle cx="2" cy="-42" r="3.5" fill="#FFFFFF" filter="url(#neonGlow)"/>

      <!-- Total Solved Number -->
      <text x="0" y="7" text-anchor="middle" fill="#FFFFFF" font-size="28px" font-weight="900" letter-spacing="0.5" filter="url(#neonGlow)">
        {total_solved}
      </text>

      <!-- Solved Label Pill -->
      <g transform="translate(0, 24)">
        <rect x="-24" y="-7" width="48" height="14" rx="7" fill="rgba(255, 161, 22, 0.12)" stroke="rgba(255, 161, 22, 0.35)" stroke-width="0.8"/>
        <text x="0" y="3.5" text-anchor="middle" fill="#FFA116" font-size="8px" font-weight="800" letter-spacing="0.8">
          SOLVED
        </text>
      </g>
    </g>

    <!-- Laser Divider Beam -->
    <line x1="145" y1="62" x2="145" y2="178" stroke="rgba(122, 162, 247, 0.18)" stroke-width="1" stroke-dasharray="4 4"/>

    <!-- ======================================================== -->
    <!-- RIGHT: DIFFICULTY BREAKDOWN BARS                         -->
    <!-- ======================================================== -->

    <!-- ─── EASY ─── -->
    <g transform="translate(162, 60)">
      <!-- Glowing Dot -->
      <circle cx="4" cy="11" r="3" fill="#00FF88" filter="url(#softGlow)"/>
      <!-- Label -->
      <text x="14" y="15" fill="#FFFFFF" font-size="12.5px" font-weight="700">Easy</text>
      <!-- Count Ratio -->
      <text x="306" y="15" text-anchor="end" fill="#C0CAF5" font-size="11px" font-weight="600" class="mono-text">
        <tspan fill="#00FF88" font-weight="700">{stats['easy_solved']}</tspan> / {stats['easy_total']}
      </text>
      <!-- Progress Bar Track -->
      <rect x="14" y="22" width="292" height="6" rx="3" fill="#151828"/>
      <!-- Progress Bar Fill -->
      <rect x="14" y="22" width="{easy_bar_w}" height="6" rx="3" fill="url(#easyGrad)" filter="url(#softGlow)"/>
      <circle cx="{easy_dot_x}" cy="25" r="2" fill="#FFFFFF"/>
    </g>

    <!-- ─── MEDIUM ─── -->
    <g transform="translate(162, 102)">
      <!-- Glowing Dot -->
      <circle cx="4" cy="11" r="3" fill="#FFB800" filter="url(#softGlow)"/>
      <!-- Label -->
      <text x="14" y="15" fill="#FFFFFF" font-size="12.5px" font-weight="700">Medium</text>
      <!-- Count Ratio -->
      <text x="306" y="15" text-anchor="end" fill="#C0CAF5" font-size="11px" font-weight="600" class="mono-text">
        <tspan fill="#FFB800" font-weight="700">{stats['med_solved']}</tspan> / {stats['med_total']}
      </text>
      <!-- Progress Bar Track -->
      <rect x="14" y="22" width="292" height="6" rx="3" fill="#151828"/>
      <!-- Progress Bar Fill -->
      <rect x="14" y="22" width="{med_bar_w}" height="6" rx="3" fill="url(#medGrad)" filter="url(#softGlow)"/>
      <circle cx="{med_dot_x}" cy="25" r="1.8" fill="#FFFFFF"/>
    </g>

    <!-- ─── HARD ─── -->
    <g transform="translate(162, 144)">
      <!-- Glowing Dot -->
      <circle cx="4" cy="11" r="3" fill="#F7768E" filter="url(#softGlow)"/>
      <!-- Label -->
      <text x="14" y="15" fill="#FFFFFF" font-size="12.5px" font-weight="700">Hard</text>
      <!-- Count Ratio -->
      <text x="306" y="15" text-anchor="end" fill="#C0CAF5" font-size="11px" font-weight="600" class="mono-text">
        <tspan fill="#F7768E" font-weight="700">{stats['hard_solved']}</tspan> / {stats['hard_total']}
      </text>
      <!-- Progress Bar Track -->
      <rect x="14" y="22" width="292" height="6" rx="3" fill="#151828"/>
      <!-- Progress Bar Fill -->
      <rect x="14" y="22" width="{hard_bar_w}" height="6" rx="3" fill="url(#hardGrad)" filter="url(#softGlow)"/>
      <circle cx="{hard_dot_x}" cy="25" r="1.8" fill="#FFFFFF"/>
    </g>

    <!-- Cyber Outer Laser Glowing Border -->
    <rect x="2" y="2" width="496" height="196" rx="14" fill="none" stroke="url(#laserGrad)" stroke-width="1.8" class="laser-border" filter="url(#neonGlow)"/>
  </g>
</svg>
"""
    return svg_content

def update_leetcode():
    stats = None
    try:
        stats = fetch_leetcode_graphql()
        print("Fetched live LeetCode stats via GraphQL successfully!")
    except Exception as e:
        print(f"GraphQL failed: {e}. Trying fallback REST API...")
        try:
            stats = fetch_leetcode_fallback()
            print("Fetched LeetCode stats via fallback REST API successfully!")
        except Exception as e2:
            print(f"Fallback failed: {e2}")

    if not stats:
        print("Could not fetch new LeetCode stats, skipping file update.")
        return

    svg_code = generate_svg(stats)
    os.makedirs(os.path.dirname(OUTPUT_SVG), exist_ok=True)
    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_code)
    print(f"Generated {OUTPUT_SVG} successfully with: Total={stats['total_solved']} (Easy:{stats['easy_solved']}, Med:{stats['med_solved']}, Hard:{stats['hard_solved']}) Rank={stats['ranking']}")

if __name__ == "__main__":
    update_leetcode()
