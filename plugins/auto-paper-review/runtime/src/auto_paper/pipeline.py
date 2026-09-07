from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .models import DomainConfig, ReviewResult
from .analysis import Analyzer, default_analyzer
from .fulltext import FullTextStage
from .code_enrichment import GitHubCodeEnricher
from .retrieval import ArxivSource, OpenAlexSource, build_query, extract_first_page_code_urls, filter_papers


def load_domain(path: str | Path) -> DomainConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        return DomainConfig.model_validate(yaml.safe_load(handle))


class ReviewPipeline:
    """Orchestrates the four user-facing blocks.

    Extraction, trend analysis and innovation generation are deliberately injectable:
    these steps require a model or domain-specific parser and must return evidence IDs.
    """

    def __init__(
        self,
        domain: DomainConfig,
        source: OpenAlexSource | ArxivSource | None = None,
        analyzer: Analyzer | None = None,
        fulltext: FullTextStage | None = None,
        code_enricher: GitHubCodeEnricher | None = None,
    ):
        self.domain = domain
        self.source = source or ArxivSource()
        self.analyzer = analyzer or default_analyzer()
        self.fulltext = fulltext or FullTextStage()
        self.code_enricher = code_enricher or GitHubCodeEnricher()

    def run(
        self, topic: str, *, years: int | None = None, limit: int = 100, download: bool = True
    ) -> ReviewResult:
        start_year = date.today().year - (years or self.domain.default_years)
        query = build_query(self.domain, topic)
        try:
            candidates = self.source.search(query, from_year=start_year, limit=limit)
        except Exception:
            # Offline/cache mode is useful for reproducible reruns and rate limits.
            candidates = []
        # For arXiv runs, enforce the user's rule literally: code must be present
        # in the arXiv abstract text. Do not infer it from a fuzzy GitHub match.
        if not isinstance(self.source, ArxivSource):
            candidates = self.code_enricher.enrich(candidates, self.domain)
        # For PDF-based reviews, the authoritative code check is page one of the
        # downloaded paper (title/abstract page), not only the arXiv Atom record.
        # Download/extract candidates first, enrich their code evidence, then filter.
        if isinstance(self.source, ArxivSource) and download:
            pre_documents = self.fulltext.collect(candidates, download=True)
            docs_by_id = {doc.paper_id: doc for doc in pre_documents}
            for paper in candidates:
                doc = docs_by_id.get(paper.paper_id)
                page_one_urls = sorted({
                    *(doc.first_page_code_urls or [] if doc else []),
                    *extract_first_page_code_urls(doc.first_page_text if doc else ""),
                })
                if page_one_urls:
                    paper.code_available = True
                    paper.code_urls = sorted({*paper.code_urls, *page_one_urls})
        papers = filter_papers(candidates, self.domain)
        accepted_ids = {paper.paper_id for paper in papers}
        excluded = [paper for paper in candidates if paper.paper_id not in accepted_ids]
        documents = self.fulltext.collect(papers, download=download)
        bundle = self.analyzer.analyze(topic, self.domain, papers, documents)
        return ReviewResult(
            topic=topic,
            generated_at=date.today(),
            domain=self.domain,
            papers=papers,
            excluded_papers=excluded,
            metrics=bundle["metrics"],
            methods=bundle["methods"],
            trends=bundle["trends"],
            innovations=bundle["innovations"],
            evidence=bundle["evidence"],
        )
