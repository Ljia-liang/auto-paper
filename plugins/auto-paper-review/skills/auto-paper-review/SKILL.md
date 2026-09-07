---
name: auto-paper-review
description: Use the Auto Paper MCP tools to collect an evidence-first literature review and synthesize it with the host Agent model.
---

# Auto Paper Review

For a concrete research direction, call `prepare_review_materials` first. It does not require an API key: it returns screened papers, public code links, and open full-text excerpts. Code availability must be checked on page 1 of the downloaded PDF (including embedded PDF hyperlinks), not only in arXiv metadata. Use the active host Agent model to produce four analysis blocks: domain review, paper list and screening reasons, method evolution, and innovation directions.

Keep exact evidence quotes and paper IDs. Do not invent metrics. Then construct a `ReviewResult` JSON and call `export_agent_review` to create Markdown, JSON, Excel, `methodology_review.pdf`, and `innovation_directions.pdf` artifacts. Pass `output_dir` as an absolute path under the user's active workspace, normally `<workspace>/artifacts/auto-paper-review`. The methodology PDF contains no innovation validation plan; the innovation PDF lists directions only.

The bundled MCP runtime installs its Python dependencies automatically on first use. If startup fails, report the Python version and bootstrap error; Python 3.10 or newer and network access to PyPI are required for the first launch.
