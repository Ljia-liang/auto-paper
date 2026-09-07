from __future__ import annotations

import re
import os
from difflib import SequenceMatcher

import httpx

from .models import DomainConfig, Paper


class GitHubCodeEnricher:
    """Best-effort public repository matcher with conservative title similarity."""

    def __init__(self, timeout: float = 20.0, max_queries: int = 5):
        self.timeout = timeout
        self.max_queries = max_queries

    def enrich(self, papers: list[Paper], domain: DomainConfig) -> list[Paper]:
        if not papers:
            return papers
        for paper in papers[: self.max_queries]:
            # Search per title: a domain-wide query causes one generic repository
            # to be incorrectly attributed to many unrelated papers.
            repos = self._search(f'"{paper.title}"')
            matches = self._matches(paper, repos)
            if matches:
                paper.code_available = True
                paper.code_urls = sorted({str(url) for url in [*paper.code_urls, *matches]})
        return papers

    def _search(self, query: str) -> list[dict]:
        headers = {"Accept": "application/vnd.github+json"}
        if os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        try:
            response = httpx.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "per_page": 30, "sort": "stars"},
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {403, 429}:
                return []
            raise
        return response.json().get("items", [])

    @staticmethod
    def _matches(paper: Paper, repos: list[dict]) -> list[str]:
        title_tokens = set(re.findall(r"[a-z0-9]+", paper.title.lower()))
        matches: list[str] = []
        for repo in repos:
            haystack = " ".join(
                [repo.get("name", ""), repo.get("description", ""), repo.get("full_name", "")]
            ).lower()
            overlap = len(title_tokens & set(re.findall(r"[a-z0-9]+", haystack)))
            ratio = SequenceMatcher(None, paper.title.lower(), haystack).ratio()
            description = (repo.get("description") or "").lower()
            # A repository description containing the title is strong evidence;
            # short-name overlap alone is not enough to claim paper code.
            if ratio >= 0.58 or (overlap >= 4 and "re-identification" in description):
                matches.append(repo.get("html_url", ""))
        return [url for url in matches if url]
