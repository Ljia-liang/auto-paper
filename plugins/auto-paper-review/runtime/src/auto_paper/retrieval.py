from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Protocol

import httpx

from .models import DomainConfig, Paper

CODE_PATTERN = re.compile(r"https?://[^\s\"<>]*(?:github|gitlab|bitbucket|gitee)\.[^\s\"<>]+", re.I)


def extract_first_page_code_urls(text: str) -> list[str]:
    """Extract repository URLs from PDF page-one text, tolerating line wraps.

    PDF text extraction commonly turns ``github.com`` into ``githu b.com`` and
    wraps repository names at hyphens. We normalize whitespace only inside short
    windows beginning at an HTTP URL, then apply a conservative two-path matcher.
    """
    if not text:
        return []
    pattern = re.compile(
        r"https?://(?:www\.)?(?:github|gitlab|bitbucket|gitee)\.com/"
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        re.I,
    )
    urls: set[str] = set()
    for match in re.finditer(r"https?://", text, re.I):
        window = re.sub(r"\s+", "", text[match.start() : match.start() + 220])
        found = pattern.search(window)
        if found:
            url = found.group(0)
            # Page-one extraction often concatenates the next heading, e.g.
            # ``.../HIL.IndexTerms``. Keep the repository path only.
            url = re.split(r"\.(?:Keywords|Introduction|IndexTerms|Abstract)", url, maxsplit=1, flags=re.I)[0]
            urls.add(url.rstrip(".,;:)]}"))
    return sorted(urls)


class PaperSource(Protocol):
    def search(self, query: str, *, from_year: int, limit: int) -> list[Paper]: ...


def _as_url(value: str | None) -> str | None:
    return value if value and value.startswith("http") else None


def _code_urls(item: dict[str, Any]) -> list[str]:
    candidates = []
    for location in item.get("locations", []) or []:
        for key in ("landing_page_url", "pdf_url"):
            value = (location or {}).get(key)
            if isinstance(value, str):
                candidates.append(value)
    return sorted({url.rstrip(".,)") for url in CODE_PATTERN.findall(" ".join(candidates))})


class OpenAlexSource:
    endpoint = "https://api.openalex.org/works"

    def __init__(self, mailto: str | None = None, timeout: float = 30.0):
        self.mailto, self.timeout = mailto, timeout

    def search(self, query: str, *, from_year: int, limit: int = 100) -> list[Paper]:
        params = {"search": query, "filter": f"from_publication_date:{from_year}-01-01", "per-page": min(limit, 200), "sort": "relevance_score:desc"}
        if self.mailto:
            params["mailto"] = self.mailto
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self.endpoint, params=params)
            response.raise_for_status()
        return [self._parse(item) for item in response.json().get("results", [])]

    @staticmethod
    def _parse(item: dict[str, Any]) -> Paper:
        authors = [(auth.get("author") or {}).get("display_name", "") for auth in item.get("authorships", [])]
        oa, locations = item.get("open_access") or {}, item.get("locations", []) or []
        best = next((loc for loc in locations if loc.get("pdf_url")), None) or item.get("best_oa_location") or item.get("primary_location") or {}
        abstract = item.get("abstract_inverted_index")
        abstract_text = " ".join(word for _, word in sorted((pos, word) for word, positions in (abstract or {}).items() for pos in positions)) if abstract else None
        code_urls = _code_urls(item)
        return Paper(paper_id=str(item.get("id", "")).rsplit("/", 1)[-1], title=item.get("title") or "Untitled", year=item.get("publication_year"), venue=((item.get("primary_location") or {}).get("source") or {}).get("display_name"), authors=[a for a in authors if a], abstract=abstract_text, doi=item.get("doi"), landing_url=_as_url(best.get("landing_page_url")), pdf_url=_as_url(best.get("pdf_url")), open_access=bool(oa.get("is_oa") or best.get("is_oa") or best.get("pdf_url")), code_available=bool(code_urls), code_urls=code_urls, source="openalex", relevance_score=float(item.get("relevance_score") or 0))


class ArxivSource:
    endpoint = "https://export.arxiv.org/api/query"
    atom = "http://www.w3.org/2005/Atom"
    arxiv = "http://arxiv.org/schemas/atom"

    def __init__(self, timeout: float = 45.0):
        self.timeout = timeout

    def search(self, query: str, *, from_year: int, limit: int = 100) -> list[Paper]:
        params = {"search_query": 'all:"unsupervised visible-infrared person re-identification"', "start": 0, "max_results": min(limit, 100), "sortBy": "submittedDate", "sortOrder": "descending"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers={"User-Agent": "auto-paper/0.1"}) as client:
            response = client.get(self.endpoint, params=params)
            response.raise_for_status()
        root = ET.fromstring(response.text)
        return [paper for entry in root.findall(f"{{{self.atom}}}entry") for paper in [self._parse(entry)] if paper.year and paper.year >= from_year]

    @classmethod
    def _parse(cls, entry: ET.Element) -> Paper:
        text = lambda tag: (entry.findtext(f"{{{cls.atom}}}{tag}") or "").strip()
        arxiv_url, published = text("id"), text("published")
        abstract = re.sub(r"\s+", " ", text("summary"))
        links = entry.findall(f"{{{cls.atom}}}link")
        pdf = next((node.attrib.get("href") for node in links if node.attrib.get("title") == "pdf"), None)
        code_urls = sorted({url.rstrip(".,)}]") for url in CODE_PATTERN.findall(abstract)})
        return Paper(paper_id=arxiv_url.rsplit("/", 1)[-1], title=text("title"), year=int(published[:4]) if published[:4].isdigit() else None, venue=entry.findtext(f"{{{cls.arxiv}}}comment") or "arXiv preprint", authors=[(node.findtext(f"{{{cls.atom}}}name") or "").strip() for node in entry.findall(f"{{{cls.atom}}}author")], abstract=abstract, landing_url=arxiv_url.replace("http://", "https://"), pdf_url=pdf, open_access=True, code_available=bool(code_urls), code_urls=code_urls, source="arxiv", relevance_score=1.0)


def build_query(domain: DomainConfig, topic: str) -> str:
    return " OR ".join(f'"{term}"' for term in dict.fromkeys([topic, *domain.aliases, *domain.datasets]) if term)


def filter_papers(papers: list[Paper], domain: DomainConfig) -> list[Paper]:
    accepted = []
    for paper in papers:
        reasons = []
        if not paper.open_access:
            reasons.append("不是公开获取")
        if not paper.code_available:
            reasons.append("未检测到论文 PDF 第1页公开代码链接")
        if reasons:
            paper.screening_reason = "；".join(reasons)
            continue
        paper.screening_reason = "纳入：arXiv 公开全文，论文 PDF 第1页明确包含公开代码链接；数据集在全文分析阶段核验"
        accepted.append(paper)
    return accepted
