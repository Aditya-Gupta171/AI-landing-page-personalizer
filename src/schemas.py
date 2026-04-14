from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class AdInsights(BaseModel):
    audience: str = Field(default="")
    pain_points: List[str] = Field(default_factory=list)
    value_proposition: str = Field(default="")
    tone: str = Field(default="")
    primary_offer: str = Field(default="")
    key_promises: List[str] = Field(default_factory=list)


class PageSection(BaseModel):
    heading: str = Field(default="")
    body: str = Field(default="")


class PageSnapshot(BaseModel):
    url: str
    title: str = Field(default="")
    hero_headline: str = Field(default="")
    primary_cta: str = Field(default="")
    sections: List[PageSection] = Field(default_factory=list)
    raw_text: str = Field(default="")


class PageAudit(BaseModel):
    current_headline: str = Field(default="")
    current_cta: str = Field(default="")
    top_benefits_present: List[str] = Field(default_factory=list)
    conversion_gaps: List[str] = Field(default_factory=list)
    editable_blocks: List[str] = Field(default_factory=list)


class PersonalizationPlan(BaseModel):
    personalized_headline: str = Field(default="")
    personalized_subheadline: str = Field(default="")
    personalized_cta: str = Field(default="")
    personalized_bullets: List[str] = Field(default_factory=list)
    trust_snippet: str = Field(default="")
    change_rationale: List[str] = Field(default_factory=list)


class QAReport(BaseModel):
    passed: bool = True
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
