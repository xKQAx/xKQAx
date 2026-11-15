#!/usr/bin/env python3
"""Generate a self-hosted SVG summary from public GitHub repository data."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USERNAME = "xKQAx"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "github-stats.svg"
API_URL = f"https://api.github.com/users/{USERNAME}/repos"
LANGUAGE_COLORS = ["#65D9FF", "#9487FF", "#FF9D70", "#71E0B2"]


def fetch_repositories() -> list[dict]:
    repositories: list[dict] = []
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "xKQAx-profile-stats-generator",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    page = 1
    while True:
        request = Request(
            f"{API_URL}?type=owner&sort=updated&per_page=100&page={page}",
            headers=headers,
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"GitHub API request failed: {error}") from error

        if not isinstance(data, list):
            raise RuntimeError("GitHub API returned an unexpected response")
        repositories.extend(data)
        if len(data) < 100:
            return repositories
        page += 1


def render_svg(repositories: list[dict]) -> str:
    originals = [repo for repo in repositories if not repo.get("fork", False)]
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in originals)
    forks = sum(int(repo.get("forks_count", 0)) for repo in originals)
    languages = Counter(
        repo["language"] for repo in originals if repo.get("language")
    )
    top_languages = languages.most_common(4)
    total_language_repositories = sum(languages.values())
    updated = datetime.now(timezone.utc).strftime("%b %d, %Y UTC")

    metrics = [
        ("PUBLIC REPOS", f"{len(repositories):,}"),
        ("STARS EARNED", f"{stars:,}"),
        ("FORKS", f"{forks:,}"),
        ("LANGUAGES", f"{len(languages):,}"),
    ]
    metric_markup = []
    for index, (label, value) in enumerate(metrics):
        x = 48 + index * 252
        metric_markup.append(
            f'<g transform="translate({x} 0)">'
            f'<text x="0" y="86" class="label">{escape(label)}</text>'
            f'<text x="0" y="132" class="value">{escape(value)}</text>'
            "</g>"
        )
        if index:
            divider_x = x - 24
            metric_markup.append(
                f'<path d="M{divider_x} 52v98" stroke="#263453"/>'
            )

    language_markup = []
    if top_languages:
        x_positions = [48, 303, 558, 813]
        for index, (language, count) in enumerate(top_languages):
            x = x_positions[index]
            color = LANGUAGE_COLORS[index]
            proportion = count / total_language_repositories
            bar_width = max(8, round(214 * proportion))
            language_markup.append(
                f'<g transform="translate({x} 0)">'
                f'<circle cx="5" cy="203" r="4" fill="{color}"/>'
                f'<text x="17" y="208" class="language">{escape(language)}</text>'
                f'<text x="214" y="208" text-anchor="end" class="language-count">{count} repos</text>'
                f'<rect x="0" y="224" width="214" height="6" rx="3" fill="#263453"/>'
                f'<rect x="0" y="224" width="{bar_width}" height="6" rx="3" fill="{color}"/>'
                "</g>"
            )
    else:
        language_markup.append(
            '<text x="48" y="215" class="language">No primary language data available yet.</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="286" viewBox="0 0 1060 286" role="img" aria-labelledby="title description">
  <title id="title">GitHub public repository snapshot for {USERNAME}</title>
  <desc id="description">{len(repositories)} public repositories, {stars} stars earned across original repositories, {forks} forks, and {len(languages)} primary languages.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1060" y2="286" gradientUnits="userSpaceOnUse">
      <stop stop-color="#10182B"/><stop offset="1" stop-color="#17142D"/>
    </linearGradient>
    <linearGradient id="accent" x1="48" y1="0" x2="310" y2="0" gradientUnits="userSpaceOnUse">
      <stop stop-color="#65D9FF"/><stop offset="1" stop-color="#A27BFF"/>
    </linearGradient>
    <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="#AAB7FF" fill-opacity=".08"/>
    </pattern>
    <style>
      .label {{ fill:#9BA9C8;font:600 11px 'Segoe UI',Arial,sans-serif;letter-spacing:1.2px }}
      .value {{ fill:#F3F6FF;font:700 34px 'Segoe UI',Arial,sans-serif }}
      .language {{ fill:#E2E8FA;font:600 13px 'Segoe UI',Arial,sans-serif }}
      .language-count {{ fill:#92A0BF;font:500 11px 'Segoe UI',Arial,sans-serif }}
      .meta {{ fill:#8290AF;font:500 10px 'Segoe UI',Arial,sans-serif;letter-spacing:.6px }}
    </style>
  </defs>
  <rect x="1" y="1" width="1058" height="284" rx="20" fill="url(#bg)" stroke="#293451" stroke-width="2"/>
  <rect x="2" y="2" width="1056" height="282" rx="19" fill="url(#dots)"/>
  <rect x="48" y="28" width="58" height="3" rx="1.5" fill="url(#accent)"/>
  <text x="118" y="34" class="label">PUBLIC CODE · {USERNAME.upper()}</text>
  {''.join(metric_markup)}
  <path d="M48 169h964" stroke="#293451"/>
  <text x="48" y="190" class="label">PRIMARY LANGUAGES · BY REPOSITORY COUNT</text>
  {''.join(language_markup)}
  <text x="1012" y="263" text-anchor="end" class="meta">UPDATED {escape(updated)} · GITHUB PUBLIC API</text>
</svg>
'''


def main() -> None:
    repositories = fetch_repositories()
    svg = render_svg(repositories)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Updated {OUTPUT.relative_to(OUTPUT.parents[1])}")


if __name__ == "__main__":
    main()
