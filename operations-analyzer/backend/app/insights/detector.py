"""Insight detectors: pure pandas, no LLM."""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from app.data.repository import Repository
from app.insights.models import Finding
from app.insights import config

log = logging.getLogger(__name__)


def _direction(glossary: dict, metric: str) -> bool:
    return glossary.get(metric, {}).get("higher_is_better", True)


def detect_anomalies(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    pivot = df.pivot_table(
        index=["country", "city", "zone", "zone_type", "zone_prioritization", "metric"],
        columns="week_offset", values="value",
    )
    for idx, row in pivot.iterrows():
        l0w = row.get(0)
        l1w = row.get(1)
        if pd.isna(l0w) or pd.isna(l1w) or l1w == 0:
            continue
        pct = (l0w - l1w) / abs(l1w)
        if abs(pct) < config.ANOMALY_PCT_CHANGE:
            continue
        history = row.dropna().values
        std = history.std() if len(history) > 1 else 0.0
        sev = float(min(1.0, abs(l0w - l1w) / (std + 1e-9)))
        country, city, zone, ztype, zprior, metric = idx
        improved = (pct > 0) == _direction(glossary, metric)
        direction_word = "mejora" if improved else "deterioro"
        findings.append(Finding(
            category="anomaly",
            severity=sev if not improved else sev * 0.5,
            metric=metric,
            headline=f"{zone} ({country}) muestra {direction_word} de {pct:+.1%} en {metric} (L0W vs L1W).",
            zone={"country": country, "city": city, "zone": zone,
                  "zone_type": ztype, "zone_prioritization": zprior},
            evidence={"l0w": float(l0w), "l1w": float(l1w),
                      "pct_change": float(pct), "improved": improved},
        ))
    return findings


def detect_negative_trends(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    pivot = df.pivot_table(
        index=["country", "city", "zone", "zone_type", "zone_prioritization", "metric"],
        columns="week_offset", values="value",
    )
    for idx, row in pivot.iterrows():
        country, city, zone, ztype, zprior, metric = idx
        higher_better = _direction(glossary, metric)
        offsets = sorted([c for c in row.index if not pd.isna(row[c])])
        if 0 not in offsets:
            continue
        streak = 0
        prev = row[0]
        for off in range(1, max(offsets) + 1):
            if pd.isna(row.get(off)):
                break
            cur = row[off]
            deteriorated = (prev < cur) if higher_better else (prev > cur)
            if deteriorated:
                streak += 1
                prev = cur
            else:
                break
        if streak >= config.TREND_MIN_STREAK:
            l0w = row[0]
            ref = row[streak] if streak in row.index else row[offsets[-1]]
            total_change = (l0w - ref) / abs(ref) if ref else 0.0
            sev = float(min(1.0, abs(total_change) * 2))
            findings.append(Finding(
                category="trend",
                severity=sev,
                metric=metric,
                headline=f"{zone} ({country}) lleva {streak} semanas de deterioro consecutivo en {metric} ({total_change:+.1%}).",
                zone={"country": country, "city": city, "zone": zone,
                      "zone_type": ztype, "zone_prioritization": zprior},
                evidence={"streak_weeks": streak, "l0w": float(l0w),
                          "ref_value": float(ref),
                          "total_change_pct": float(total_change)},
            ))
    return findings


def detect_benchmark_divergence(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    df = df[df["week_offset"] == 0]
    for (country, ztype, metric), grp in df.groupby(
        ["country", "zone_type", "metric"]
    ):
        if len(grp) < 5:
            continue
        p_low = np.percentile(grp["value"], config.BENCHMARK_LOW_PCT)
        p_high = np.percentile(grp["value"], config.BENCHMARK_HIGH_PCT)
        median = grp["value"].median()
        higher_better = _direction(glossary, metric)
        for _, row in grp.iterrows():
            v = row["value"]
            distance = abs(v - median) / (abs(median) + 1e-9)
            if v <= p_low:
                is_bad = higher_better
                label = "bajo p10" if higher_better else "alto p90 (mejor)"
                findings.append(Finding(
                    category="benchmark",
                    severity=float(min(1.0, distance)),
                    metric=metric,
                    headline=(f"{row['zone']} ({country}, {ztype}) está "
                              f"{'rezagada' if is_bad else 'sobresaliente'} "
                              f"en {metric}: {v:.3f} vs mediano {median:.3f} del grupo."),
                    zone={"country": country, "city": row["city"], "zone": row["zone"],
                          "zone_type": ztype,
                          "zone_prioritization": row["zone_prioritization"]},
                    evidence={"value": float(v), "p10": float(p_low),
                              "p90": float(p_high), "median": float(median),
                              "label": label},
                ))
            elif v >= p_high:
                is_bad = not higher_better
                label = "alto p90" if higher_better else "bajo p10 (mejor)"
                findings.append(Finding(
                    category="benchmark",
                    severity=float(min(1.0, distance)),
                    metric=metric,
                    headline=(f"{row['zone']} ({country}, {ztype}) destaca "
                              f"{'positivamente' if not is_bad else 'negativamente'} "
                              f"en {metric}: {v:.3f} vs mediano {median:.3f}."),
                    zone={"country": country, "city": row["city"], "zone": row["zone"],
                          "zone_type": ztype,
                          "zone_prioritization": row["zone_prioritization"]},
                    evidence={"value": float(v), "p10": float(p_low),
                              "p90": float(p_high), "median": float(median),
                              "label": label},
                ))
    return findings


def detect_correlations(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    df = df[df["week_offset"] == 0]
    pivot = df.pivot_table(index=["country", "zone"], columns="metric", values="value")
    metrics = list(pivot.columns)
    seen = set()
    for i, m_a in enumerate(metrics):
        for m_b in metrics[i+1:]:
            pair = pivot[[m_a, m_b]].dropna()
            if len(pair) < config.CORRELATION_MIN_N:
                continue
            r = pair[m_a].corr(pair[m_b])
            if pd.isna(r) or abs(r) < config.CORRELATION_MIN_ABS_R:
                continue
            key = tuple(sorted([m_a, m_b]))
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                category="correlation",
                severity=float(min(1.0, abs(r))),
                metric=f"{m_a} vs {m_b}",
                headline=(f"Correlación {'positiva' if r > 0 else 'negativa'} "
                          f"fuerte entre {m_a} y {m_b}: r={r:+.2f} "
                          f"(n={len(pair)} zonas)."),
                zone={},
                evidence={"metric_a": m_a, "metric_b": m_b,
                          "r": float(r), "n": int(len(pair))},
            ))
    return findings


def detect_opportunities(repo: Repository, glossary: dict) -> list[Finding]:
    """Combina señales: High Priority zones bajo p25 = under-performance estratégica."""
    findings: list[Finding] = []
    df = repo.metrics
    df = df[(df["week_offset"] == 0)
            & (df["zone_prioritization"] == "High Priority")]
    for (country, ztype, metric), grp in df.groupby(
        ["country", "zone_type", "metric"]
    ):
        if len(grp) < 5:
            continue
        p25 = np.percentile(grp["value"], 25)
        higher_better = _direction(glossary, metric)
        for _, row in grp.iterrows():
            v = row["value"]
            underperforming = (v <= p25) if higher_better else (v >= np.percentile(grp["value"], 75))
            if not underperforming:
                continue
            findings.append(Finding(
                category="opportunity",
                severity=0.7,
                metric=metric,
                headline=(f"{row['zone']} ({country}) es High Priority pero "
                          f"está en el cuartil bajo de su grupo en {metric}."),
                zone={"country": country, "city": row["city"], "zone": row["zone"],
                      "zone_type": ztype, "zone_prioritization": "High Priority"},
                evidence={"value": float(v), "p25": float(p25)},
            ))
    return findings
