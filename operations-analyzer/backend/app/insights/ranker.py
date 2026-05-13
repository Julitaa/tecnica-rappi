"""Rank, dedup, and limit findings."""
from collections import defaultdict
from app.insights.models import Finding
from app.insights import config


def rank_and_select(findings: list[Finding]) -> list[Finding]:
    # Sort by severity desc
    findings = sorted(findings, key=lambda f: f.severity, reverse=True)
    # Dedup: per (zone-key, metric), keep highest severity
    seen: dict[tuple, Finding] = {}
    for f in findings:
        zk = (f.zone.get("country", ""), f.zone.get("zone", ""), f.metric)
        if zk not in seen or seen[zk].severity < f.severity:
            seen[zk] = f
    deduped = sorted(seen.values(), key=lambda f: f.severity, reverse=True)
    # Cap per category
    counts: dict[str, int] = defaultdict(int)
    out: list[Finding] = []
    for f in deduped:
        if counts[f.category] >= config.PER_CATEGORY_CAP:
            continue
        out.append(f)
        counts[f.category] += 1
        if len(out) >= config.TOP_K_TOTAL:
            break
    return out
