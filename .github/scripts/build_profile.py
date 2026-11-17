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
ADDITIONAL_LANGUAGE_REPOSITORIES = (
    "ThanhMiLa/bookteria-microservice",
    "ThanhMiLa/Identity_Service_FullStack",
    "ThanhMiLa/HSF302_VoNgocThanh_SE20A11",
    "ThanhMiLa/spring-ai-demo",
    "ThanhMiLa/source-hsf-pe",
    "fptu-se-su26/swp391-su26-ai-audit-project-swp391_se20a11_group-02",
    "fudn-traltb-su26/course-project-hsf302_se20a11_quang_tan_thanh",
)
BG = "#0d1117"
FG, MUTED, GREEN = "#f0f6fc", "#919ba8", "#3fb950"
FPT_BLUE, FPT_GREEN, FPT_ORANGE = "#0066b3", "#0db14b", "#f37021"
FPT_COLORS = (FPT_BLUE, FPT_GREEN, FPT_ORANGE)
PROJECTS = [
    {"repo": "codelearning", "title": "CodeLearning", "color": FPT_BLUE, "logo": "LOGO_SINGLE.png", "logo_size": 38,
     "category": "E - LEARNING",
     "tags": ["Spring Boot", "React", "Judge0"]},
    {"repo": "reallive", "title": "RealLive", "color": FPT_ORANGE, "logo": "RealLive-favicon.svg", "logo_size": 40,
     "category": "STREAMING PLATFORM",
     "tags": ["Spring Boot", "MediaMTX", "Kafka"]},
    {"repo": "springlens", "title": "SpringLens", "color": FPT_GREEN, "logo": "Logo_SpringLens.svg", "logo_size": 34,
     "category": "DEVELOPER TOOLS",
     "tags": ["Java", "IntelliJ SDK", "REST API"]},
]
TECH = [
    ("Java", "java", "#d66a36"), ("Spring Boot", "spring", "#6db33f"),
    ("TypeScript", "typescript", "#3178c6"), ("React", "react", "#149eca"),
    ("Kotlin", "kotlin", "#9b62ee"), ("Jetpack Compose", "jetpackcompose", "#1d5f7a"),
    ("PostgreSQL", "postgresql", "#416d9b"), ("MySQL", "mysql", "#36749b"),
    ("MongoDB", "mongodb", "#00684a"), ("Redis", "redis", "#c94040"),
    ("RabbitMQ", "rabbitmq", "#ed780e"), ("Kafka", "kafka", "#8b949e"),
    ("Git", "git", "#e75c3c"), ("GitHub", "github", "#484f58"),
    ("Docker", "docker", "#248aca"), ("VPS", "vps", "#5856d6"),
    ("Vercel", "vercel", "#2b3137"), ("Cloudflare", "cloudflare", "#334155"),
]
CONTACTS = [
    {"slug": "email", "title": "Email", "category": "EMAIL ADDRESS",
     "value": "vntvlogs@gmail.com", "color": "#ff7b72", "icon": "email",
     "href": "mailto:vntvlogs@gmail.com"},
    {"slug": "linkedin", "title": "LinkedIn", "category": "PROFESSIONAL NETWORK",
     "value": "Võ Ngọc Thanh", "color": "#58a6ff", "icon": "linkedin",
     "href": "https://www.linkedin.com/in/v%C3%B5-ng%E1%BB%8Dc-thanh-761067324/"},
    {"slug": "facebook", "title": "Facebook", "category": "SOCIAL PROFILE",
     "value": "fb.com/thanhh.mila", "color": "#79c0ff", "icon": "facebook",
     "href": "https://www.facebook.com/thanhh.mila"},
    {"slug": "phone", "title": "Phone", "category": "MOBILE / ZALO",
     "value": "0763769325", "color": "#3fb950", "icon": "phone",
     "href": "tel:0763769325"},
]


def fetch(url, payload=None):
    accept = "text/html" if url.startswith("https://github.com/") else "application/json"
    headers = {"User-Agent": "ThanhMiLa-Profile", "Accept": accept}
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    if "api.github.com" in url and token:
        headers["Authorization"] = "Bearer " + token
    data = None if payload is None else json.dumps(payload).encode()
    if data:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


def fetch_public_repositories():
    repositories, page = [], 1
    while True:
        batch = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"))
        repositories.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            return repositories
        page += 1


def fetch_language_stats(repositories):
    totals, sources = {}, {}
    unique = {repo["full_name"].lower(): repo for repo in repositories
              if not repo["private"] and not repo["fork"]
              and repo["full_name"].split("/", 1)[0].lower() == USER.lower()}
    for full_name in ADDITIONAL_LANGUAGE_REPOSITORIES:
        repo = json.loads(fetch(f"https://api.github.com/repos/{full_name}"))
        # Explicit selections override the general exclusion of forks and orgs.
        if repo["full_name"].lower() != full_name.lower():
            raise ValueError(f"Additional language repository must match its configured name: {full_name}")
        unique[repo["full_name"].lower()] = repo
    for repo in sorted(unique.values(), key=lambda item: item["full_name"].lower()):
        counts = json.loads(fetch(repo["languages_url"]))
        sources[repo["full_name"]] = counts
        for language, byte_count in counts.items():
            totals[language] = totals.get(language, 0) + byte_count
    return {"bytes": totals, "repositories": sources, "repository_count": len(unique),
            "private_repository_count": sum(bool(repo["private"]) for repo in unique.values()),
            "included_forks": [repo["full_name"] for repo in unique.values() if repo["fork"]]}


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
    repos_cache = None
    def public_repositories():
        nonlocal repos_cache
        if repos_cache is None:
            repos_cache = fetch_public_repositories()
        return repos_cache

    def save_section(name, loader):
        try:
            snapshot[name] = dict(loader(), updated_at=now)
        except Exception as error:
            print(f"::warning::{name}: {error}; keeping the last successful snapshot", file=sys.stderr)
            errors.append(name)

    def repositories():
        lookup = {repo["name"].lower(): repo for repo in public_repositories()}
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

    for name, loader in (("projects", repositories), ("github", github), ("leetcode", leetcode),
                         ("languages", lambda: fetch_language_stats(public_repositories()))):
        save_section(name, loader)
    if any(name not in snapshot for name in ("projects", "github", "leetcode", "languages")):
        raise RuntimeError("Missing initial data; rerun --refresh when the services are available")
    CACHE.write_text(json.dumps(snapshot, indent=2) + "\n")
    return errors


def text(x, y, value, size=16, color=FG, weight=400, extra=""):
    w_attr = f' font-weight="{weight}"' if weight != 400 else ""
    e_attr = f" {extra}" if extra else ""
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}"{w_attr}{e_attr}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill=BG, radius=10, stroke="none"):
    r_attr = f' rx="{radius}"' if radius else ""
    s_attr = f' stroke="{stroke}"' if stroke != "none" else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{r_attr} fill="{fill}"{s_attr}/>'


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
        "email": '<rect x="4" y="7" width="24" height="18" rx="3"/><path d="m5 9 11 8 11-8"/>',
        "linkedin": '<rect x="5" y="5" width="22" height="22" rx="4"/><path d="M11 14v7M11 10.5v.1M16 21v-4.2a2.8 2.8 0 0 1 5.6 0V21M16 14v7"/>',
        "facebook": '<rect x="5" y="5" width="22" height="22" rx="4"/><path d="M18 27V15h3.5M14.5 18.5H21M18 15v-2.2a2.3 2.3 0 0 1 2.3-2.3H22"/>',
        "phone": '<path d="M24.5 21.3v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 4.6 8.6a2 2 0 0 1 2-2.2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.4 2.1L10.6 14.3a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    }
    return f'<g transform="translate({x} {y})" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</g>'


def hero():
    content = rect(0, 0, 1200, 152, BG, 0)
    content += text(0, 30, "ThanhMiLa", 28.6, GREEN, 600, 'letter-spacing="3" class="mono"')
    content += text(0, 92, "Vo Ngoc Thanh", 48.6, FG, 750, 'letter-spacing="-1.5"')
    content += text(2, 133, "Software Engineer · Student at FPT University", 25, "#c9d1d9", 500)
    write("profile-header.svg", 1200, 152, content, "Vo Ngoc Thanh (ThanhMiLa) — Software Engineer · Student at FPT University")


def technology():
    # Brisk vertical turns keep larger badges clear while the rows stay close.
    left, top, width, height = 57, 36, 1086, 84
    duration = 56
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

    keyframes = "".join(f'{c*100:g}%{{transform:translate({x}px,{y}px)}}' for c, (x, y) in zip(corners, points))
    styles = [
        f'@keyframes orbit{{{keyframes}}} .badge{{animation:orbit {duration}s linear infinite;will-change:transform}} '
        f'.badge text{{fill:#ffffff;font-size:11px;font-weight:600}}'
    ]
    badges = []
    for index, (label, filename, color) in enumerate(TECH):
        offset = index / len(TECH)
        styles.append(f'.badge{index}{{animation-delay:-{offset * duration:.3f}s}}')
        x, y = point(offset)
        logo = ET.fromstring((ASSETS / "icons" / f"{filename}.svg").read_text())
        # Native SVG geometry works in image mode without external image requests.
        logo.set("x", "-49"); logo.set("y", "-17"); logo.set("width", "34"); logo.set("height", "34")
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        logo_code = ET.tostring(logo, encoding="unicode")
        for identifier in re.findall(r'\bid="([^"]+)"', logo_code):
            logo_code = logo_code.replace(f'"{identifier}"', f'"tech{index}-{identifier}"').replace(f'#{identifier})', f'#tech{index}-{identifier})')
        if filename == "kafka":
            logo_code = (logo_code.replace('fill="#000"', 'fill="#e6edf3"')
                         .replace('fill="#000000"', 'fill="#e6edf3"')
                         .replace('fill="#231f20"', 'fill="#e6edf3"'))
        if filename == "github":
            logo_code = logo_code.replace('fill="#181616"', 'fill="#f0f6fc"')
        if filename == "mysql":
            logo_code = logo_code.replace('fill="#00618A"', 'fill="#f0f6fc"')
        # Strip redundant nested namespace and whitespace
        logo_code = re.sub(r'\s*xmlns="http://www\.w3\.org/2000/svg"', '', logo_code)
        logo_code = re.sub(r'>\s+<', '><', logo_code).strip()
        if " " in label:
            first, second = label.split(" ", 1)
            label_svg = f'<text x="-8" y="-2.5">{first}</text><text x="-8" y="11">{second}</text>'
        else:
            label_svg = f'<text x="-8" y="4">{label}</text>'
        badges.append(f'<g class="badge badge{index}" transform="translate({x:.2f} {y:.2f})">'
                      f'<use href="#tb" fill="{color}"/><use href="#to"/>'
                      + logo_code + label_svg + '</g>')
    content = '<defs><rect id="tb" x="-57" y="-27" width="114" height="54" rx="7"/>'
    content += '<rect id="to" x="-56" y="-26" width="112" height="52" rx="6" fill="#0d1117" fill-opacity=".17"/></defs>'
    content += '<style>' + ''.join(styles) + '@media(prefers-reduced-motion:reduce){.badge{animation:none!important}}</style>'
    content += rect(0, 0, 1200, 156, BG, 0)
    content += ''.join(badges)
    write("tech-stack.svg", 1200, 156, content, "Tech stack — clockwise rectangular animation", ", ".join(t[0] for t in TECH))


def projects(snapshot):
    """Render the three borderless featured project SVG tiles."""
    descriptions = {p["repo"]: snapshot["projects"][p["repo"]]["description"] or "" for p in PROJECTS}
    lines = {repo: textwrap.wrap(description, width=41, break_long_words=False, break_on_hyphens=False)
             for repo, description in descriptions.items()}
    tags_y = max(180, 110 + (max(len(value) for value in lines.values()) - 1) * 22 + 26)
    card_height = tags_y + 70
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    slots = ((400, 0), (400, 16), (400, 32))
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    for project, (slot_width, offset_x) in zip(PROJECTS, slots):
        data = snapshot["projects"][project["repo"]]
        color = project["color"]
        parts = [rect(0, 0, slot_width, card_height, BG, 0)]
        inner = []
        if project.get("logo"):
            logo_path = ASSETS / "icons" / project["logo"]
            # Keep every logo centered at (20, 39), independent of its optical size.
            logo_size = project.get("logo_size", 36)
            logo_x, logo_y = 20 - logo_size / 2, 39 - logo_size / 2
            if logo_path.suffix.lower() == ".svg":
                logo = ET.fromstring(logo_path.read_text())
                for name, value in {"x": f"{logo_x:g}", "y": f"{logo_y:g}",
                                    "width": str(logo_size), "height": str(logo_size),
                                    "preserveAspectRatio": "xMidYMid meet"}.items():
                    logo.set(name, value)
                logo_code = re.sub(r'\s*xmlns="http://www\.w3\.org/2000/svg"', "", ET.tostring(logo, encoding="unicode"))
                inner.append("\n".join(line.rstrip() for line in logo_code.splitlines()))
            else:
                logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
                inner.append(f'<image x="{logo_x:g}" y="{logo_y:g}" width="{logo_size}" height="{logo_size}" preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{logo}"/>')
        else:
            inner.append(icon(project["icon"], color, 2, 23))
        inner.append(text(48, 47, project["title"], 23, FG, 650))
        inner.append('<path d="M356 29h12v12m-1-11-15 15m11 1v6h-17V35h6" fill="none" stroke="#919ba8" stroke-width="1.7"/>')
        inner.append(text(0, 81, project["category"], 13, color, 600, 'letter-spacing="1.2" class="mono"'))
        for i, line in enumerate(lines[project["repo"]]):
            inner.append(text(0, 110 + i * 22, line, 16, "#b7c0cc"))
        x = 0
        for tag in project["tags"]:
            w = len(tag) * 7 + 20
            inner.append(rect(x, tags_y, w, 27, "#212b36", 6))
            inner.append(text(x + 10, tags_y + 18, tag, 12, color, 600))
            x += w + 7
        inner.append(text(0, tags_y + 55, f'☆  {data["stargazers_count"]}    ⑂  {data["forks_count"]}', 15, MUTED))
        inner.append(text(368, tags_y + 55, "Explore repository →", 12, color, 500, 'text-anchor="end"'))
        body = "".join(inner)
        if offset_x:
            body = f'<g transform="translate({offset_x} 0)">{body}</g>'
        parts.append(body)
        title = f'{project["title"]} — {descriptions[project["repo"]]}'
        write(f'project-{project["repo"]}.svg', slot_width, card_height, "".join(parts), title)
        pattern = rf'(<img\b[^>]*\bsrc="(?:\.|https://raw\.githubusercontent\.com/{re.escape(USER)}/{re.escape(USER)}/main)/assets/project-{re.escape(project["repo"])}\.svg(?:\?[^"]*)?"[^>]*\balt=")[^"]*(")'
        readme = re.sub(pattern, lambda match: match[1] + escape(title) + match[2], readme)
    readme_path.write_text(readme)


def github_section(snapshot, origin_y_offset=0):
    """Render the GitHub contributions summary and calendar fragment."""
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
    parts = []
    for x, value, label, color in ((0, f"{total:,}", "Contributions", FPT_BLUE), (160, current, "Current Streak", FPT_GREEN), (320, longest, "Longest Streak", FPT_ORANGE)):
        parts.append(text(x, 56, label, 14, MUTED))
        parts.append(text(x, 102, value, 36, color, 700))
    parts.append(text(0, 138, f'{start:%b %d, %Y} – {end:%b %d, %Y}', 12, MUTED))
    parts.append(text(0, 158, "Public profile contribution calendar", 11, MUTED))
    cell, gap, origin_y = 9, 3, 60
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    max_col = max((date.fromisoformat(entry["date"]) - sunday).days // 7 for entry in days)
    origin_x = 1200 - (max_col * (cell + gap) + cell)
    colors = ["#212b26", "#0e4429", "#006d32", "#26a641", "#39d353"]
    parts.append(f'<defs><rect id="c" width="{cell}" height="{cell}" rx="2"/></defs>')
    month_labels, month = [], None
    groups = [[] for _ in colors]
    for entry in days:
        d = date.fromisoformat(entry["date"])
        column, row = (d - sunday).days // 7, (d.weekday() + 1) % 7
        if d.month != month and (row == 0 or month is None):
            month_labels.append(f'<text x="{origin_x + column * (cell + gap)}" y="48">{d.strftime("%b")}</text>')
            month = d.month
        groups[entry["level"]].append(f'<use href="#c" x="{origin_x + column * (cell + gap)}" y="{origin_y + row * (cell + gap)}"/>')
    parts.append(f'<g fill="{MUTED}" font-size="10">{"".join(month_labels)}</g>')
    for color, rects in zip(colors, groups):
        if rects:
            parts.append(f'<g fill="{color}">{"".join(rects)}</g>')
    parts.append(f'<g fill="{MUTED}" font-size="9"><text x="{origin_x - 19}" y="{origin_y + 1 * 12 + 8}">M</text><text x="{origin_x - 19}" y="{origin_y + 3 * 12 + 8}">W</text><text x="{origin_x - 19}" y="{origin_y + 5 * 12 + 8}">F</text></g>')
    parts.append(text(1070, 166, "Less", 10, MUTED))
    for i, color in enumerate(colors):
        parts.append(rect(1102 + i * 13, 157, 9, 9, color, 2))
    parts.append(text(1200, 166, "More", 10, MUTED, 400, 'text-anchor="end"'))
    fragment = f'<g transform="translate(0 {origin_y_offset})">{"".join(parts)}</g>' if origin_y_offset else "".join(parts)
    desc = f"GitHub: {total} contributions, current streak {current} days, longest streak {longest} days ({section['updated_at'][:10]})."
    return fragment, desc


def leetcode_section(snapshot, origin_y_offset):
    """Render the LeetCode statistics fragment."""
    stats = snapshot["leetcode"]
    solved, questions = stats["solved"], stats["questions"]
    # Adapt the dark part of the Devicon logo for the dark background.
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    logo = ET.fromstring((ASSETS / "icons" / "leetcode.svg").read_text())
    logo.set("x", "0"); logo.set("y", "13")
    logo.set("width", "32"); logo.set("height", "32")
    for path in logo:
        if path.get("fill") == "#070706":
            path.set("fill", "#f0f6fc")
    parts = [re.sub(r'\s*xmlns="http://www\.w3\.org/2000/svg"', "", ET.tostring(logo, encoding="unicode"))]
    parts.append(text(42, 38, "LeetCode", 24, FG, 650))
    colors = ("#00b8a3", "#ffc01e", "#ff375f")
    # Three muted arcs and colored progress, with a gap at the bottom.
    circumference = 2 * math.pi * 78
    segment = circumference * .72 / 3
    for i, (difficulty, color) in enumerate(zip(("Easy", "Medium", "Hard"), colors)):
        offset = -i * segment
        common = f'cx="152" cy="151" r="78" fill="none" stroke-width="7" stroke-linecap="round" transform="rotate(140 152 151)"'
        parts.append(f'<circle {common} stroke="{color}" opacity=".25" stroke-dasharray="{segment - 5:.2f} {circumference:.2f}" stroke-dashoffset="{offset:.2f}"/>')
        progress = (segment - 5) * min(1, solved[difficulty] / max(1, questions[difficulty]))
        if progress:
            parts.append(f'<circle {common} stroke="{color}" stroke-dasharray="{progress:.2f} {circumference:.2f}" stroke-dashoffset="{offset:.2f}"/>')
        y = 57 + i * 61
        parts.append(rect(278, y, 155, 52, "#21262d", 7))
        parts.append(text(355, y + 21, "Med." if difficulty == "Medium" else difficulty, 18, color, 650, 'text-anchor="middle"'))
        parts.append(text(355, y + 43, f'{solved[difficulty]:,}/{questions[difficulty]:,}', 19, FG, 650, 'text-anchor="middle"'))
    parts.append(text(147, 153, f'{solved["All"]:,}', 36, FG, 700, 'text-anchor="end"'))
    parts.append(text(151, 153, f'/ {questions["All"]:,}', 16, MUTED, 500))
    parts.append(text(152, 180, "✓ Solved", 17, GREEN, 600, 'text-anchor="middle"'))
    parts.append(text(152, 234, LEETCODE, 14, MUTED, 500, 'text-anchor="middle"'))
    fragment = f'<g transform="translate(0 {origin_y_offset})">{"".join(parts)}</g>'
    desc = f'LeetCode ({LEETCODE}): {solved["All"]}/{questions["All"]} solved (Easy {solved["Easy"]}, Medium {solved["Medium"]}, Hard {solved["Hard"]}; {stats["updated_at"][:10]}).'
    return fragment, desc


def languages_section(snapshot, origin_y_offset):
    """Render the top 8 languages with individual progress bars."""
    stats = snapshot["languages"]
    counts = stats["bytes"]
    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_eight = ranked[:8]
    colors = {"Java": "#b07219", "Python": "#3572a5", "TypeScript": "#3178c6",
              "JavaScript": "#f1e05a", "HTML": "#e34c26", "CSS": "#a78bfa",
              "C#": "#178600", "C++": "#f34b7d", "Kotlin": "#a97bff",
              "Shell": "#89e051", "Dart": "#00b4ab", "Swift": "#f05138",
              "PLpgSQL": "#336790", "Dockerfile": "#384d54", "Lua": "#000080"}
    origin_x = 555
    parts = []
    for index, (language, byte_count) in enumerate(top_eight):
        x, y = origin_x + (index % 2) * 340, 77 + (index // 2) * 48
        bar_w = 305
        color = colors.get(language, "#79c0ff")
        percent = 100 * byte_count / max(1, total)
        parts.append(f'<circle cx="{x + 4}" cy="{y - 5}" r="4" fill="{color}"/>')
        parts.append(text(x + 15, y, language, 14, FG, 600))
        parts.append(text(x + bar_w, y, f'{percent:.1f}%', 17, color, 650, 'text-anchor="end"'))
        parts.append(rect(x, y + 15, bar_w, 6, "#30363d", 3))
        if percent:
            parts.append(rect(x, y + 15, round(bar_w * percent / 100, 3), 6, color, 3))
    if not top_eight:
        parts.append(text(origin_x, 106, "No language data available.", 15, MUTED))
    summary_text = "; ".join(f'{name} {100 * count / max(1, total):.1f}%' for name, count in top_eight)
    fragment = f'<g transform="translate(0 {origin_y_offset})">{"".join(parts)}</g>'
    desc = f'Top languages ({stats["updated_at"][:10]}): {summary_text or "No language data available."}.'
    return fragment, desc


def stats(snapshot):
    """Render the borderless GitHub, LeetCode, and top languages summary SVG."""
    gh_offset = -14
    lc_offset = 178
    height = 428
    gh_svg, gh_desc = github_section(snapshot, gh_offset)
    lc_svg, lc_desc = leetcode_section(snapshot, lc_offset)
    lang_svg, lang_desc = languages_section(snapshot, lc_offset)
    content = rect(0, 0, 1200, height, BG, 0) + gh_svg + lc_svg + lang_svg
    write(
        "profile-summary.svg",
        1200,
        height,
        content,
        "GitHub, LeetCode, and top 8 languages summary",
        f"{gh_desc} {lc_desc} {lang_desc}",
    )


def contacts():
    """Render the four clickable borderless contact SVG tiles."""
    offsets = (0, 70, 141, 200)
    for x_offset, item in zip(offsets, CONTACTS):
        color = item["color"]
        content = rect(0, 0, 300, 114, BG, 0)
        content += icon(item["icon"], color, x_offset - 4, 20)
        content += text(x_offset + 37, 44, item["title"], 21, FG, 650)
        content += text(x_offset, 74, item["category"], 10, color, 600, 'letter-spacing="1.2" class="mono"')
        content += text(x_offset, 99, item["value"], 15, "#c9d1d9", 500)
        title = f'{item["title"]} — {item["value"]}'
        write(f'contact-{item["slug"]}.svg', 300, 114, content, title)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    snapshot = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    errors = refresh(snapshot) if args.refresh else []
    if not snapshot:
        parser.error("No saved data; run with --refresh first")
    hero(); technology(); projects(snapshot); stats(snapshot); contacts()
    print("Built profile assets from saved, timestamped data.")
    if errors:
        print("Retained previous data for: " + ", ".join(errors))
        sys.exit(1)


if __name__ == "__main__":
    main()
