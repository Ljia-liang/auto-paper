from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class DomainConfig(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    required_properties: list[str] = Field(
        default_factory=lambda: ["open_access", "code_available"]
    )
    metric_schema: list[str] = Field(default_factory=list)
    default_years: int = 5


class Paper(BaseModel):
    paper_id: str
    title: str
    year: int | None = None
    venue: str | None = None
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    doi: str | None = None
    landing_url: HttpUrl | None = None
    pdf_url: HttpUrl | None = None
    open_access: bool = False
    code_available: bool = False
    code_urls: list[str] = Field(default_factory=list)
    source: str = "unknown"
    relevance_score: float = 0.0
    screening_reason: str = ""


class Evidence(BaseModel):
    paper_id: str
    claim: str
    quote: str
    source_url: HttpUrl | None = None
    location: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class MetricResult(BaseModel):
    paper_id: str
    method: str
    dataset: str
    protocol: str | None = None
    metrics: dict[str, float | str] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class MethodRecord(BaseModel):
    name: str
    year: int | None = None
    category: str | None = None
    key_idea: str = ""
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)


class InnovationCandidate(BaseModel):
    title: str
    problem: str
    evidence: list[str] = Field(default_factory=list)
    proposed_direction: str
    validation_plan: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    novelty_status: Literal["unverified", "partially_checked", "likely_saturated"] = "unverified"
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    topic: str
    generated_at: date
    domain: DomainConfig
    papers: list[Paper] = Field(default_factory=list)
    excluded_papers: list[Paper] = Field(default_factory=list)
    metrics: list[MetricResult] = Field(default_factory=list)
    methods: list[MethodRecord] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    innovations: list[InnovationCandidate] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
