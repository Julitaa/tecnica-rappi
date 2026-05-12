import pandas as pd
import pytest
from app.data.repository import Repository
from app.chat.toolbox import Toolbox


@pytest.fixture
def repo():
    rows = []
    for country in ["CO", "MX"]:
        for zone_n in range(3):
            for w in range(9):
                rows.append({
                    "country": country,
                    "city": f"City-{country}",
                    "zone": f"{country}_zone_{zone_n}",
                    "zone_type": "Wealthy" if zone_n % 2 == 0 else "Non Wealthy",
                    "zone_prioritization": "High Priority",
                    "metric": "Lead Penetration",
                    "week_offset": w,
                    "value": 0.1 * (zone_n + 1) + 0.01 * (8 - w),
                })
    metrics = pd.DataFrame(rows)
    orders = pd.DataFrame()
    return Repository(metrics, orders)


@pytest.fixture
def toolbox(repo):
    return Toolbox(repo)


def test_top_n_zones_returns_n(toolbox):
    result = toolbox.top_n_zones(metric="Lead Penetration", n=3)
    assert len(result["data"]) == 3
    assert "summary" in result


def test_top_n_zones_orders_descending(toolbox):
    result = toolbox.top_n_zones(metric="Lead Penetration", n=5, order="desc")
    values = [row["value"] for row in result["data"]]
    assert values == sorted(values, reverse=True)


def test_top_n_zones_with_country_filter(toolbox):
    result = toolbox.top_n_zones(
        metric="Lead Penetration", n=10, filters={"country": "CO"},
    )
    countries = {row["country"] for row in result["data"]}
    assert countries == {"CO"}


def test_compare_segments(toolbox):
    result = toolbox.compare_segments(
        metric="Lead Penetration",
        group_by="zone_type",
        filters={"country": "CO"},
    )
    groups = {row["zone_type"] for row in result["data"]}
    assert groups == {"Wealthy", "Non Wealthy"}
    for row in result["data"]:
        assert "mean" in row and "count" in row


def test_metric_trend_returns_9_weeks(toolbox):
    result = toolbox.metric_trend(
        metric="Lead Penetration", country="CO", zone="CO_zone_0",
    )
    assert len(result["data"]) == 9
    offsets = [row["week_offset"] for row in result["data"]]
    # ordered oldest -> latest: week_offset 8 (L8W) -> 0 (L0W)
    assert offsets == list(range(8, -1, -1))


def test_aggregate_by_country(toolbox):
    result = toolbox.aggregate(
        metric="Lead Penetration", group_by="country", agg="mean",
    )
    countries = {row["country"] for row in result["data"]}
    assert countries == {"CO", "MX"}
