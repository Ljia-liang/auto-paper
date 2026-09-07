"""MCP adapter for AI agents.

The Codex plugin launches the bundled copy through its first-use bootstrapper.
For standalone development, install ``.[agent]`` and run ``auto-paper-mcp``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .analysis import HeuristicAnalyzer
from .exporters import write_excel, write_innovations_pdf, write_json, write_markdown, write_methodology_pdf
from .fulltext import FullTextStage
from .models import ReviewResult
from .pipeline import ReviewPipeline, load_domain
from .retrieval import OpenAlexSource, build_query, filter_papers
from .code_enrichment import GitHubCodeEnricher


def _data_root() -> Path:
    """Return a writable cache root that is independent of the plugin install."""
    override = os.getenv("AUTO_PAPER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "auto-paper-review"


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("MCP support requires: pip install 'auto-paper[agent]'") from exc

    server = FastMCP("auto-paper")
    domain_path = os.getenv("AUTO_PAPER_DOMAIN", "config/domains/vit_reid.yaml")

    @server.tool()
    def run_literature_review(topic: str, years: int = 5, limit: int = 30) -> str:
        """Retrieve public papers with code and return an evidence-backed review JSON."""
        result = ReviewPipeline(load_domain(domain_path)).run(topic, years=years, limit=limit)
        return result.model_dump_json(indent=2)

    @server.tool()
    def prepare_review_materials(topic: str, years: int = 5, limit: int = 30) -> str:
        """Collect papers, code links and open full-text excerpts for the host Agent to analyze.

        This tool does not call an external model or require an API key. The calling Agent
        should perform the synthesis with its own active model and preserve evidence quotes.
        """
        domain = load_domain(domain_path)
        source = OpenAlexSource()
        candidates = source.search(build_query(domain, topic), from_year=__import__("datetime").date.today().year - years, limit=limit)
        candidates = GitHubCodeEnricher().enrich(candidates, domain)
        papers = filter_papers(candidates, domain)
        docs = FullTextStage(_data_root() / "papers").collect(papers)
        return json.dumps({
            "topic": topic,
            "domain": domain.model_dump(mode="json"),
            "papers": [paper.model_dump(mode="json") for paper in papers],
            "excluded_papers": [paper.model_dump(mode="json") for paper in candidates if paper not in papers],
            "documents": [{"paper_id": doc.paper_id, "text": doc.text, "error": doc.error} for doc in docs],
        }, ensure_ascii=False)

    @server.tool()
    def export_agent_review(review_json: str, output_dir: str = "") -> str:
        """Export a ReviewResult JSON to Markdown, JSON, Excel and two PDFs.

        Pass an absolute output_dir to put results in the active workspace. If omitted,
        files are written beneath the user's Auto Paper data directory.
        """
        result = ReviewResult.model_validate_json(review_json)
        if not output_dir:
            output_dir = str(_data_root() / "agent_review")
        os.makedirs(output_dir, exist_ok=True)
        write_markdown(result, os.path.join(output_dir, "review.md"))
        write_json(result, os.path.join(output_dir, "review.json"))
        write_excel(result, os.path.join(output_dir, "review.xlsx"))
        write_methodology_pdf(result, os.path.join(output_dir, "methodology_review.pdf"))
        write_innovations_pdf(result, os.path.join(output_dir, "innovation_directions.pdf"))
        return os.path.abspath(output_dir)

    @server.tool()
    def review_config() -> str:
        """Return the active domain configuration."""
        return load_domain(domain_path).model_dump_json(indent=2)

    server.run()
