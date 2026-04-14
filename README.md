# Troopod AI PM Assignment MVP

This project demonstrates an agent-style AI workflow that personalizes an **existing landing page** based on ad creative input.

## What It Does

Inputs:

- Ad creative text (plus optional ad link)
- Landing page URL

Output:

- Personalized conversion copy for the same page structure
- Change rationale linked to CRO principles
- Guardrail checks for unsupported claims and inconsistent output

## Agent Flow

1. Ad Insight Agent

- Extracts audience, pain points, value proposition, tone, and offer from ad input.

2. Landing Page Audit Agent

- Analyzes current page messaging and conversion gaps from extracted page content.

3. Personalization Agent

- Produces scoped updates for hero copy, CTA, bullets, and trust snippet.
- Enforces rule: enhance existing page, do not generate a net-new page.

4. QA Guardrail Layer

- Checks for missing required blocks.
- Flags potentially unsupported claims.

## Setup

1. Create and activate virtual environment (already done).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browser (needed for JavaScript-rendered pages like Shopify):

```bash
python -m playwright install chromium
```

4. Configure environment:

```bash
copy .env.example .env
```

Edit `.env` and set `GROQ_API_KEY`.

By default, JavaScript rendering fallback is disabled for runtime stability.
Set `ENABLE_JS_RENDERING=true` only if your environment supports Playwright subprocess execution.
On Windows, also set `ENABLE_JS_RENDERING_UNSTABLE=true` if you want to force Playwright mode.

## Run

```bash
python -m streamlit run app.py
```

- This MVP intentionally keeps personalization scoped to CRO-critical copy blocks to preserve original page structure.
