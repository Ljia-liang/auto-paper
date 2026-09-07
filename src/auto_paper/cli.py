from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from .exporters import (
    write_excel,
    write_innovations_pdf,
    write_json,
    write_markdown,
    write_methodology_pdf,
)
from .fulltext import FullTextStage
from .pipeline import ReviewPipeline, load_domain


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an evidence-first literature review corpus")
    parser.add_argument("topic", help="Specific research direction")
    parser.add_argument("--domain", default="config/domains/vit_reid.yaml")
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", default="artifacts")
    parser.add_argument("--no-download", action="store_true", help="Do not download open-access PDFs")
    args = parser.parse_args()

    console = Console()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    try:
        result = ReviewPipeline(load_domain(args.domain), fulltext=FullTextStage(output / "papers")).run(
            args.topic, years=args.years, limit=args.limit, download=not args.no_download
        )
    except Exception as error:
        console.print(f"[yellow]Analysis failed; no fabricated results were written: {error}[/yellow]")
        raise
    write_markdown(result, output / "review.md")
    write_json(result, output / "review.json")
    try:
        write_excel(result, output / "review.xlsx")
        write_methodology_pdf(result, output / "综述及方法论.pdf")
        write_innovations_pdf(result, output / "创新方向.pdf")
    except RuntimeError as error:
        console.print(f"[yellow]{error}[/yellow]")
    console.print(f"Accepted {len(result.papers)} papers. Artifacts: {output.resolve()}")


if __name__ == "__main__":
    main()
