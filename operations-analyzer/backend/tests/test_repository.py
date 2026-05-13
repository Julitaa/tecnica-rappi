import pandas as pd
import pytest
from app.data.repository import Repository

@pytest.fixture
def repo():
    metrics = pd.DataFrame([
        {"country": "CO", "city": "Bogota", "zone": "Chapinero",
         "zone_type": "Wealthy", "zone_prioritization": "High Priority",
         "metric": "Lead Penetration", "week_offset": w, "value": 0.5 + (8 - w) * 0.01}
        for w in range(9)
    ] + [
        {"country": "MX", "city": "CDMX", "zone": "Roma",
         "zone_type": "Wealthy", "zone_prioritization": "Prioritized",
         "metric": "Lead Penetration", "week_offset": w, "value": 0.7}
        for w in range(9)
    ])
    orders = pd.DataFrame([
        {"country": "CO", "city": "Bogota", "zone": "Chapinero",
         "metric": "Orders", "week_offset": w, "value": 1000 + w*10}
        for w in range(9)
    ])
    return Repository(metrics, orders)

def test_list_countries(repo):
    assert set(repo.list_countries()) == {"CO", "MX"}

def test_list_zones_filtered(repo):
    zones = repo.list_zones(country="CO")
    assert zones == ["Chapinero"]

def test_get_metric_series(repo):
    series = repo.get_metric_series("CO", "Chapinero", "Lead Penetration")
    assert len(series) == 9
    assert series[0] == pytest.approx(0.50)   # L8W (oldest)
    assert series[-1] == pytest.approx(0.58)  # L0W (latest)

def test_get_metric_series_unknown_returns_empty(repo):
    assert repo.get_metric_series("XX", "Nowhere", "Lead Penetration") == []

def test_combined_view_joins_zone_metadata_to_orders(repo):
    view = repo.combined_view()
    chap = view[(view["zone"] == "Chapinero") & (view["metric"] == "Orders")]
    assert (chap["zone_type"] == "Wealthy").all()
