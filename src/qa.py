from __future__ import annotations

import re

from src.schemas import PersonalizationPlan, QAReport


SUSPICIOUS_PATTERNS = [
    r"\bguaranteed\b",
    r"\b#1\b",
    r"\b100%\b",
    r"\bno risk\b",
]


def validate_personalization(plan: PersonalizationPlan, source_text: str) -> QAReport:
    issues = []
    warnings = []

    if not plan.personalized_headline.strip():
        issues.append("Missing personalized headline.")
    if not plan.personalized_cta.strip():
        issues.append("Missing personalized CTA.")

    if len(plan.personalized_bullets) < 3:
        warnings.append("Recommended at least 3 benefit bullets for stronger CRO clarity.")

    generated_text = " ".join(
        [
            plan.personalized_headline,
            plan.personalized_subheadline,
            plan.personalized_cta,
            plan.trust_snippet,
            " ".join(plan.personalized_bullets),
        ]
    ).lower()

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, generated_text) and not re.search(pattern, source_text.lower()):
            warnings.append(
                f"Potential unsupported claim detected: pattern '{pattern}'."
            )

    return QAReport(passed=len(issues) == 0, issues=issues, warnings=warnings)
