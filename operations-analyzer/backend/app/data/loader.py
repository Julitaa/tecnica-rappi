"""Load Excel source, pivot wide->long, cache to Parquet."""
from pathlib import Path
import logging
import pandas as pd

log = logging.getLogger(__name__)

METRICS_SHEET = "RAW_INPUT_METRICS"
ORDERS_SHEET = "RAW_ORDERS"

WEEK_COLS_VALUE = [f"L{i}W_VALUE" for i in range(9)]
WEEK_COLS_ROLL = [f"L{i}W_ROLL" for i in range(9)]
WEEK_COLS_BARE = [f"L{i}W" for i in range(9)]


def _detect_week_cols(df: pd.DataFrame) -> list[str]:
    for candidate in (WEEK_COLS_VALUE, WEEK_COLS_ROLL, WEEK_COLS_BARE):
        if all(c in df.columns for c in candidate):
            return candidate
    raise ValueError(f"No week columns recognized. Got: {list(df.columns)}")


def pivot_wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    week_cols = _detect_week_cols(df)
    id_cols = [c for c in df.columns if c not in week_cols]
    long = df.melt(
        id_vars=id_cols, value_vars=week_cols,
        var_name="week_col", value_name="value",
    )
    long["week_offset"] = long["week_col"].str.extract(r"L(\d+)W").astype(int)
    long = long.drop(columns=["week_col"])
    rename_map = {
        "COUNTRY": "country", "CITY": "city", "ZONE": "zone",
        "ZONE_TYPE": "zone_type", "ZONE_PRIORITIZATION": "zone_prioritization",
        "METRIC": "metric",
    }
    long = long.rename(columns={k: v for k, v in rename_map.items() if k in long.columns})
    return long


def _validate(df: pd.DataFrame, name: str) -> None:
    nulls = df["value"].isna().sum()
    if nulls:
        log.warning("%s: %d null values", name, nulls)
    negatives = (df["value"] < 0).sum()
    if negatives:
        log.warning("%s: %d negative values", name, negatives)


def load_data(xlsx_path: Path, cache_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    xlsx_path, cache_path = Path(xlsx_path), Path(cache_path)
    metrics_cache = cache_path.with_name("metrics_" + cache_path.name)
    orders_cache = cache_path.with_name("orders_" + cache_path.name)
    if metrics_cache.exists() and orders_cache.exists():
        log.info("Loading from parquet cache")
        return pd.read_parquet(metrics_cache), pd.read_parquet(orders_cache)
    log.info("Loading from xlsx and caching")
    metrics_wide = pd.read_excel(xlsx_path, sheet_name=METRICS_SHEET)
    orders_wide = pd.read_excel(xlsx_path, sheet_name=ORDERS_SHEET)
    metrics_df = pivot_wide_to_long(metrics_wide)
    orders_df = pivot_wide_to_long(orders_wide)
    _validate(metrics_df, "metrics")
    _validate(orders_df, "orders")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_parquet(metrics_cache)
    orders_df.to_parquet(orders_cache)
    return metrics_df, orders_df
