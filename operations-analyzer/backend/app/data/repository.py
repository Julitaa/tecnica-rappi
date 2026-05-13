"""Typed facade over the two pandas DataFrames."""
from __future__ import annotations
import pandas as pd


class Repository:
    def __init__(self, metrics_df: pd.DataFrame, orders_df: pd.DataFrame):
        self._metrics = metrics_df
        self._orders = orders_df

    @property
    def metrics(self) -> pd.DataFrame:
        return self._metrics

    @property
    def orders(self) -> pd.DataFrame:
        return self._orders

    def list_countries(self) -> list[str]:
        return sorted(self._metrics["country"].unique().tolist())

    def list_zones(self, country: str | None = None,
                   zone_type: str | None = None) -> list[str]:
        df = self._metrics
        if country:
            df = df[df["country"] == country]
        if zone_type:
            df = df[df["zone_type"] == zone_type]
        return sorted(df["zone"].unique().tolist())

    def list_metrics(self) -> list[str]:
        return sorted(self._metrics["metric"].unique().tolist())

    def get_metric_series(self, country: str, zone: str, metric: str) -> list[float]:
        """Return list of 9 values ordered from L8W (oldest, week_offset=8)
        to L0W (latest, week_offset=0)."""
        df = self._metrics[
            (self._metrics["country"] == country)
            & (self._metrics["zone"] == zone)
            & (self._metrics["metric"] == metric)
        ].sort_values("week_offset", ascending=False)
        return df["value"].tolist()

    def combined_view(self) -> pd.DataFrame:
        """Orders joined with zone metadata from metrics."""
        zone_meta = (
            self._metrics[["country", "city", "zone",
                           "zone_type", "zone_prioritization"]]
            .drop_duplicates()
        )
        return self._orders.merge(
            zone_meta, on=["country", "city", "zone"], how="left",
        )
