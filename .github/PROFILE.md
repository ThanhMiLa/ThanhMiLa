# Profile maintenance

The public profile is rendered from `README.md` and the SVGs in `assets/`. Profile images in `README.md` point directly to Fastly CDN (`raw.githubusercontent.com`) with per-file SHA-256 content hashes (`?v=<hash>`), eliminating 302 redirects and ensuring unchanged cards stay permanently cached on both CDN and visitor browsers.

```sh
# Rebuild visuals from the last successful data snapshot (no network).
python3 .github/scripts/build_profile.py

# Fetch GitHub repositories, the public contribution calendar, and LeetCode stats.
python3 .github/scripts/build_profile.py --refresh
```

Edit `PROJECTS` in `build_profile.py` to change the three featured repositories, titles, and tags. Project descriptions are copied verbatim from each repository's GitHub Description and refreshed automatically with the statistics; line wrapping only changes their layout. Card heights adapt to fit the full descriptions. If the repository names change, also update their links in `README.md`, cache paths in `bust_cache.py`, and the workflow's staged asset paths. Edit `TECH` to change badge labels, colors, or local Devicon logos.

The **Refresh profile** workflow runs every three hours and supports manual runs. It uses the built-in `GITHUB_TOKEN` for repository writes and the existing `GH_PAT` secret for GitHub API reads, including the selected private repositories. `GH_PAT` must retain access to those repositories; no external statistics image service is required. Failed sources keep their last successful data and timestamp; successful sources still update, and the workflow reports the incomplete refresh.

The language card ranks the top six languages by the sum of code bytes returned by GitHub's Languages API for personal public repositories owned by `ThanhMiLa`, plus exactly the repositories in `ADDITIONAL_LANGUAGE_REPOSITORIES`: five selected personal private repositories and two selected organization repositories (one public, one private). Explicit selections override the general fork exclusion: the selected private `fudn-traltb-su26/course-project-hsf302_se20a11_quang_tan_thanh` repository is a fork and is intentionally included. Other forks, organization repositories, and private repositories are excluded; archived original repositories are included. Public repository discovery is paginated and repositories are deduplicated by full owner/name, including if a selected private repository becomes public. Percentages use the total bytes of **all** detected languages as the denominator, so the displayed six percentages may sum to less than 100%. Only language-byte statistics are fetched, not source code. Per-repository counts and included fork names are saved in the snapshot for verification. `GH_PAT` must also have access to the selected private organization repository. A failed repository fetch preserves the previous complete language snapshot rather than publishing incomplete totals.

GitHub metrics cover the **displayed calendar**, rather than lifetime contributions. Current streak allows an unfinished day with no contributions, as long as yesterday was active. The calendar is the public GitHub profile view, so private contribution details are not fetched. All statistics come from real responses saved in `assets/profile-data.json`.

The tech animation is self-contained SVG/CSS: badges travel clockwise around a rectangle without rotating their labels. The static positions remain visible when animations are disabled, and `prefers-reduced-motion` disables movement. There is no JavaScript, iframe, remote font, or external image dependency inside the SVGs.

The repository contains only the current profile assets, their source logos and data snapshot, the renderer, the cache helper, and the refresh workflow. Obsolete artwork and updater scripts from the previous design have been removed.
