#!/usr/bin/env python3
import re
import time

README_PATH = "README.md"

def bust_readme_cache():
    timestamp = int(time.time())
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    dynamic_cards = [
        "assets/profile-header.svg",
        "assets/tech-stack.svg",
        "assets/project-codelearning.svg",
        "assets/project-reallive.svg",
        "assets/project-springlens.svg",
        "assets/github-summary.svg",
        "assets/leetcode-summary.svg",
    ]

    for card in dynamic_cards:
        pattern = rf'src="\./{re.escape(card)}(\?[^"]*)?"'
        replacement = f'src="./{card}?raw=true&amp;t={timestamp}"'
        content = re.sub(pattern, replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Busted Camo cache in {README_PATH} with timestamp {timestamp}!")

if __name__ == "__main__":
    bust_readme_cache()
