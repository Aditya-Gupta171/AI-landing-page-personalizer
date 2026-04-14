from __future__ import annotations

import os
from urllib.parse import quote
from html import escape

import streamlit as st
from dotenv import load_dotenv

from src.agents import GroqPersonalizationEngine
from src.fetcher import fetch_page_snapshot
from src.qa import validate_personalization

load_dotenv()


def _build_enhanced_preview_html(
        original_title: str,
        original_headline: str,
        original_cta: str,
        personalized_headline: str,
        personalized_subheadline: str,
        personalized_cta: str,
        personalized_bullets: list[str],
        trust_snippet: str,
) -> str:
        bullets_html = "".join(
                f"<li>{escape(item)}</li>" for item in personalized_bullets if item.strip()
        )

        return f"""
        <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(160deg, #f3f8ff 0%, #eefbf3 100%);
                        color: #122024;
                    }}
                    .wrap {{
                        max-width: 980px;
                        margin: 0 auto;
                        padding: 28px;
                    }}
                    .badge {{
                        display: inline-block;
                        background: #d7f8e2;
                        color: #0d5b33;
                        border: 1px solid #9adab3;
                        border-radius: 999px;
                        padding: 6px 12px;
                        font-size: 12px;
                        margin-bottom: 14px;
                        font-weight: 600;
                    }}
                    .grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 14px;
                        margin-bottom: 16px;
                    }}
                    .card {{
                        background: #ffffff;
                        border: 1px solid #dce8ea;
                        border-radius: 16px;
                        padding: 16px;
                    }}
                    .muted {{
                        color: #4a5a60;
                        font-size: 13px;
                    }}
                    h1 {{
                        margin: 8px 0 8px;
                        font-size: 30px;
                        line-height: 1.2;
                    }}
                    h2 {{
                        margin: 8px 0;
                        font-size: 20px;
                        line-height: 1.3;
                    }}
                    p {{
                        margin: 0 0 14px;
                        line-height: 1.5;
                    }}
                    .btn {{
                        display: inline-block;
                        background: #0f766e;
                        color: #ffffff;
                        border-radius: 10px;
                        text-decoration: none;
                        font-weight: 700;
                        padding: 11px 16px;
                    }}
                    ul {{
                        margin: 0;
                        padding-left: 20px;
                    }}
                    li {{
                        margin: 8px 0;
                    }}
                    .trust {{
                        margin-top: 14px;
                        border-left: 4px solid #10b981;
                        background: #ecfdf5;
                        padding: 10px 12px;
                        border-radius: 8px;
                        font-size: 14px;
                    }}
                    @media (max-width: 760px) {{
                        .grid {{
                            grid-template-columns: 1fr;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="wrap">
                    <span class="badge">Enhanced Existing Page Preview</span>
                    <h2>{escape(original_title or 'Landing Page')}</h2>
                    <div class="grid">
                        <div class="card">
                            <div class="muted">Before (Current Hero)</div>
                            <h1>{escape(original_headline)}</h1>
                            <a class="btn" href="#">{escape(original_cta)}</a>
                        </div>
                        <div class="card">
                            <div class="muted">After (Personalized Hero)</div>
                            <h1>{escape(personalized_headline)}</h1>
                            <p>{escape(personalized_subheadline)}</p>
                            <a class="btn" href="#">{escape(personalized_cta)}</a>
                        </div>
                    </div>
                    <div class="card">
                        <div class="muted">Personalized Benefits</div>
                        <ul>{bullets_html}</ul>
                        <div class="trust">{escape(trust_snippet)}</div>
                    </div>
                </div>
            </body>
        </html>
        """


st.set_page_config(page_title="Troopod AI PM Assignment", layout="wide")
st.title("Ad-to-Landing-Page Personalization MVP")
st.caption("Existing page enhancement workflow using Groq + Streamlit")

model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
api_key_input = os.getenv("GROQ_API_KEY", "")

col_left, col_right = st.columns(2)

with col_left:
    ad_text = st.text_area(
        "Ad Creative Text",
        placeholder="Paste ad copy, audience angle, offer details, and hooks...",
        height=220,
    )
    ad_link = st.text_input("Ad Creative Link (optional)")

with col_right:
    landing_url = st.text_input(
        "Landing Page URL",
        placeholder="https://example.com/landing-page",
    )

run_clicked = st.button("Generate Personalized Landing Page", type="primary")

if run_clicked:
    if not api_key_input.strip():
        st.error("Missing GROQ_API_KEY. Add it in your .env file and restart the app.")
        st.stop()
    if not landing_url.strip():
        st.error("Please provide a landing page URL.")
        st.stop()
    if not ad_text.strip():
        st.error("Please provide ad creative text.")
        st.stop()

    with st.spinner("Fetching page, running agents, and generating enhancements..."):
        try:
            snapshot = fetch_page_snapshot(landing_url)
            engine = GroqPersonalizationEngine(api_key=api_key_input, model=model_name)
            ad_insights = engine.analyze_ad(ad_text=ad_text, ad_link=ad_link)
            page_audit = engine.audit_page(snapshot=snapshot)
            plan = engine.personalize(
                ad_insights=ad_insights,
                page_audit=page_audit,
                snapshot=snapshot,
            )
            qa_report = validate_personalization(plan, snapshot.raw_text)
        except Exception as exc:
            st.exception(exc)
            st.stop()

    st.success("Personalization generated.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Original Snapshot",
            "Personalized Output",
            "Enhanced Page Preview",
            "Change Log",
            "Safety Checks",
        ]
    )

    with tab1:
        st.subheader("Current Landing Page Signals")
        st.write(f"**URL:** {snapshot.url}")
        st.write(f"**Title:** {snapshot.title}")
        st.write(f"**Hero Headline:** {snapshot.hero_headline}")
        st.write(f"**Primary CTA:** {snapshot.primary_cta}")
        st.markdown("### Extracted Sections")
        for section in snapshot.sections[:8]:
            with st.expander(section.heading or "Section"):
                st.write(section.body or "(No body extracted)")

    with tab2:
        st.subheader("Enhanced Existing Page Copy")
        st.write("This is a scoped enhancement of current conversion blocks, not a net-new page.")

        st.markdown("### Hero")
        st.markdown(f"**Headline:** {plan.personalized_headline}")
        st.markdown(f"**Subheadline:** {plan.personalized_subheadline}")

        st.markdown("### CTA")
        st.markdown(f"**Primary CTA:** {plan.personalized_cta}")

        st.markdown("### Benefit Bullets")
        for bullet in plan.personalized_bullets:
            st.write(f"- {bullet}")

        st.markdown("### Trust Snippet")
        st.write(plan.trust_snippet)

    with tab3:
        st.subheader("Visual Personalized Page")
        st.write("Rendered preview to demonstrate existing-page enhancement visually.")

        preview_html = _build_enhanced_preview_html(
            original_title=snapshot.title,
            original_headline=snapshot.hero_headline,
            original_cta=snapshot.primary_cta,
            personalized_headline=plan.personalized_headline,
            personalized_subheadline=plan.personalized_subheadline,
            personalized_cta=plan.personalized_cta,
            personalized_bullets=plan.personalized_bullets,
            trust_snippet=plan.trust_snippet,
        )
        preview_data_url = "data:text/html;charset=utf-8," + quote(preview_html)
        st.iframe(preview_data_url, height=780)

    with tab4:
        st.subheader("Why These Changes")
        st.markdown("#### Ad Insights")
        st.json(ad_insights.model_dump())

        st.markdown("#### Page Audit")
        st.json(page_audit.model_dump())

        st.markdown("#### Change Rationale (CRO)")
        for item in plan.change_rationale:
            st.write(f"- {item}")

    with tab5:
        st.subheader("Guardrails")
        st.write(f"**Passed:** {qa_report.passed}")

        st.markdown("#### Issues")
        if qa_report.issues:
            for issue in qa_report.issues:
                st.error(issue)
        else:
            st.write("No blocking issues found.")

        st.markdown("#### Warnings")
        if qa_report.warnings:
            for warning in qa_report.warnings:
                st.warning(warning)
        else:
            st.write("No warnings.")

st.markdown("---")
st.caption(
    "Assignment note: output is an enhancement of the existing page's conversion-critical copy "
    "to maintain structure while improving message match with ad creative."
)
