from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from .models import Paper


@dataclass
class FullTextDocument:
    paper_id: str
    text: str
    first_page_text: str = ""
    first_page_code_urls: list[str] | None = None
    path: Path | None = None
    error: str | None = None


class FullTextStage:
    """Download and extract only PDFs advertised as open access by the source."""

    def __init__(self, root: str | Path = "artifacts/papers", timeout: float = 60.0):
        self.root = Path(root)
        self.timeout = timeout

    def collect(self, papers: list[Paper], *, download: bool = True) -> list[FullTextDocument]:
        documents: list[FullTextDocument] = []
        for paper in papers:
            if not paper.pdf_url:
                documents.append(FullTextDocument(paper.paper_id, "", error="no OA PDF URL"))
                continue
            path = self.root / f"{paper.paper_id}.pdf"
            try:
                if download and not path.exists():
                    self._download(str(paper.pdf_url), path)
                if not path.exists():
                    documents.append(FullTextDocument(paper.paper_id, "", path=path, error="PDF not downloaded"))
                    continue
                documents.append(self._extract(paper.paper_id, path))
            except Exception as exc:  # keep one bad PDF from aborting the corpus
                documents.append(FullTextDocument(paper.paper_id, "", path=path, error=str(exc)))
        return documents

    def _download(self, url: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(path.suffix + ".part")
        try:
            headers = {"User-Agent": "auto-paper/0.1 (research metadata client)"}
            with httpx.stream("GET", url, headers=headers, timeout=self.timeout, follow_redirects=True) as response:
                response.raise_for_status()
                with partial.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
            partial.replace(path)
        finally:
            if partial.exists():
                partial.unlink()

    @staticmethod
    def _extract(paper_id: str, path: Path) -> FullTextDocument:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages)
        first_page = pages[0] if pages else ""
        code_urls: list[str] = []
        for annotation in (reader.pages[0].get("/Annots", []) if reader.pages else []) or []:
            try:
                target = annotation.get_object().get("/A", {}).get("/URI")
                if isinstance(target, str) and any(host in target.lower() for host in ("github.com", "gitlab.com", "gitee.com", "bitbucket.org")):
                    code_urls.append(target.rstrip(".,;:)]}"))
            except Exception:
                continue
        return FullTextDocument(paper_id, text, first_page_text=first_page, first_page_code_urls=sorted(set(code_urls)), path=path)
