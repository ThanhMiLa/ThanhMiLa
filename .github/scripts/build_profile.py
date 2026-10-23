#!/usr/bin/env python3
"""Render SVG profile assets. Use --refresh to fetch public GitHub/LeetCode data.

No dependencies. Project selection and tech badges are configured below.
Without --refresh, rendering uses the last timestamped snapshot in assets/.
"""
import argparse
import base64
import json
import math
import os
import re
import sys
import textwrap
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
CACHE = ASSETS / "profile-data.json"
USER, LEETCODE = "ThanhMiLa", "Thanh_MiLa"
BG, SURFACE, BORDER = "#0d1117", "#161b22", "#30363d"
FG, MUTED, GREEN = "#f0f6fc", "#919ba8", "#3fb950"
PROJECTS = [
    {"repo": "codelearning", "title": "CodeLearning", "color": "#79c0ff", "logo": "LOGO_SINGLE.png",
     "category": "DSA - COMPETITIVE PROGRAMING",
     "tags": ["Spring Boot", "React", "Judge0"]},
    {"repo": "reallive", "title": "RealLive", "color": "#ff7b72", "icon": "live",
     "category": "STREAMING - MICROSERVICES",
     "tags": ["Spring Boot", "MediaMTX", "Kafka"]},
    {"repo": "springlens", "title": "SpringLens", "color": "#7ee787", "logo": "Logo_SpringLens.svg",
     "category": "DEVELOPER TOOLS",
     "tags": ["Java", "IntelliJ SDK", "REST API"]},
]
TECH = [
    ("Java", "java", "#d66a36"), ("Spring Boot", "spring", "#6db33f"),
    ("React", "react", "#149eca"), ("TypeScript", "typescript", "#3178c6"),
    ("Kotlin", "kotlin", "#9b62ee"), ("C#", "csharp", "#8848c8"),
    (".NET", "dotnet", "#7655d7"), ("Kafka", "kafka", "#8b949e"),
    ("RabbitMQ", "rabbitmq", "#ed780e"), ("PostgreSQL", "postgresql", "#416d9b"),
    ("MySQL", "mysql", "#36749b"), ("Redis", "redis", "#c94040"),
    ("Docker", "docker", "#248aca"), ("Git", "git", "#e75c3c"),
]


def fetch(url, payload=None):
    accept = "text/html" if url.startswith("https://github.com/") else "application/json"
    headers = {"User-Agent": "ThanhMiLa-Profile", "Accept": accept}
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    data = None if payload is None else json.dumps(payload).encode()
    if data:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


class ContributionParser(HTMLParser):
    """Join GitHub's public calendar cells with their count tooltips."""
    def __init__(self):
        super().__init__()
        self.cells, self.counts, self.active, self.buffer = {}, {}, None, ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-date") and "data-level" in attrs:
            self.cells[attrs["id"]] = {"date": attrs["data-date"], "level": int(attrs["data-level"])}
        if tag == "tool-tip" and attrs.get("for"):
            self.active, self.buffer = attrs["for"], ""

    def handle_data(self, data):
        if self.active:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.active:
            match = re.search(r"([\d,]+) contribution", self.buffer)
            self.counts[self.active] = int(match[1].replace(",", "")) if match else 0
            self.active = None

    def days(self):
        if not self.cells or any(key not in self.counts for key in self.cells):
            raise ValueError("GitHub calendar is missing cells or count tooltips")
        return sorted([dict(cell, count=self.counts[key]) for key, cell in self.cells.items()], key=lambda day: day["date"])


def refresh(snapshot):
    errors = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    def save_section(name, loader):
        try:
            snapshot[name] = dict(loader(), updated_at=now)
        except Exception as error:
            print(f"::warning::{name}: {error}; keeping the last successful snapshot", file=sys.stderr)
            errors.append(name)

    def repositories():
        repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100"))
        lookup = {repo["name"].lower(): repo for repo in repos}
        return {p["repo"]: {k: lookup[p["repo"]][k] for k in ("description", "stargazers_count", "forks_count", "html_url")} for p in PROJECTS}

    def github():
        parser = ContributionParser()
        parser.feed(fetch(f"https://github.com/users/{USER}/contributions"))
        return {"days": parser.days()}

    def leetcode():
        query = """query($username:String!){allQuestionsCount{difficulty count} matchedUser(username:$username){profile{ranking} submitStatsGlobal{acSubmissionNum{difficulty count}}}}"""
        response = json.loads(fetch("https://leetcode.com/graphql", {"query": query, "variables": {"username": LEETCODE}}))
        data = response["data"]
        user = data["matchedUser"]
        if not user:
            raise ValueError("LeetCode user was not found")
        return {"ranking": user["profile"]["ranking"],
                "solved": {item["difficulty"]: item["count"] for item in user["submitStatsGlobal"]["acSubmissionNum"]},
                "questions": {item["difficulty"]: item["count"] for item in data["allQuestionsCount"]}}

    for name, loader in (("projects", repositories), ("github", github), ("leetcode", leetcode)):
        save_section(name, loader)
    if any(name not in snapshot for name in ("projects", "github", "leetcode")):
        raise RuntimeError("Missing initial data; rerun --refresh when the services are available")
    CACHE.write_text(json.dumps(snapshot, indent=2) + "\n")
    return errors


def text(x, y, value, size=16, color=FG, weight=400, extra=""):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill=SURFACE, radius=10, stroke="none"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def svg(width, height, content, title, description=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description or title)}</desc>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}} .mono{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}</style>
{content}</svg>\n'''


def write(name, width, height, content, title, description=""):
    (ASSETS / name).write_text(svg(width, height, content, title, description))


def icon(name, color, x, y):
    paths = {
        "live": '<rect x="7" y="9" width="18" height="14" rx="4"/><path d="m14 12 7 4-7 4zM3 7a15 15 0 0 0 0 18M29 7a15 15 0 0 1 0 18"/>',
    }
    return f'<g transform="translate({x} {y})" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</g>'


def hero():
    content = rect(0, 0, 1200, 162, BG, 0)
    content += text(0, 30, "ThanhMiLa", 28.6, GREEN, 600, 'letter-spacing="3" class="mono"')
    content += text(0, 92, "Vo Ngoc Thanh", 48.6, FG, 750, 'letter-spacing="-1.5"')
    content += text(2, 133, "Software Engineer · Student at FPT University", 25, "#c9d1d9", 500)
    content += '<line x1="0" y1="161" x2="1200" y2="161" stroke="#30363d"/>'
    write("profile-header.svg", 1200, 162, content, "Vo Ngoc Thanh (ThanhMiLa) — Software Engineer · Student at FPT University")


def technology():
    # Brisk vertical turns keep larger badges clear while the rows stay close.
    left, top, width, height = 72, 36, 1056, 84
    corners = (0, 0.497, 0.5, 0.997, 1)
    points = ((left, top), (left + width, top), (left + width, top + height),
              (left, top + height), (left, top))
    def point(phase):
        phase %= 1
        for i in range(4):
            if corners[i] <= phase < corners[i + 1]:
                fraction = (phase - corners[i]) / (corners[i + 1] - corners[i])
                x, y = points[i]
                next_x, next_y = points[i + 1]
                return x + (next_x - x) * fraction, y + (next_y - y) * fraction

    styles, badges = [], []
    for index, (label, filename, color) in enumerate(TECH):
        offset = index / len(TECH)
        stops = [0, 1] + [(corner - offset) % 1 for corner in corners[:-1]]
        frames = []
        for stop in sorted(set(stops)):
            x, y = point(offset + stop)
            frames.append(f'{stop*100:.6f}%{{transform:translate({x:.3f}px,{y:.3f}px)}}')
        styles.append(f'@keyframes orbit{index}{{{"".join(frames)}}} .badge{index}{{animation:orbit{index} 56s linear infinite}}')
        x, y = point(offset)
        logo = ET.fromstring((ASSETS / "icons" / f"{filename}.svg").read_text())
        # Native SVG geometry works in image mode without external image requests.
        logo.set("x", "-61.5414725"); logo.set("y", "-22.1267475"); logo.set("width", "44.253495"); logo.set("height", "44.253495")
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        logo_code = ET.tostring(logo, encoding="unicode")
        for identifier in re.findall(r'\bid="([^"]+)"', logo_code):
            logo_code = logo_code.replace(f'"{identifier}"', f'"tech{index}-{identifier}"').replace(f'#{identifier})', f'#tech{index}-{identifier})')
        if filename == "kafka":
            logo_code = logo_code.replace('fill="#000"', 'fill="#e6edf3"').replace('fill="#000000"', 'fill="#e6edf3"')
        if filename == "mysql":
            logo_code = logo_code.replace('fill="#00618A"', 'fill="#f0f6fc"')
        badges.append(f'<g class="badge badge{index}" transform="translate({x} {y})">' + rect(-72, -29, 144, 58, color, 7)
                      + '<rect x="-71" y="-28" width="142" height="56" rx="6" fill="#0d1117" fill-opacity=".17"/>'
                      + logo_code + text(-8, 4.5, label, 12, "#ffffff", 600) + '</g>')
    content = '<style>' + ''.join(styles) + '@media(prefers-reduced-motion:reduce){.badge{animation:none!important}}</style>'
    content += rect(0, 0, 1200, 156, BG, 0)
    content += rect(left, top, width, height, "none", 0, "#252d38")
    content += ''.join(badges)
    write("tech-stack.svg", 1200, 156, content, "Tech stack — clockwise rectangular animation", ", ".join(t[0] for t in TECH))


def projects(snapshot):
    write("project-repositories-link.svg", 200, 24,
          text(200, 18, "View all repositories →", 16, "#79c0ff", 400, 'text-anchor="end"'),
          "View all repositories →")
    descriptions = {p["repo"]: snapshot["projects"][p["repo"]]["description"] or "" for p in PROJECTS}
    lines = {repo: textwrap.wrap(description, width=41, break_long_words=False, break_on_hyphens=False)
             for repo, description in descriptions.items()}
    tags_y = max(180, 110 + (max(len(value) for value in lines.values()) - 1) * 22 + 26)
    card_height = tags_y + 76
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    for project in PROJECTS:
        data = snapshot["projects"][project["repo"]]
        color = project["color"]
        content = rect(.5, .5, 387, card_height - 1, SURFACE, 12, BORDER)
        content += rect(1, 20, 3, 32, color, 1)
        if project.get("logo"):
            logo_path = ASSETS / "icons" / project["logo"]
            if logo_path.suffix.lower() == ".svg":
                logo = ET.fromstring(logo_path.read_text())
                for name, value in {"x": "22", "y": "21", "width": "36", "height": "36",
                                    "preserveAspectRatio": "xMidYMid meet"}.items():
                    logo.set(name, value)
                content += "\n".join(line.rstrip() for line in ET.tostring(logo, encoding="unicode").splitlines())
            else:
                logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
                content += f'<image x="22" y="21" width="36" height="36" preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{logo}"/>'
        else:
            content += icon(project["icon"], color, 22, 23)
        content += text(68, 47, project["title"], 23, FG, 650)
        content += '<path d="M355 29h12v12m-1-11-15 15m11 1v6h-17V35h6" fill="none" stroke="#919ba8" stroke-width="1.7"/>'
        content += text(23, 81, project["category"], 10, color, 600, 'letter-spacing="1.2" class="mono"')
        for i, line in enumerate(lines[project["repo"]]):
            content += text(23, 110 + i * 22, line, 16, "#b7c0cc")
        x = 23
        for tag in project["tags"]:
            w = len(tag) * 7 + 20
            content += rect(x, tags_y, w, 27, "#212b36", 6)
            content += text(x + 10, tags_y + 18, tag, 12, color, 600)
            x += w + 7
        content += text(23, tags_y + 57, f'☆  {data["stargazers_count"]}    ⑂  {data["forks_count"]}', 15, MUTED)
        content += text(365, tags_y + 57, "Explore repository →", 12, color, 500, 'text-anchor="end"')
        title = f'{project["title"]} — {descriptions[project["repo"]]}'
        write(f'project-{project["repo"]}.svg', 388, card_height, content, title)
        pattern = rf'(<img\b[^>]*\bsrc="\./assets/project-{re.escape(project["repo"])}\.svg(?:\?[^"]*)?"[^>]*\balt=")[^"]*(")'
        readme = re.sub(pattern, lambda match: match[1] + escape(title) + match[2], readme)
    readme_path.write_text(readme)


def github(snapshot):
    section = snapshot["github"]
    as_of = date.fromisoformat(section["updated_at"][:10])
    days = [d for d in section["days"] if d["date"] <= as_of.isoformat()]
    counts = {d["date"]: d["count"] for d in days}
    current, longest, run = 0, 0, 0
    start, end = date.fromisoformat(days[0]["date"]), date.fromisoformat(days[-1]["date"])
    day = start
    while day <= end:
        run = run + 1 if counts.get(day.isoformat(), 0) else 0
        longest = max(longest, run)
        day += timedelta(days=1)
    day = as_of
    if not counts.get(day.isoformat(), 0):
        day -= timedelta(days=1)
    while day >= start and counts.get(day.isoformat(), 0):
        current += 1
        day -= timedelta(days=1)
    total = sum(d["count"] for d in days)
    content = rect(.5, .5, 1199, 265, SURFACE, 12, BORDER)
    content += text(26, 35, "A little progress, every day.", 20, FG, 600)
    content += text(1174, 34, f'Updated {section["updated_at"][:10]} UTC', 12, MUTED, 400, 'text-anchor="end"')
    for x, value, label, color in ((27, f"{total:,}", "Contributions", FG), (181, current, "Current streak", "#ffa657"), (335, longest, "Longest streak", GREEN)):
        content += text(x, 105, value, 36, color, 700)
        content += text(x, 134, label, 14, MUTED)
        content += text(x, 156, "in displayed year" if x != 181 else "days", 11, MUTED)
    content += text(27, 214, f'{start:%b %d, %Y} – {end:%b %d, %Y}', 12, MUTED)
    content += text(27, 239, "Public profile contribution calendar", 11, MUTED)
    content += '<path d="M495 66v176" stroke="#30363d"/>'
    cell, gap, origin_x, origin_y = 9, 3, 535, 99
    colors = ["#212b26", "#0e4429", "#006d32", "#26a641", "#39d353"]
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    month = None
    for entry in days:
        d = date.fromisoformat(entry["date"])
        column, row = (d - sunday).days // 7, (d.weekday() + 1) % 7
        if d.month != month and (row == 0 or month is None):
            content += text(origin_x + column * (cell + gap), 83, d.strftime("%b"), 10, MUTED)
            month = d.month
        content += f'<rect x="{origin_x + column * (cell + gap)}" y="{origin_y + row * (cell + gap)}" width="{cell}" height="{cell}" rx="2" fill="{colors[entry["level"]]}"><title>{entry["date"]}: {entry["count"]} contributions</title></rect>'
    for row, label in ((1, "M"), (3, "W"), (5, "F")):
        content += text(516, origin_y + row * 12 + 8, label, 9, MUTED)
    content += text(1020, 214, "Less", 10, MUTED)
    for i, color in enumerate(colors):
        content += rect(1053 + i * 13, 205, 9, 9, color, 2)
    content += text(1123, 214, "More", 10, MUTED)
    write("github-summary.svg", 1200, 266, content, "GitHub contributions summary", f"{total} contributions; current streak {current} days; longest streak {longest} days in the displayed year. Updated {section['updated_at'][:10]}.")


def leetcode(snapshot):
    stats = snapshot["leetcode"]
    solved, questions = stats["solved"], stats["questions"]
    content = rect(.5, .5, 1199, 227, SURFACE, 12, BORDER)
    content += text(27, 35, "Problem solving, one challenge at a time.", 20, FG, 600)
    content += text(1174, 34, f'Updated {stats["updated_at"][:10]} UTC', 12, MUTED, 400, 'text-anchor="end"')
    content += '<circle cx="92" cy="137" r="53" fill="none" stroke="#30363d" stroke-width="8"/>'
    colors = ["#3fb9a5", "#e3b341", "#f47067"]
    circumference, offset = 2 * math.pi * 53, 0
    for difficulty, color in zip(("Easy", "Medium", "Hard"), colors):
        length = circumference * solved[difficulty] / max(1, solved["All"])
        content += f'<circle cx="92" cy="137" r="53" fill="none" stroke="{color}" stroke-width="8" stroke-dasharray="{length} {circumference-length}" stroke-dashoffset="{-offset}" transform="rotate(-90 92 137)"/>'
        offset += length
    content += text(92, 143, solved["All"], 34, FG, 700, 'text-anchor="middle"')
    content += text(92, 164, "SOLVED", 10, MUTED, 600, 'text-anchor="middle" letter-spacing="1"')
    content += text(175, 113, LEETCODE, 24, FG, 650)
    content += text(175, 143, f'Global rank  #{stats["ranking"]:,}', 17, "#ffa657", 500)
    content += text(175, 174, "Practice. Understand. Improve.", 14, MUTED)
    content += '<path d="M495 69v129" stroke="#30363d"/>'
    for i, (difficulty, color) in enumerate(zip(("Easy", "Medium", "Hard"), colors)):
        x, y = 527 + i * 220, 103
        content += text(x, y, difficulty, 15, color, 600)
        content += text(x, y + 39, solved[difficulty], 29, FG, 650)
        content += text(x + 55, y + 39, f'/ {questions[difficulty]:,}', 14, MUTED)
        content += rect(x, y + 57, 187, 6, "#30363d", 3)
        bar = 187 * solved[difficulty] / max(1, questions[difficulty])
        if bar:
            content += rect(x, y + 57, round(bar, 3), 6, color, 3)
        content += text(x, y + 85, f'{100*solved[difficulty]/max(1,questions[difficulty]):.1f}% completed', 12, MUTED)
    write("leetcode-summary.svg", 1200, 228, content, "LeetCode statistics", f'{LEETCODE}: {solved["All"]} problems solved. Easy {solved["Easy"]}, Medium {solved["Medium"]}, Hard {solved["Hard"]}. Updated {stats["updated_at"][:10]}.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    snapshot = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    errors = refresh(snapshot) if args.refresh else []
    if not snapshot:
        parser.error("No saved data; run with --refresh first")
    hero(); technology(); projects(snapshot); github(snapshot); leetcode(snapshot)
    print("Built profile assets from saved, timestamped data.")
    if errors:
        print("Retained previous data for: " + ", ".join(errors))
        sys.exit(1)


if __name__ == "__main__":
    main()
