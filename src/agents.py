from __future__ import annotations

import json
import re
from typing import Any, Type, TypeVar

from groq import Groq
from pydantic import BaseModel, ValidationError

from src.schemas import AdInsights, PageAudit, PageSnapshot, PersonalizationPlan

ModelType = TypeVar("ModelType", bound=BaseModel)


class GroqPersonalizationEngine:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = Groq(api_key=api_key)
        self.model = model

    def _extract_json(self, raw_text: str) -> dict[str, Any]:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("Model did not return valid JSON.")

        return json.loads(match.group(0))

    def _call_json(self, system_prompt: str, user_prompt: str, schema: Type[ModelType]) -> ModelType:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        payload = self._extract_json(raw)

        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Model output failed schema validation: {exc}") from exc

    def analyze_ad(self, ad_text: str, ad_link: str = "") -> AdInsights:
        system = (
            "You are Ad Insight Agent. Extract audience and offer intent from ad context. "
            "Return JSON only with this schema: "
            "{audience:string,pain_points:string[],value_proposition:string,tone:string,"
            "primary_offer:string,key_promises:string[]}."
        )
        user = f"Ad Text:\n{ad_text}\n\nAd Creative Link (optional):\n{ad_link}"
        return self._call_json(system, user, AdInsights)

    def audit_page(self, snapshot: PageSnapshot) -> PageAudit:
        system = (
            "You are Landing Page Audit Agent. Analyze current conversion strengths and gaps. "
            "Keep scope to editable copy only. Return JSON only with this schema: "
            "{current_headline:string,current_cta:string,top_benefits_present:string[],"
            "conversion_gaps:string[],editable_blocks:string[]}."
        )
        sections_preview = "\n".join(
            [f"- {section.heading}: {section.body[:220]}" for section in snapshot.sections[:8]]
        )
        user = (
            f"Page Title: {snapshot.title}\n"
            f"Current Hero Headline: {snapshot.hero_headline}\n"
            f"Current Primary CTA: {snapshot.primary_cta}\n"
            f"Sections:\n{sections_preview}"
        )
        return self._call_json(system, user, PageAudit)

    def personalize(
        self,
        ad_insights: AdInsights,
        page_audit: PageAudit,
        snapshot: PageSnapshot,
    ) -> PersonalizationPlan:
        system = (
            "You are Personalization Agent for CRO. Important rules: "
            "1) Keep existing page structure. 2) Do not create a new page. "
            "3) Edit only conversion copy blocks like hero, cta, bullets, trust text. "
            "4) Do not invent unsupported claims. "
            "Return JSON only with this schema: "
            "{personalized_headline:string,personalized_subheadline:string,"
            "personalized_cta:string,personalized_bullets:string[],trust_snippet:string,"
            "change_rationale:string[]}."
        )

        user = (
            "Ad Insights:\n"
            f"{ad_insights.model_dump_json(indent=2)}\n\n"
            "Page Audit:\n"
            f"{page_audit.model_dump_json(indent=2)}\n\n"
            "Existing Page Context:\n"
            f"Title: {snapshot.title}\n"
            f"Hero: {snapshot.hero_headline}\n"
            f"CTA: {snapshot.primary_cta}\n"
            "Instruction: produce enhanced copy for higher message-match and conversion."
        )

        return self._call_json(system, user, PersonalizationPlan)
