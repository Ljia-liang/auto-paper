import json
from pathlib import Path

from auto_paper.models import DomainConfig, Paper
from auto_paper.pipeline import ReviewPipeline
from auto_paper.retrieval import extract_first_page_code_urls


class FakeSource:
    def search(self, query, *, from_year, limit):
        return [
            Paper(
                paper_id="accepted",
                title="A VI-ReID method on SYSU-MM01",
                year=2025,
                open_access=True,
                code_available=True,
                code_urls=["https://github.com/example/reid"],
            ),
            Paper(
                paper_id="rejected",
                title="A method without released implementation",
                year=2025,
                open_access=True,
                code_available=False,
            ),
        ]


class FakeEnricher:
    def enrich(self, papers, domain):
        return papers


def test_pipeline_enforces_open_access_code_and_dataset_rules():
    domain = DomainConfig(
        name="VI-ReID", aliases=["VI-ReID"], datasets=["SYSU-MM01", "RegDB"]
    )
    result = ReviewPipeline(domain, FakeSource(), code_enricher=FakeEnricher()).run(
        "visible infrared person re-identification", download=False
    )
    assert [paper.paper_id for paper in result.papers] == ["accepted"]
    assert result.papers[0].screening_reason.startswith("纳入")


def test_pdf_first_page_code_url_normalizes_line_wrapped_links():
    text = "Code is available at https://githu\n b.com/author/code-for-MULT.\nKeywords"
    assert extract_first_page_code_urls(text) == ["https://github.com/author/code-for-MULT"]


def test_distributable_plugin_contains_runtime_and_launcher():
    root = Path(__file__).resolve().parents[1]
    plugin = root / "plugins" / "auto-paper-review"
    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((plugin / ".mcp.json").read_text(encoding="utf-8"))

    assert manifest["mcpServers"] == "./.mcp.json"
    assert (plugin / "runtime" / "src" / "auto_paper" / "mcp_server.py").is_file()
    assert (plugin / "config" / "domains" / "vit_reid.yaml").is_file()
    assert (plugin / "requirements-runtime.txt").is_file()
    assert mcp["mcpServers"]["auto-paper"]["args"] == ["scripts/launch_mcp.py"]
