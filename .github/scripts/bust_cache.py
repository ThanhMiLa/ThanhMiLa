#!/usr/bin/env python3
import re
import time

README_PATH = "README.md"

def bust_readme_cache():
    timestamp = int(time.time())
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    dynamic_cards = [
        "profile-3d-contrib/profile-night-view.svg",
        "assets/tech-sphere-3d.svg",
        "assets/streak-stats.svg",
        "assets/leetcode-stats.svg",
        "assets/recent-activity.svg",
        "assets/most-used-langs.svg"
    ]

    for card in dynamic_cards:
        pattern = rf'src="\./{re.escape(card)}(\?[^"]*)?"'
        replacement = f'src="./{card}?raw=true&amp;t={timestamp}"'
        content = re.sub(pattern, replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Busted Camo cache in {README_PATH} with timestamp {timestamp}!")

def apply_3d_contrib_border():
    svg_path = "profile-3d-contrib/profile-night-view.svg"
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "laserGrad" in content:
            return

        defs_block = """  <defs>
    <!-- Neon Laser Gradient Border -->
    <linearGradient id="laserGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00F2FE" stop-opacity="0.85"/>
      <stop offset="30%" stop-color="#70A5FD" stop-opacity="0.55"/>
      <stop offset="70%" stop-color="#BB9AF7" stop-opacity="0.75"/>
      <stop offset="100%" stop-color="#00FF88" stop-opacity="0.85"/>
    </linearGradient>

    <!-- Filters -->
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <clipPath id="cardClip">
      <rect x="4" y="4" width="1272" height="842" rx="20"/>
    </clipPath>
  </defs>
  <rect x="4" y="4" width="1272" height="842" rx="20" fill="#00000f"/>
  <g clip-path="url(#cardClip)">"""

        border_block = """  </g>
  <!-- Cyber Outer Laser Glowing Border -->
  <rect x="4" y="4" width="1272" height="842" rx="20" fill="none" stroke="url(#laserGrad)" stroke-width="3" filter="url(#neonGlow)"/>
</svg>"""

        old_bg_pattern = r"<rect\s+x=[\"']0[\"']\s+y=[\"']0[\"']\s+width=[\"']1280[\"']\s+height=[\"']850[\"']\s+fill=[\"']#[0-9a-fA-F]+[\"']\s*(?:/>|></rect>)"
        match = re.search(old_bg_pattern, content)
        if match:
            start, end = match.span()
            new_content = content[:start] + defs_block + content[end:-len("</svg>")] + border_block
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Applied glowing cyber border to {svg_path}!")
    except Exception as e:
        print(f"Warning: Could not apply border to 3D contrib SVG: {e}")

if __name__ == "__main__":
    apply_3d_contrib_border()
    bust_readme_cache()
