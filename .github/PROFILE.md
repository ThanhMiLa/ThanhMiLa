# Profile maintenance

The public profile is rendered from `README.md` and the SVGs in `assets/`. Profile images in `README.md` point directly to `raw.githubusercontent.com` with per-file SHA-256 content hashes (`?v=<hash>`). Unchanged cards keep the same URL; updated cards receive a new cache key. GitHub/CDN caches may still take a few minutes to serve a newly pushed branch revision.

```sh
# Rebuild visuals from the last successful data snapshot (no network).
python3 .github/scripts/build_profile.py
python3 .github/scripts/bust_cache.py

# Validate assets, source logos, cache keys, and refresh fallback behavior offline.
python3 -B -m unittest discover -s .github/tests -v

# Fetch GitHub repositories, the public contribution calendar, and LeetCode stats.
python3 .github/scripts/build_profile.py --refresh
python3 .github/scripts/bust_cache.py
```

Edit `PROJECTS` in `build_profile.py` to change the three featured repositories, titles, and tags. Project descriptions are copied verbatim from each repository's GitHub Description and refreshed automatically with the statistics; line wrapping only changes their layout. Card heights adapt to fit the full descriptions. If the repository names change, also update their links in `README.md`, cache paths in `bust_cache.py`, and the workflow's staged asset paths. Edit `TECH` to change badge labels, colors, or local Devicon logos.

The **Refresh profile** workflow runs every three hours, supports manual runs on `main`, and runs when profile scripts, tests, workflows, assets, or `README.md` change on `main`. Pull requests targeting `main` run offline validation only, without secrets or write permissions. Validation checks SVG parsing, README cache keys, unused/missing source logos and generated assets, reproducible builds, top-eight rendering, repository selection, and failed-source fallback.

After validation succeeds, the refresh job checks out the latest `main` and uses the built-in `GITHUB_TOKEN` for repository writes and the existing `GH_PAT` secret for GitHub API reads, including the selected private repositories. `GH_PAT` must retain access to those repositories; a missing secret is reported explicitly. No external statistics image service is required. Failed sources keep their last successful data and timestamp; successful sources still update, and the workflow reports the incomplete refresh after saving valid results. Refreshed assets are validated before committing. Snapshot-only changes to `assets/profile-data.json` are committed too, even when the visible cards do not change. Concurrent runs on the same ref are serialized, and both jobs have time limits. Bot commits use `[skip ci]` to avoid refresh loops.

The languages section inside `assets/profile-summary.svg` ranks the top eight languages in a two-column, four-row layout with individual progress bars and no combined chart. Rankings use the sum of code bytes returned by GitHub's Languages API for personal public repositories owned by `ThanhMiLa`, plus exactly the repositories in `ADDITIONAL_LANGUAGE_REPOSITORIES`: five selected personal private repositories and two selected organization repositories (one public, one private). Explicit selections override the general fork exclusion: the selected private `fudn-traltb-su26/course-project-hsf302_se20a11_quang_tan_thanh` repository is a fork and is intentionally included. Other forks, organization repositories, and private repositories are excluded; archived original repositories are included. Public repository discovery is paginated and repositories are deduplicated by full owner/name, including if a selected private repository becomes public. Percentages use the total bytes of **all** detected languages as the denominator, so the displayed eight percentages may sum to less than 100%. Only language-byte statistics are fetched, not source code. Per-repository counts and included fork names are saved in the snapshot for verification. `GH_PAT` must also have access to the selected private organization repository. A failed repository fetch preserves the previous complete language snapshot rather than publishing incomplete totals.

GitHub metrics cover the **displayed calendar**, rather than lifetime contributions. Current streak allows an unfinished day with no contributions, as long as yesterday was active. The calendar is the public GitHub profile view, so private contribution details are not fetched. All statistics come from real responses saved in `assets/profile-data.json`.

The tech animation is self-contained SVG/CSS: badges travel clockwise around a rectangle without rotating their labels. The static positions remain visible when animations are disabled, and `prefers-reduced-motion` disables movement. There is no JavaScript, iframe, remote font, or external image dependency inside the SVGs.

The repository contains only the current profile assets, their source logos and data snapshot, the renderer, the cache helper, offline regression tests, and the refresh workflow. The logo license and attribution files are required and should be retained. Local `.DS_Store`, `__pycache__`, and `.pyc` files are ignored by Git.
