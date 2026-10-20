"""Reads a user's PUBLIC GitHub repositories and detects technologies from their languages and topics.
Nothing is stored; the username is only used for this one request."""
import re
from collections import Counter

import httpx
from sqlalchemy.orm import Session

from app.normalize import resolve_technology

USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


class GithubError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def fetch_repos(client: httpx.Client, username: str) -> list[dict]:
    """Most recently pushed original (non-fork) public repositories, up to 100."""
    if not USERNAME_RE.match(username):
        raise GithubError(422, "That does not look like a valid GitHub username")
    try:
        resp = client.get(f"https://api.github.com/users/{username}/repos",
                          params={"per_page": 100, "sort": "pushed", "type": "owner"})
    except httpx.HTTPError:
        raise GithubError(503, "Could not reach GitHub. Try again in a moment.")
    if resp.status_code == 404:
        raise GithubError(404, f"GitHub user '{username}' was not found")
    if resp.status_code in (403, 429):
        raise GithubError(503, "GitHub rate limit reached. Try again later or add your skills manually.")
    if resp.status_code != 200:
        raise GithubError(503, "GitHub returned an unexpected error. Try again later.")
    return [r for r in resp.json() if not r.get("fork")]


def detect_technologies(db: Session, repos: list[dict]) -> Counter:
    """tech_id -> number of repositories that use it (via main language or topics)."""
    counts: Counter = Counter()
    for repo in repos:
        names = [repo.get("language")] + list(repo.get("topics") or [])
        found = set()
        for name in names:
            if name and (tech := resolve_technology(db, name)):
                found.add(tech.id)
        counts.update(found)
    return counts
