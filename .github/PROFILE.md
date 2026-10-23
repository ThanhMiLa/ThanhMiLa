# Profile maintenance

The public profile is rendered from `README.md` and the SVGs in `assets/`.

```sh
# Rebuild visuals from the last successful data snapshot (no network).
python3 .github/scripts/build_profile.py

# Fetch GitHub repositories, the public contribution calendar, and LeetCode stats.
python3 .github/scripts/build_profile.py --refresh
```

Edit `PROJECTS` in `build_profile.py` to change the three featured repositories, descriptions, and tags. If the repository names change, also update their links in `README.md`, cache paths in `bust_cache.py`, and the workflow's staged asset paths. Edit `TECH` to change badge labels, colors, or local Devicon logos.

The **Refresh profile** workflow runs every six hours and supports manual runs. It uses the built-in `GITHUB_TOKEN`; no additional secret or external statistics image service is required. Failed sources keep their last successful data and timestamp; successful sources still update, and the workflow reports the incomplete refresh.

GitHub metrics cover the **displayed calendar**, rather than lifetime contributions. Current streak allows an unfinished day with no contributions, as long as yesterday was active. The calendar is the public GitHub profile view, so private contribution details are not fetched. All statistics come from real responses saved in `assets/profile-data.json`.

The tech animation is self-contained SVG/CSS: badges travel clockwise around a rectangle without rotating their labels. The static positions remain visible when animations are disabled, and `prefers-reduced-motion` disables movement. There is no JavaScript, iframe, remote font, or external image dependency inside the SVGs.

The repository contains only the current profile assets, their source logos and data snapshot, the renderer, the cache helper, and the refresh workflow. Obsolete artwork and updater scripts from the previous design have been removed.
