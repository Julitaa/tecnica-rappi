import pandas as pd
from pathlib import Path
from app.data.loader import load_data, pivot_wide_to_long


def test_pivot_wide_to_long():
    wide = pd.DataFrame([{
        "COUNTRY": "CO", "CITY": "Bogota", "ZONE": "Chapinero",
        "ZONE_TYPE": "Wealthy", "ZONE_PRIORITIZATION": "High Priority",
        "METRIC": "Lead Penetration",
        "L8W_VALUE": 0.1, "L7W_VALUE": 0.2, "L6W_VALUE": 0.3,
        "L5W_VALUE": 0.4, "L4W_VALUE": 0.5, "L3W_VALUE": 0.6,
        "L2W_VALUE": 0.7, "L1W_VALUE": 0.8, "L0W_VALUE": 0.9,
    }])
    long = pivot_wide_to_long(wide)
    assert len(long) == 9
    assert set(long["week_offset"]) == set(range(9))
    row_l0w = long[long["week_offset"] == 0].iloc[0]
    assert row_l0w["value"] == 0.9
    row_l8w = long[long["week_offset"] == 8].iloc[0]
    assert row_l8w["value"] == 0.1


def test_load_data_returns_two_dataframes(tmp_path):
    metrics_wide = pd.DataFrame([{
        "COUNTRY": "CO", "CITY": "Bogota", "ZONE": "Chapinero",
        "ZONE_TYPE": "Wealthy", "ZONE_PRIORITIZATION": "High Priority",
        "METRIC": "Lead Penetration",
        **{f"L{i}W_VALUE": 0.5 for i in range(9)},
    }])
    orders_wide = pd.DataFrame([{
        "COUNTRY": "CO", "CITY": "Bogota", "ZONE": "Chapinero",
        "METRIC": "Orders",
        **{f"L{i}W": 1000 for i in range(9)},
    }])
    xlsx_path = tmp_path / "fixture.xlsx"
    with pd.ExcelWriter(xlsx_path) as w:
        metrics_wide.to_excel(w, sheet_name="RAW_INPUT_METRICS", index=False)
        orders_wide.to_excel(w, sheet_name="RAW_ORDERS", index=False)
    cache_path = tmp_path / "cache.parquet"
    metrics_df, orders_df = load_data(xlsx_path, cache_path)
    assert len(metrics_df) == 9
    assert len(orders_df) == 9
    assert "week_offset" in metrics_df.columns
    assert "value" in metrics_df.columns
