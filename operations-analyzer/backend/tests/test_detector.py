import pandas as pd
import pytest
from app.data.repository import Repository
from app.data.glossary import GLOSSARY
from app.insights.detector import detect_anomalies, detect_negative_trends


def _build_repo(rows):
    metrics = pd.DataFrame(rows)
    return Repository(metrics, pd.DataFrame())


def test_anomaly_detected_when_wow_delta_exceeds_threshold():
    rows = []
    # Stable for 8 weeks, then sudden drop in L0W
    for w in range(9):
        val = 0.5 if w > 0 else 0.3  # L0W=0.3, L1W=0.5 → -40%
        rows.append({"country": "CO", "city": "X", "zone": "A",
                     "zone_type": "Wealthy", "zone_prioritization": "P",
                     "metric": "Lead Penetration", "week_offset": w, "value": val})
    repo = _build_repo(rows)
    findings = detect_anomalies(repo, GLOSSARY)
    assert any(f.category == "anomaly" and f.zone["zone"] == "A" for f in findings)


def test_anomaly_not_detected_when_change_is_small():
    rows = []
    for w in range(9):
        val = 0.50 if w > 0 else 0.51
        rows.append({"country": "CO", "city": "X", "zone": "B",
                     "zone_type": "Wealthy", "zone_prioritization": "P",
                     "metric": "Lead Penetration", "week_offset": w, "value": val})
    repo = _build_repo(rows)
    findings = detect_anomalies(repo, GLOSSARY)
    assert not any(f.zone["zone"] == "B" for f in findings)


def test_negative_trend_detected_with_3_consecutive_deteriorations():
    rows = []
    # Lead Penetration (higher is better) deteriorating last 4 weeks
    values_by_offset = {8: 0.7, 7: 0.7, 6: 0.7, 5: 0.7, 4: 0.7,
                        3: 0.65, 2: 0.6, 1: 0.55, 0: 0.5}
    for w, v in values_by_offset.items():
        rows.append({"country": "CO", "city": "X", "zone": "C",
                     "zone_type": "Wealthy", "zone_prioritization": "P",
                     "metric": "Lead Penetration", "week_offset": w, "value": v})
    repo = _build_repo(rows)
    findings = detect_negative_trends(repo, GLOSSARY)
    assert any(f.zone["zone"] == "C" and f.category == "trend" for f in findings)
