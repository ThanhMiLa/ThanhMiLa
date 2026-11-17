"""Offline regression tests for the profile renderer and refresh pipeline."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
NS = {"s": "http://www.w3.org/2000/svg"}


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".github/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


profile = load_script("build_profile")
cache = load_script("bust_cache")


class AssetTests(unittest.TestCase):
    def test_generated_files_match_readme_and_cache_manifest(self):
        readme = (ROOT / "README.md").read_text()
        sources = re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', readme)
        self.assertEqual(len(sources), len(cache.CARDS))
        self.assertEqual(
            {str(path.relative_to(ROOT)) for path in (ROOT / "assets").glob("*.svg")},
            set(cache.CARDS),
        )
        for card in cache.CARDS:
            with self.subTest(card=card):
                body = (ROOT / card).read_bytes()
                ET.fromstring(body)
                digest = hashlib.sha256(body).hexdigest()[:8]
                self.assertEqual(sources.count(f"{cache.RAW_BASE}/{card}?v={digest}"), 1)

    def test_all_source_logos_are_used_and_credits_are_retained(self):
        used = {f"{name}.svg" for _, name, _ in profile.TECH}
        used.update(project["logo"] for project in profile.PROJECTS)
        used.update({"leetcode.svg", "README.md", "LICENSE"})
        actual = {path.name for path in (ROOT / "assets/icons").iterdir()
                  if path.is_file() and path.name != ".DS_Store"}
        self.assertEqual(actual, used)

    def test_language_totals_match_repository_snapshot(self):
        stats = json.loads(profile.CACHE.read_text())["languages"]
        totals = {}
        for counts in stats["repositories"].values():
            for language, count in counts.items():
                self.assertGreaterEqual(count, 0)
                totals[language] = totals.get(language, 0) + count
        self.assertEqual(stats["bytes"], totals)
        self.assertEqual(stats["repository_count"], len(stats["repositories"]))

    def test_build_and_cache_update_are_reproducible_from_any_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "assets", root / "assets", ignore=shutil.ignore_patterns(".DS_Store"))
            shutil.copytree(ROOT / ".github/scripts", root / ".github/scripts",
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy2(ROOT / "README.md", root / "README.md")
            expected = {path: (ROOT / path).read_bytes() for path in [*cache.CARDS, "README.md"]}
            for _ in range(2):
                for name in ("build_profile", "bust_cache"):
                    result = subprocess.run(
                        [sys.executable, "-B", str(root / ".github/scripts" / f"{name}.py")],
                        cwd=root.parent, capture_output=True, text=True, timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual({path: (root / path).read_bytes() for path in expected}, expected)


class LanguageTests(unittest.TestCase):
    def render(self, counts):
        fragment, description = profile.languages_section(
            {"languages": {"bytes": counts, "updated_at": "2026-11-17"}}, 178,
        )
        return ET.fromstring(profile.svg(1200, 428, fragment, "test", description))

    def test_top_eight_keep_individual_bars_without_combined_chart(self):
        counts = {f"Language{i}": 10 - i for i in range(10)}
        root = self.render(counts)
        labels = [node.text for node in root.findall(".//s:text", NS)]
        self.assertEqual(labels[::2], [f"Language{i}" for i in range(8)])
        self.assertEqual(labels[1], f"{1000 / sum(counts.values()):.1f}%")
        self.assertEqual(len(root.findall(".//s:circle", NS)), 8)
        self.assertEqual(len(root.findall(".//s:rect", NS)), 16)
        self.assertFalse(root.findall(".//s:clipPath", NS))
        self.assertFalse(root.findall(".//s:path", NS))
        for node in root.findall(".//s:rect", NS):
            self.assertLessEqual(float(node.get("x")) + float(node.get("width")), 1200)
            self.assertLessEqual(float(node.get("y")) + float(node.get("height")) + 178, 428)

    def test_empty_single_zero_and_tied_counts(self):
        empty = self.render({})
        self.assertIn("No language data available.", ET.tostring(empty, encoding="unicode"))
        self.assertFalse(empty.findall(".//s:rect", NS))
        single = self.render({"Java": 100})
        self.assertEqual(single.findall(".//s:text", NS)[1].text, "100.0%")
        zero = self.render({"Java": 0})
        self.assertEqual(zero.findall(".//s:text", NS)[1].text, "0.0%")
        tied = self.render({"Python": 10, "Java": 10})
        self.assertEqual(tied.findall(".//s:text", NS)[0].text, "Java")

    def test_repository_selection_deduplicates_and_keeps_explicit_forks(self):
        def repo(name, private=False, fork=False):
            return {"full_name": name, "private": private, "fork": fork,
                    "languages_url": f"https://api.github.com/repos/{name}/languages"}

        primary = repo("ThanhMiLa/primary")
        selected = repo("Org/selected", private=True, fork=True)
        responses = {
            "https://api.github.com/repos/ThanhMiLa/primary": primary,
            "https://api.github.com/repos/Org/selected": selected,
            primary["languages_url"]: {"Java": 20},
            selected["languages_url"]: {"Java": 10, "Kotlin": 5},
        }
        repositories = [
            primary, repo("ThanhMiLa/fork", fork=True), repo("Org/unselected"),
            repo("ThanhMiLa/private", private=True),
        ]
        with mock.patch.object(profile, "ADDITIONAL_LANGUAGE_REPOSITORIES",
                               ("ThanhMiLa/primary", "Org/selected")), \
                mock.patch.object(profile, "fetch", side_effect=lambda url: json.dumps(responses[url])) as fetch:
            result = profile.fetch_language_stats(repositories)
        self.assertEqual(result["bytes"], {"Java": 30, "Kotlin": 5})
        self.assertEqual(result["repository_count"], 2)
        self.assertEqual(result["private_repository_count"], 1)
        self.assertEqual(result["included_forks"], ["Org/selected"])
        self.assertEqual(fetch.call_args_list.count(mock.call(primary["languages_url"])), 1)


class CacheTests(unittest.TestCase):
    def test_missing_asset_fails_without_rewriting_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            readme.write_text("original")
            with mock.patch.multiple(cache, ROOT=root, README_PATH=readme):
                with self.assertRaises(FileNotFoundError):
                    cache.bust_readme_cache()
            self.assertEqual(readme.read_text(), "original")

    def test_missing_or_duplicate_image_reference_fails(self):
        for references in (0, 2):
            with self.subTest(references=references), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "card.svg").write_text("<svg/>")
                readme = root / "README.md"
                content = '<img src="./card.svg" />' * references
                readme.write_text(content)
                with mock.patch.multiple(cache, ROOT=root, README_PATH=readme, CARDS=["card.svg"]):
                    with self.assertRaises(ValueError):
                        cache.bust_readme_cache()
                self.assertEqual(readme.read_text(), content)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads(profile.CACHE.read_text())

    def test_contribution_parser_joins_counts_and_rejects_missing_tooltips(self):
        parser = profile.ContributionParser()
        parser.feed('<td id="day" data-date="2026-11-17" data-level="3"></td>'
                    '<tool-tip for="day">1,234 contributions</tool-tip>')
        self.assertEqual(parser.days(), [{"date": "2026-11-17", "level": 3, "count": 1234}])
        incomplete = profile.ContributionParser()
        incomplete.feed('<td id="day" data-date="2026-11-17" data-level="3"></td>')
        with self.assertRaises(ValueError):
            incomplete.days()

    def test_refresh_saves_successful_sources_and_preserves_failed_languages(self):
        previous = copy.deepcopy(self.snapshot["languages"])
        repositories = [
            dict(self.snapshot["projects"][item["repo"]], name=item["repo"])
            for item in profile.PROJECTS
        ]
        repositories[0]["stargazers_count"] += 1
        lc = self.snapshot["leetcode"]
        response = {"data": {
            "allQuestionsCount": [{"difficulty": key, "count": value} for key, value in lc["questions"].items()],
            "matchedUser": {"profile": {"ranking": lc["ranking"]},
                            "submitStatsGlobal": {"acSubmissionNum": [
                                {"difficulty": key, "count": value} for key, value in lc["solved"].items()
                            ]}},
        }}

        def fetch(url, payload=None):
            if url.startswith("https://github.com/"):
                return ('<td id="day" data-date="2026-11-17" data-level="1"></td>'
                        '<tool-tip for="day">3 contributions</tool-tip>')
            self.assertEqual(url, "https://leetcode.com/graphql")
            return json.dumps(response)

        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(profile, "CACHE", Path(directory) / "snapshot.json"), \
                mock.patch.object(profile, "fetch_public_repositories", return_value=repositories), \
                mock.patch.object(profile, "fetch", side_effect=fetch), \
                mock.patch.object(profile, "fetch_language_stats", side_effect=OSError("unavailable")), \
                contextlib.redirect_stderr(io.StringIO()):
            errors = profile.refresh(self.snapshot)
            self.assertEqual(json.loads(profile.CACHE.read_text()), self.snapshot)
        self.assertEqual(errors, ["languages"])
        self.assertEqual(self.snapshot["languages"], previous)
        self.assertEqual(self.snapshot["projects"]["codelearning"]["stargazers_count"],
                         repositories[0]["stargazers_count"])
        self.assertEqual(self.snapshot["github"]["days"][0]["count"], 3)

    def test_missing_initial_snapshot_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(profile, "CACHE", Path(directory) / "snapshot.json"), \
                mock.patch.object(profile, "fetch_public_repositories", side_effect=OSError("unavailable")), \
                mock.patch.object(profile, "fetch", side_effect=OSError("unavailable")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                profile.refresh({})
            self.assertFalse(profile.CACHE.exists())

    def test_workflow_commits_and_pushes_snapshot_only_changes(self):
        workflow = (ROOT / ".github/workflows/update-activity.yml").read_text()
        commit_step = re.search(
            r"      - name: Commit refreshed assets\n        run: \|\n((?:          .*\n)+)",
            workflow,
        )
        self.assertIsNotNone(commit_step)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            root.mkdir()

            def git(*args):
                result = subprocess.run(
                    ["git", *args], cwd=root, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout.strip()

            for card in cache.CARDS:
                path = root / card
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<svg/>")
            snapshot = root / "assets/profile-data.json"
            snapshot.write_text('{"version": 1}\n')
            (root / "README.md").write_text("unchanged README\n")
            git("init", "--initial-branch=main")
            git("init", "--bare", str(Path(directory) / "origin.git"))
            git("config", "user.name", "Profile tests")
            git("config", "user.email", "profile-tests@example.invalid")
            git("add", ".")
            git("commit", "-m", "Initial test assets")
            git("remote", "add", "origin", str(Path(directory) / "origin.git"))
            git("push", "-u", "origin", "main")
            snapshot.write_text('{"version": 2}\n')
            result = subprocess.run(
                ["bash", "-e", "-c", textwrap.dedent(commit_step[1])],
                cwd=root, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
                             "assets/profile-data.json")
            remote_sha = git("ls-remote", "origin", "refs/heads/main").split()[0]
            self.assertEqual(remote_sha, git("rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
