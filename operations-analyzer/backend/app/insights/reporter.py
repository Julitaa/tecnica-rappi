"""Build the executive report: detection → ranking → LLM narrative → markdown."""
from __future__ import annotations
import json
import logging
from app.data.repository import Repository
from app.data.glossary import GLOSSARY, glossary_for_prompt
from app.insights.detector import (
    detect_anomalies, detect_negative_trends,
    detect_benchmark_divergence, detect_correlations, detect_opportunities,
)
from app.insights.ranker import rank_and_select
from app.insights.prompts import REPORTER_SYSTEM
from app.llm.client import get_llm

log = logging.getLogger(__name__)


def collect_findings(repo: Repository) -> list[dict]:
    findings = []
    findings += detect_anomalies(repo, GLOSSARY)
    findings += detect_negative_trends(repo, GLOSSARY)
    findings += detect_benchmark_divergence(repo, GLOSSARY)
    findings += detect_correlations(repo, GLOSSARY)
    findings += detect_opportunities(repo, GLOSSARY)
    log.info("Collected %d raw findings", len(findings))
    top = rank_and_select(findings)
    log.info("Selected %d findings after ranking", len(top))
    return [f.to_dict() for f in top]


async def generate_markdown_report(repo: Repository) -> str:
    findings = collect_findings(repo)
    llm = get_llm()
    user_payload = {
        "findings": findings,
        "glossary": glossary_for_prompt(),
    }
    messages = [
        {"role": "system", "content": REPORTER_SYSTEM},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]
    resp = await llm.chat(messages)
    return resp.choices[0].message.content or ""
