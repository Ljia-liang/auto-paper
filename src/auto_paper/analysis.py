from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

import httpx

from .fulltext import FullTextDocument
from .models import (
    DomainConfig,
    Evidence,
    InnovationCandidate,
    MethodRecord,
    MetricResult,
    Paper,
)


class AnalysisBundle(dict):
    """Typed-by-convention result returned by an analysis backend."""


class Analyzer(Protocol):
    def analyze(
        self, topic: str, domain: DomainConfig, papers: list[Paper], documents: list[FullTextDocument]
    ) -> AnalysisBundle: ...


def _as_bundle(payload: dict[str, Any]) -> AnalysisBundle:
    evidence = [Evidence.model_validate(row) for row in payload.get("evidence", [])]
    evidence_ids = {item.paper_id: [] for item in evidence}
    for item in evidence:
        evidence_ids.setdefault(item.paper_id, []).append(item.paper_id)
    metrics = [MetricResult.model_validate(row) for row in payload.get("metrics", [])]
    methods = [MethodRecord.model_validate(row) for row in payload.get("methods", [])]
    innovations = [InnovationCandidate.model_validate(row) for row in payload.get("innovations", [])]
    return AnalysisBundle(
        evidence=evidence,
        metrics=metrics,
        methods=methods,
        trends=[str(item) for item in payload.get("trends", [])],
        innovations=innovations,
    )


class HeuristicAnalyzer:
    """No-key fallback. It creates a transparent draft, never synthetic claims."""

    def analyze(self, topic, domain, papers, documents):
        return AnalysisBundle(
            evidence=[],
            metrics=[],
            methods=[
                MethodRecord(
                    name="Unparsed method",
                    key_idea="Full-text/model analysis is required.",
                    paper_ids=[paper.paper_id for paper in papers],
                )
            ] if papers else [],
            trends=["Pending model-backed extraction of methods and comparable metrics."],
            innovations=[],
        )


class OpenAIAnalyzer:
    """OpenAI-compatible JSON analyzer; supports gateways exposing chat completions."""

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None, timeout: float = 120.0):
        self.api_key = api_key
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout

    def analyze(self, topic, domain, papers, documents):
        paper_rows = [paper.model_dump(mode="json") for paper in papers]
        # Keep gateway requests bounded; full PDFs can be hundreds of pages.
        # The extractor preserves the beginning of each paper (abstract/method setup),
        # while a later table-specific stage can process remaining pages.
        text_rows = [{"paper_id": doc.paper_id, "text": self._analysis_excerpt(doc.text)} for doc in documents if doc.text]
        schema_hint = {
            "evidence": [{"paper_id": "", "claim": "", "quote": "", "location": "", "confidence": "high|medium|low"}],
            "metrics": [{"paper_id": "", "method": "", "dataset": "SYSU-MM01|RegDB", "protocol": "", "metrics": {"rank_1": 0, "mAP": 0}, "evidence_ids": []}],
            "methods": [{"name": "", "year": 2025, "category": "", "key_idea": "", "strengths": [], "limitations": [], "paper_ids": []}],
            "trends": ["evidence-backed trend"],
            "innovations": [{"title": "", "problem": "", "evidence": [], "proposed_direction": "", "validation_plan": [], "risks": [], "novelty_status": "unverified", "evidence_ids": []}],
        }
        prompt = (
            f"Topic: {topic}\nDomain: {domain.model_dump_json()}\n"
            "请使用中文输出所有可读字段（方法名称可保留官方英文缩写）。只分析提供的论文和摘录，不要编造数值或引用。 "
            "Analyze only the supplied papers and excerpts. Do not invent values or citations. "
            "For every factual claim, create an evidence row with an exact quote and paper_id. "
            "Metrics are comparable only when dataset/protocol are explicit. Return JSON matching this shape:\n"
            + json.dumps(schema_hint, ensure_ascii=False)
            + "\nPapers:\n" + json.dumps(paper_rows, ensure_ascii=False)
            + "\nFull-text excerpts:\n" + json.dumps(text_rows, ensure_ascii=False)
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a rigorous literature-review analyst."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 6000,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPError:
                # Retry with metadata and abstracts only when a gateway rejects a large request.
                compact_prompt = (
                    f"主题：{topic}\n请用中文，仅基于论文元数据和摘要，输出同样的 JSON 结构；不要编造指标。\n"
                    + json.dumps(schema_hint, ensure_ascii=False)
                    + "\n论文：\n" + json.dumps(paper_rows, ensure_ascii=False)
                )
                compact_payload = dict(payload)
                compact_payload["messages"] = [
                    {"role": "system", "content": "你是严谨的文献综述分析员。"},
                    {"role": "user", "content": compact_prompt},
                ]
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=compact_payload)
                response.raise_for_status()
        body = response.json()
        raw = ((body.get("choices") or [{}])[0].get("message") or {}).get("content")
        if not raw:
            raise ValueError("Model response did not contain output_text")
        return _as_bundle(json.loads(raw))

    @staticmethod
    def _analysis_excerpt(text: str) -> str:
        """Keep abstract/method context plus windows around evaluation tables."""
        if len(text) <= 7000:
            return text
        head = text[:3000]
        anchors = list(re.finditer(r"SYSU[- ]?MM01|RegDB|Rank[- ]?1|mAP|mINP", text, re.I))
        windows = []
        for match in anchors[:12]:
            start, end = max(0, match.start() - 500), min(len(text), match.end() + 900)
            windows.append(text[start:end])
        return head + "\n\n[实验表格/评测证据片段]\n" + "\n---\n".join(windows)[:5000]


def default_analyzer() -> Analyzer:
    key = os.getenv("OPENAI_API_KEY")
    return OpenAIAnalyzer(key) if key else HeuristicAnalyzer()
