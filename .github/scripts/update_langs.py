#!/usr/bin/env python3
"""
⚡ Update Most Used Languages SVG Card
Fetches language statistics from GitHub repositories (GraphQL API with fallback to REST API)
and renders the high-performance 3D Cyber HUD Most Used Languages SVG card.
"""

import os
import re
import json
import urllib.request
import urllib.error
from collections import defaultdict

USERNAME = "ThanhMiLa"
OUTPUT_SVG = "assets/most-used-langs.svg"
GRAPHQL_URL = "https://api.github.com/graphql"

# Predefined high-contrast cyber neon palettes for top languages
LANGUAGE_PALETTES = {
    "TypeScript": {
        "linear": ("#4FACFE", "#00F2FE", "#1E5EA8"),
        "radial": ("#E0FFFF", "#00F2FE", "#0066CC"),
        "badge_color": "#00F2FE",
        "badge_rgb": (0, 242, 254),
    },
    "Java": {
        "linear": ("#FFC048", "#FF9E64", "#ED8B00"),
        "radial": ("#FFF0D0", "#FF9E64", "#C05000"),
        "badge_color": "#FF9E64",
        "badge_rgb": (255, 158, 100),
    },
    "JavaScript": {
        "linear": ("#FFF375", "#FFE600", "#D4B000"),
        "radial": ("#FFFFE0", "#FFE600", "#B8860B"),
        "badge_color": "#FFE600",
        "badge_rgb": (255, 230, 0),
    },
    "Python": {
        "linear": ("#8BB9FE", "#70A5FD", "#2B5B84"),
        "radial": ("#E6F2FF", "#70A5FD", "#1A3A5A"),
        "badge_color": "#70A5FD",
        "badge_rgb": (112, 165, 253),
    },
    "PLpgSQL": {
        "linear": ("#55E6D5", "#38BDAE", "#246888"),
        "radial": ("#E0FFFF", "#38BDAE", "#1B4F72"),
        "badge_color": "#38BDAE",
        "badge_rgb": (56, 189, 174),
    },
    "SQL": {
        "linear": ("#55E6D5", "#38BDAE", "#246888"),
        "radial": ("#E0FFFF", "#38BDAE", "#1B4F72"),
        "badge_color": "#38BDAE",
        "badge_rgb": (56, 189, 174),
    },
    "CSS": {
        "linear": ("#D6B8FF", "#BB9AF7", "#7000FF"),
        "radial": ("#F5EEFF", "#BB9AF7", "#4B0082"),
        "badge_color": "#BB9AF7",
        "badge_rgb": (187, 154, 247),
    },
    "HTML": {
        "linear": ("#FFA07A", "#FF5722", "#A82D0D"),
        "radial": ("#FFE4DD", "#FF5722", "#821E06"),
        "badge_color": "#FF7043",
        "badge_rgb": (255, 112, 67),
    },
    "C++": {
        "linear": ("#FF7EB6", "#F34B7D", "#9B1D45"),
        "radial": ("#FFE4EF", "#F34B7D", "#801438"),
        "badge_color": "#F34B7D",
        "badge_rgb": (243, 75, 125),
    },
    "C": {
        "linear": ("#B0BEC5", "#78909C", "#37474F"),
        "radial": ("#ECEFF1", "#78909C", "#263238"),
        "badge_color": "#90A4AE",
        "badge_rgb": (144, 164, 174),
    },
    "Go": {
        "linear": ("#60EFFF", "#00ADD8", "#006E8A"),
        "radial": ("#E0FBFF", "#00ADD8", "#004F63"),
        "badge_color": "#00ADD8",
        "badge_rgb": (0, 173, 216),
    },
    "Rust": {
        "linear": ("#FFB899", "#DEA584", "#8C4E2D"),
        "radial": ("#FFF0EB", "#DEA584", "#6E381C"),
        "badge_color": "#DEA584",
        "badge_rgb": (222, 165, 132),
    },
    "PHP": {
        "linear": ("#99A9D9", "#4F5D95", "#2E3657"),
        "radial": ("#E8ECF8", "#4F5D95", "#222942"),
        "badge_color": "#7A8AC4",
        "badge_rgb": (122, 138, 196),
    },
    "C#": {
        "linear": ("#75E068", "#239120", "#125410"),
        "radial": ("#E5FCE3", "#239120", "#0E3D0C"),
        "badge_color": "#48C73E",
        "badge_rgb": (72, 199, 62),
    },
    "Shell": {
        "linear": ("#B4F788", "#89E051", "#478221"),
        "radial": ("#EFFFE3", "#89E051", "#336314"),
        "badge_color": "#89E051",
        "badge_rgb": (137, 224, 81),
    },
    "Dockerfile": {
        "linear": ("#7E9DA8", "#384D54", "#1F2E33"),
        "radial": ("#E1EDF0", "#384D54", "#152226"),
        "badge_color": "#668A96",
        "badge_rgb": (102, 138, 150),
    },
    "Kotlin": {
        "linear": ("#CE9FFC", "#7F52FF", "#471DB3"),
        "radial": ("#F3EBFF", "#7F52FF", "#321185"),
        "badge_color": "#A97BFF",
        "badge_rgb": (169, 123, 255),
    },
    "Swift": {
        "linear": ("#FF8E7A", "#F05138", "#992210"),
        "radial": ("#FFEBE8", "#F05138", "#75180A"),
        "badge_color": "#F05138",
        "badge_rgb": (240, 81, 56),
    },
    "Dart": {
        "linear": ("#4FE8DE", "#00B4AB", "#00635E"),
        "radial": ("#E0FAF8", "#00B4AB", "#004743"),
        "badge_color": "#00D2C7",
        "badge_rgb": (0, 210, 199),
    },
}

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return f"#{int(max(0, min(255, rgb[0]))):02X}{int(max(0, min(255, rgb[1]))):02X}{int(max(0, min(255, rgb[2]))):02X}"

def generate_palette_from_hex(hex_color):
    try:
        r, g, b = hex_to_rgb(hex_color)
    except Exception:
        r, g, b = 0, 242, 254

    # Linear: Top highlight (+35%), Base, Dark shade (-45%)
    top_c = rgb_to_hex((r + (255 - r) * 0.35, g + (255 - g) * 0.35, b + (255 - b) * 0.35))
    mid_c = rgb_to_hex((r, g, b))
    bot_c = rgb_to_hex((r * 0.55, g * 0.55, b * 0.55))

    # Radial: Core specular (+70%), Base, Deep core (-55%)
    spec_c = rgb_to_hex((r + (255 - r) * 0.70, g + (255 - g) * 0.70, b + (255 - b) * 0.70))
    deep_c = rgb_to_hex((r * 0.45, g * 0.45, b * 0.45))

    return {
        "linear": (top_c, mid_c, bot_c),
        "radial": (spec_c, mid_c, deep_c),
        "badge_color": mid_c,
        "badge_rgb": (int(r), int(g), int(b)),
    }

def get_palette_for_language(lang_name, fallback_hex=None):
    if lang_name in LANGUAGE_PALETTES:
        return LANGUAGE_PALETTES[lang_name]
    if fallback_hex:
        return generate_palette_from_hex(fallback_hex)
    return generate_palette_from_hex("#00F2FE")

def fetch_languages_graphql(token):
    """
    Fetch repository languages using GitHub GraphQL API.
    If authenticated viewer matches USERNAME, queries both public and private repositories.
    Otherwise queries user repositories.
    """
    query = """
    query($username: String!) {
      viewer {
        login
        repositories(first: 100, ownerAffiliations: [OWNER], isFork: false) {
          nodes {
            name
            isPrivate
            languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
      user(login: $username) {
        repositories(first: 100, ownerAffiliations: [OWNER], isFork: false) {
          nodes {
            name
            isPrivate
            languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "GitHub-Action-Language-Updater",
        "Content-Type": "application/json",
    }
    data = json.dumps({"query": query, "variables": {"username": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(GRAPHQL_URL, data=data, headers=headers)
    
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if "errors" in res:
            print(f"GraphQL notice: {res['errors']}")
        data = res.get("data", {})
        
        viewer = data.get("viewer")
        if viewer and viewer.get("login", "").lower() == USERNAME.lower():
            print(f"Authenticated as viewer '{USERNAME}'. Inspecting all (public + private) repositories...")
            return viewer.get("repositories", {}).get("nodes", [])
            
        user = data.get("user")
        if user:
            print(f"Fetched public repositories for user '{USERNAME}'...")
            return user.get("repositories", {}).get("nodes", [])
            
    return []

def fetch_languages_rest(token=None):
    """Fallback to GitHub REST API if GraphQL or token is unavailable."""
    print("Fetching repositories via GitHub REST API...")
    repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
    headers = {"User-Agent": "GitHub-Action-Language-Updater", "Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(repos_url, headers=headers)
    repos = []
    with urllib.request.urlopen(req) as resp:
        repos = json.loads(resp.read().decode("utf-8"))

    repo_nodes = []
    for r in repos:
        if r.get("fork"):
            continue
        repo_name = r.get("name")
        lang_url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/languages"
        lang_req = urllib.request.Request(lang_url, headers=headers)
        try:
            with urllib.request.urlopen(lang_req) as l_resp:
                langs = json.loads(l_resp.read().decode("utf-8"))
                edges = [{"size": size, "node": {"name": name, "color": None}} for name, size in langs.items()]
                repo_nodes.append({"name": repo_name, "isPrivate": r.get("private", False), "languages": {"edges": edges}})
        except Exception as e:
            print(f"Could not fetch languages for repo {repo_name}: {e}")

    return repo_nodes

def collect_language_stats():
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    repo_nodes = []

    if token:
        try:
            repo_nodes = fetch_languages_graphql(token)
        except Exception as e:
            print(f"GraphQL query failed ({e}), attempting REST fallback...")
            try:
                repo_nodes = fetch_languages_rest(token)
            except Exception as e_rest:
                print(f"REST query with token also failed ({e_rest})")

    if not repo_nodes:
        try:
            repo_nodes = fetch_languages_rest()
        except Exception as e:
            print(f"Unauthenticated REST query failed: {e}")

    lang_sizes = defaultdict(int)
    lang_colors = {}

    for repo in repo_nodes:
        languages = repo.get("languages", {}).get("edges", [])
        for edge in languages:
            size = edge.get("size", 0)
            node = edge.get("node", {})
            name = node.get("name")
            color = node.get("color")
            if name and size > 0:
                lang_sizes[name] += size
                if color and name not in lang_colors:
                    lang_colors[name] = color

    total_bytes = sum(lang_sizes.values())
    if total_bytes == 0:
        print("Warning: No language bytes found! Preserving existing SVG.")
        return None

    # Sort languages descending by size
    sorted_langs = sorted(lang_sizes.items(), key=lambda item: item[1], reverse=True)
    stats = []
    for name, size in sorted_langs:
        pct = (size / total_bytes) * 100
        stats.append({
            "name": name,
            "bytes": size,
            "percent": pct,
            "color": lang_colors.get(name)
        })

    return stats

def render_svg(lang_stats):
    """
    Renders the exact 500x200 3D Cyber HUD Most Used Languages SVG card
    with dynamic gradients, segmented energy bar, and 2-column metrics grid.
    """
    # Pick top 6 languages for display
    top_langs = lang_stats[:6]
    
    # Generate unique gradient definitions for each of the top languages
    defs_gradients = []
    
    for idx, item in enumerate(top_langs):
        palette = get_palette_for_language(item["name"], item.get("color"))
        linear_top, linear_mid, linear_bot = palette["linear"]
        rad_spec, rad_mid, rad_deep = palette["radial"]
        
        # Linear gradient for progress bar cylinder
        defs_gradients.append(f"""    <linearGradient id="langGrad{idx}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{linear_top}"/>
      <stop offset="50%" stop-color="{linear_mid}"/>
      <stop offset="100%" stop-color="{linear_bot}"/>
    </linearGradient>""")

        # Radial gradient for 3D glowing nodes
        defs_gradients.append(f"""    <radialGradient id="langNode{idx}" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="{rad_spec}"/>
      <stop offset="40%" stop-color="{rad_mid}"/>
      <stop offset="100%" stop-color="{rad_deep}"/>
    </radialGradient>""")

    # Progress bar segment calculations (Track width = 440px, x = 30 to 470)
    TOTAL_BAR_WIDTH = 440.0
    START_X = 30.0
    current_x = START_X
    bar_segments_svg = []
    
    # Calculate widths based on percentages of all languages or top languages normalized
    # To represent the full scale accurately, each top language gets (percent / 100) * TOTAL_BAR_WIDTH
    for idx, item in enumerate(top_langs):
        pct = item["percent"]
        seg_w = max(2.0, round((pct / 100.0) * TOTAL_BAR_WIDTH, 1))
        # Don't overflow the 440px track
        if current_x + seg_w > START_X + TOTAL_BAR_WIDTH:
            seg_w = max(1.0, round((START_X + TOTAL_BAR_WIDTH) - current_x, 1))
            
        bar_segments_svg.append(f'      <!-- {item["name"]}: {pct:.2f}% = {seg_w}px -->')
        bar_segments_svg.append(f'      <rect x="{current_x:.1f}" y="52" width="{seg_w:.1f}" height="14" fill="url(#langGrad{idx})"/>')
        
        current_x += seg_w
        if idx < len(top_langs) - 1 and current_x < (START_X + TOTAL_BAR_WIDTH - 2):
            bar_segments_svg.append(f'      <line x1="{current_x:.1f}" y1="52" x2="{current_x:.1f}" y2="66" stroke="#080911" stroke-width="1.5"/>')

    # Grid columns (Col 1: x = 30; Col 2: x = 265)
    # Rows at y = 88, 120, 152
    col_x_map = [30, 30, 30, 265, 265, 265]
    row_y_map = [88, 120, 152, 88, 120, 152]
    
    grid_items_svg = []
    for idx, item in enumerate(top_langs):
        col_x = col_x_map[idx]
        row_y = row_y_map[idx]
        palette = get_palette_for_language(item["name"], item.get("color"))
        badge_c = palette["badge_color"]
        r, g, b = palette["badge_rgb"]
        pulse_class = ' class="node-pulse"' if idx == 0 else ""
        
        badge_w = 68 if col_x == 30 else 66
        badge_text_x = 169 if col_x == 30 else 168

        # Escape HTML chars in name if needed
        safe_name = item["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        grid_items_svg.append(f"""    <!-- {safe_name} ({item["percent"]:.2f}%) -->
    <g transform="translate({col_x}, {row_y})">
      <circle cx="8" cy="8" r="5.5" fill="url(#langNode{idx})" filter="url(#softGlow)"{pulse_class}/>
      <circle cx="6" cy="6" r="1.8" fill="#FFFFFF" opacity="0.85"/>
      <text x="20" y="12" fill="#FFFFFF" font-size="12px" font-weight="700">{safe_name}</text>
      <rect x="135" y="0" width="{badge_w}" height="18" rx="9" fill="rgba({r}, {g}, {b}, 0.1)" stroke="rgba({r}, {g}, {b}, 0.35)" stroke-width="0.8"/>
      <text x="{badge_text_x}" y="13" text-anchor="middle" fill="{badge_c}" font-size="10px" font-weight="700" class="mono-text">{item["percent"]:.2f}%</text>
    </g>""")

    defs_gradients_str = "\n\n".join(defs_gradients)
    bar_segments_str = "\n".join(bar_segments_svg)
    grid_items_str = "\n\n".join(grid_items_svg)

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

      /* Glowing / Shimmer Animations */
      @keyframes borderGaze {{
        0%, 100% {{ stroke: #00F2FE; }}
        33% {{ stroke: #70A5FD; }}
        66% {{ stroke: #BB9AF7; }}
      }}
      @keyframes shimmerBar {{
        0% {{ transform: translateX(-100px); opacity: 0; }}
        30% {{ opacity: 0.8; }}
        70% {{ opacity: 0.8; }}
        100% {{ transform: translateX(500px); opacity: 0; }}
      }}
      @keyframes pulseGlow {{
        0%, 100% {{ opacity: 0.85; }}
        50% {{ opacity: 1; }}
      }}
      @keyframes nodeBreathe {{
        0%, 100% {{ transform: scale(1); opacity: 0.9; }}
        50% {{ transform: scale(1.2); opacity: 1; }}
      }}

      .laser-border {{
        animation: borderGaze 9s ease-in-out infinite;
      }}
      .shimmer-effect {{
        animation: shimmerBar 4s ease-in-out infinite;
      }}
      .title-glow {{
        animation: pulseGlow 4s ease-in-out infinite;
      }}
      .node-pulse {{
        animation: nodeBreathe 3s ease-in-out infinite;
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

{defs_gradients_str}

    <!-- Shimmer Beam Gradient -->
    <linearGradient id="shimmerBeam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>

    <!-- Ambient Core Glow -->
    <radialGradient id="barGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00F2FE" stop-opacity="0.22"/>
      <stop offset="60%" stop-color="#70A5FD" stop-opacity="0.08"/>
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

    <!-- Clip for Progress Bar rounding -->
    <clipPath id="barClip">
      <rect x="30" y="52" width="440" height="14" rx="7"/>
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
      <line x1="125" y1="0" x2="125" y2="200"/>
      <line x1="250" y1="0" x2="250" y2="200"/>
      <line x1="375" y1="0" x2="375" y2="200"/>
      <line x1="450" y1="0" x2="450" y2="200"/>
    </g>

    <!-- Ambient Core Glow under progress bar -->
    <ellipse cx="250" cy="59" rx="210" ry="28" fill="url(#barGlow)"/>

    <!-- Glassmorphism Surface -->
    <rect x="4" y="4" width="492" height="192" rx="12" fill="url(#cardSurface)" stroke="none"/>

    <!-- ======================================================== -->
    <!-- HEADER: TITLE & TECH BADGE                               -->
    <!-- ======================================================== -->
    <g transform="translate(30, 16)">
      <!-- Mini Glowing Cyber Indicator -->
      <circle cx="4" cy="11" r="4" fill="#00F2FE" filter="url(#neonGlow)"/>
      <circle cx="4" cy="11" r="1.8" fill="#FFFFFF"/>

      <!-- Title Text -->
      <text x="16" y="16" fill="url(#titleGrad)" font-size="15px" font-weight="800" letter-spacing="0.6" filter="url(#softGlow)">
        Most Used Languages
      </text>

      <!-- Right HUD Tag -->
      <g transform="translate(440, 3)">
        <rect x="-96" y="0" width="96" height="18" rx="9" fill="rgba(0, 242, 254, 0.08)" stroke="rgba(0, 242, 254, 0.35)" stroke-width="0.9"/>
        <circle cx="-86" cy="9" r="2.2" fill="#00FF88" filter="url(#neonGlow)"/>
        <text x="-44" y="13" text-anchor="middle" fill="#73DAC6" font-size="8.5px" font-weight="700" letter-spacing="0.8" class="mono-text">
          METRICS HUD
        </text>
      </g>
    </g>

    <!-- ======================================================== -->
    <!-- 3D PROGRESS BAR (CYBER ISOMETRIC ENERGY BAR)             -->
    <!-- ======================================================== -->
    <!-- Bar Outer Glow Frame -->
    <rect x="28" y="50" width="444" height="18" rx="9" fill="none" stroke="rgba(122, 162, 247, 0.22)" stroke-width="1"/>

    <!-- Segmented 3D Cylinders in ClipPath -->
    <g clip-path="url(#barClip)">
      <!-- Track Background -->
      <rect x="30" y="52" width="440" height="14" fill="#151828"/>

{bar_segments_str}

      <!-- 3D Cylindrical Top Specular Highlight -->
      <rect x="30" y="53" width="440" height="3.5" fill="#FFFFFF" opacity="0.32" rx="1.5"/>

      <!-- Animated Scanning Shimmer Beam -->
      <rect x="0" y="52" width="80" height="14" fill="url(#shimmerBeam)" class="shimmer-effect"/>
    </g>

    <!-- ======================================================== -->
    <!-- LANGUAGE STATS GRID (2 COLUMNS x 3 ROWS)                 -->
    <!-- ======================================================== -->
{grid_items_str}

    <!-- Cyber Outer Laser Glowing Border -->
    <rect x="2" y="2" width="496" height="196" rx="14" fill="none" stroke="url(#laserGrad)" stroke-width="1.8" class="laser-border" filter="url(#neonGlow)"/>
  </g>
</svg>
"""
    return svg_content

def main():
    print("🚀 Starting Most Used Languages update...")
    stats = collect_language_stats()
    if not stats:
        print("❌ Could not obtain language statistics. Aborting update.")
        return

    print("📊 Current Language Breakdown:")
    for s in stats[:10]:
        print(f"  • {s['name']}: {s['bytes']:,} bytes ({s['percent']:.2f}%)")

    svg_content = render_svg(stats)
    os.makedirs(os.path.dirname(OUTPUT_SVG), exist_ok=True)
    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"✨ Successfully generated and saved {OUTPUT_SVG}!")

if __name__ == "__main__":
    main()
