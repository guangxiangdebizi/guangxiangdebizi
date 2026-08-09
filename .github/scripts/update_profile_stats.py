from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError
from xml.sax.saxutils import escape


OWNER = os.environ.get("PROFILE_OWNER", "guangxiangdebizi")
OUTPUT_PATH = Path(os.environ.get("PROFILE_STATS_PATH", "assets/total-stars.svg"))


def fetch_json(url: str, headers: dict[str, str]) -> list[dict]:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=30
            ) as response:
                payload = json.load(response)
            if not isinstance(payload, list):
                raise RuntimeError("GitHub API returned an unexpected response")
            return payload
        except (HTTPError, URLError):
            if attempt == 2:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("GitHub API request failed")


def fetch_owned_repositories(owner: str, token: str | None) -> list[dict]:
    repositories: list[dict] = []
    page = 1
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{owner}-profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while True:
        query = urllib.parse.urlencode(
            {"per_page": 100, "page": page, "type": "owner", "sort": "full_name"}
        )
        batch = fetch_json(
            f"https://api.github.com/users/{owner}/repos?{query}", headers
        )

        repositories.extend(batch)
        if len(batch) < 100:
            return repositories

        page += 1


def render_badge(total_stars: int) -> str:
    value = f"{total_stars:,}"
    label_width = 82
    value_width = max(46, 18 + len(value) * 7)
    width = label_width + value_width
    aria_label = escape(f"Total stars: {value}")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{aria_label}">
  <title>{aria_label}</title>
  <clipPath id="badge">
    <rect width="{width}" height="20" rx="3" />
  </clipPath>
  <g clip-path="url(#badge)">
    <rect width="{label_width}" height="20" fill="#24292f" />
    <rect x="{label_width}" width="{value_width}" height="20" fill="#bf8700" />
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_width / 2}" y="14">total stars</text>
    <text x="{label_width + value_width / 2}" y="14">{escape(value)}</text>
  </g>
</svg>
"""


def main() -> None:
    repositories = fetch_owned_repositories(OWNER, os.environ.get("GITHUB_TOKEN"))
    original_repositories = [repository for repository in repositories if not repository["fork"]]
    total_stars = sum(repository["stargazers_count"] for repository in original_repositories)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_badge(total_stars), encoding="utf-8", newline="\n")
    print(f"Updated {OUTPUT_PATH} from {len(original_repositories)} repositories: {total_stars} stars")


if __name__ == "__main__":
    main()
