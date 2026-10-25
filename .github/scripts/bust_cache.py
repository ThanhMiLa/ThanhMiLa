#!/usr/bin/env python3
import hashlib
from pathlib import Path
import re

README_PATH = Path("README.md")
RAW_BASE = "https://raw.githubusercontent.com/ThanhMiLa/ThanhMiLa/main"

CARDS = [
    "assets/profile-header.svg",
    "assets/tech-stack.svg",
    "assets/project-repositories-link.svg",
    "assets/project-codelearning.svg",
    "assets/project-reallive.svg",
    "assets/project-springlens.svg",
    "assets/github-summary.svg",
    "assets/leetcode-summary.svg",
    "assets/languages-summary.svg",
    "assets/contact-email.svg",
    "assets/contact-linkedin.svg",
    "assets/contact-facebook.svg",
    "assets/contact-phone.svg",
]


def bust_readme_cache():
    content = README_PATH.read_text(encoding="utf-8")

    updated_hashes = {}
    for card in CARDS:
        card_path = Path(card)
        if not card_path.exists():
            continue
        digest = hashlib.sha256(card_path.read_bytes()).hexdigest()[:8]
        updated_hashes[card] = digest
        pattern = rf'src="(?:\.|{re.escape(RAW_BASE)})/{re.escape(card)}(?:\?[^"]*)?"'
        replacement = f'src="{RAW_BASE}/{card}?v={digest}"'
        content = re.sub(pattern, replacement, content)

    README_PATH.write_text(content, encoding="utf-8")
    print(f"Updated cache-busting hashes in {README_PATH}:")
    for card, digest in updated_hashes.items():
        print(f"  - {card}: {digest}")


if __name__ == "__main__":
    bust_readme_cache()
