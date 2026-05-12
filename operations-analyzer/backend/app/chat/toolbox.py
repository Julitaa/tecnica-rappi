"""Toolbox of analysis functions callable by the LLM."""
from __future__ import annotations
from typing import Any
import pandas as pd
from app.data.repository import Repository


class Toolbox:
    def __init__(self, repo: Repository):
        self.repo = repo

    # ---- Tool 1: top_n_zones ----------------------------------------
    def top_n_zones(self, metric: str, n: int = 5, week_offset: int = 0,
                    filters: dict | None = None, order: str = "desc") -> dict:
        df = self._metrics_slice(metric, week_offset, filters)
        ascending = (order == "asc")
        df = df.sort_values("value", ascending=ascending).head(n)
        data = df[["country", "city", "zone", "zone_type", "value"]].to_dict("records")
        summary = (f"Top {n} zonas por {metric} (semana L{week_offset}W, orden={order}). "
                   f"{len(data)} resultados.")
        return {"data": data, "summary": summary, "metadata": {"metric": metric}}

    # ---- Tool 2: compare_segments -----------------------------------
    def compare_segments(self, metric: str, group_by: str,
                         filters: dict | None = None,
                         week_offset: int = 0) -> dict:
        df = self._metrics_slice(metric, week_offset, filters)
        if group_by not in df.columns:
            return {"data": [], "summary": f"Columna {group_by} no existe.",
                    "metadata": {}}
        grouped = (df.groupby(group_by)["value"]
                     .agg(["mean", "median", "std", "count"])
                     .reset_index())
        data = grouped.to_dict("records")
        summary = f"Comparación de {metric} agrupado por {group_by}: {len(data)} segmentos."
        return {"data": data, "summary": summary, "metadata": {"metric": metric}}

    # ---- Tool 3: metric_trend ---------------------------------------
    def metric_trend(self, metric: str, country: str, zone: str,
                     weeks: int = 9) -> dict:
        df = self.repo.metrics
        df = df[(df["metric"] == metric)
                & (df["country"] == country)
                & (df["zone"] == zone)]
        df = df.sort_values("week_offset", ascending=False).head(weeks)
        data = df[["week_offset", "value"]].to_dict("records")
        if not data:
            return {"data": [], "summary": f"Sin datos para {zone}/{metric}.",
                    "metadata": {}}
        delta = data[-1]["value"] - data[0]["value"]
        summary = (f"Evolución de {metric} en {zone} ({country}), "
                   f"últimas {len(data)} semanas. Δ total: {delta:+.4f}.")
        return {"data": data, "summary": summary, "metadata": {"metric": metric}}

    # ---- Tool 4: aggregate ------------------------------------------
    def aggregate(self, metric: str, group_by: str, agg: str = "mean",
                  filters: dict | None = None, week_offset: int = 0) -> dict:
        df = self._metrics_slice(metric, week_offset, filters)
        if group_by not in df.columns:
            return {"data": [], "summary": f"Columna {group_by} no existe.",
                    "metadata": {}}
        valid_aggs = {"mean", "median", "sum", "min", "max", "std"}
        if agg not in valid_aggs:
            agg = "mean"
        grouped = df.groupby(group_by)["value"].agg(agg).reset_index()
        data = grouped.to_dict("records")
        summary = f"{agg.capitalize()} de {metric} por {group_by}: {len(data)} grupos."
        return {"data": data, "summary": summary,
                "metadata": {"metric": metric, "agg": agg}}

    # ---- Tool 5: multivariable_filter -------------------------------
    def multivariable_filter(self, conditions: list[dict],
                             week_offset: int = 0) -> dict:
        """conditions = [{metric, op, value}], op in {>, <, >=, <=, ==}."""
        repo_metrics = self.repo.metrics
        zones = None
        for cond in conditions:
            df = repo_metrics[(repo_metrics["metric"] == cond["metric"])
                              & (repo_metrics["week_offset"] == week_offset)]
            op = cond["op"]
            v = cond["value"]
            if op == ">":    match = df[df["value"] > v]
            elif op == "<":  match = df[df["value"] < v]
            elif op == ">=": match = df[df["value"] >= v]
            elif op == "<=": match = df[df["value"] <= v]
            elif op == "==": match = df[df["value"] == v]
            else:            match = df.iloc[0:0]
            keys = set(zip(match["country"], match["zone"]))
            zones = keys if zones is None else zones & keys
        zones = zones or set()
        data = [{"country": c, "zone": z} for c, z in sorted(zones)]
        summary = f"{len(data)} zonas cumplen las {len(conditions)} condiciones."
        return {"data": data, "summary": summary,
                "metadata": {"conditions": conditions}}

    # ---- Tool 6: correlate_metrics ----------------------------------
    def correlate_metrics(self, metric_a: str, metric_b: str,
                          scope: dict | None = None,
                          week_offset: int = 0) -> dict:
        df = self.repo.metrics
        df = df[df["week_offset"] == week_offset]
        for k, v in (scope or {}).items():
            if k in df.columns:
                df = df[df[k] == v]
        pivot = df.pivot_table(index=["country", "zone"],
                                columns="metric", values="value",
                                aggfunc="first")
        if metric_a not in pivot.columns or metric_b not in pivot.columns:
            return {"data": {"correlation": None, "n": 0},
                    "summary": "Métricas no disponibles en el panel.",
                    "metadata": {}}
        pair = pivot[[metric_a, metric_b]].dropna()
        if len(pair) < 3:
            return {"data": {"correlation": None, "n": len(pair)},
                    "summary": "Datos insuficientes.", "metadata": {}}
        r = pair[metric_a].corr(pair[metric_b])
        summary = (f"Correlación Pearson entre {metric_a} y {metric_b}: "
                   f"r={r:+.3f} (n={len(pair)} zonas).")
        return {"data": {"correlation": float(r), "n": int(len(pair))},
                "summary": summary,
                "metadata": {"metric_a": metric_a, "metric_b": metric_b}}

    # ---- Tool 7: growth_explainer -----------------------------------
    def growth_explainer(self, metric: str = "Orders", weeks: int = 5,
                         top_n: int = 10) -> dict:
        """Find top-growing zones in `metric` over `weeks` and compare
        their other metrics vs the average to hypothesize causes."""
        src = self.repo.orders if metric == "Orders" else self.repo.metrics
        df = src[src["metric"] == metric]
        df = df[df["week_offset"] < weeks]
        pivot = df.pivot_table(index=["country", "zone"],
                               columns="week_offset", values="value")
        if pivot.empty:
            return {"data": {"top_growth": [], "correlated_metrics": []},
                    "summary": "Sin datos.", "metadata": {}}
        latest = pivot[0] if 0 in pivot.columns else None
        oldest_col = max(c for c in pivot.columns if c < weeks)
        oldest = pivot[oldest_col]
        growth = ((latest - oldest) / oldest.replace(0, 1)).fillna(0)
        top = growth.sort_values(ascending=False).head(top_n)
        top_records = [
            {"country": idx[0], "zone": idx[1],
             "growth_pct": float(top.loc[idx])}
            for idx in top.index
        ]
        top_zones_set = set(top.index)
        all_metrics = self.repo.metrics
        l0w = all_metrics[all_metrics["week_offset"] == 0]
        deltas = []
        for m, sub in l0w.groupby("metric"):
            sub = sub.set_index(["country", "zone"])["value"]
            in_top = sub.loc[sub.index.intersection(top_zones_set)].mean()
            in_rest = sub.loc[~sub.index.isin(top_zones_set)].mean()
            if pd.notna(in_top) and pd.notna(in_rest) and in_rest != 0:
                deltas.append({"metric": m,
                               "top_mean": float(in_top),
                               "rest_mean": float(in_rest),
                               "lift_pct": float((in_top - in_rest) / abs(in_rest))})
        deltas.sort(key=lambda d: abs(d["lift_pct"]), reverse=True)
        summary = (f"Top {top_n} zonas en crecimiento de {metric} "
                   f"sobre {weeks} semanas. Sus métricas se comparan al resto "
                   f"para sugerir hipótesis de causa.")
        return {"data": {"top_growth": top_records,
                          "correlated_metrics": deltas[:5]},
                "summary": summary,
                "metadata": {"metric": metric, "weeks": weeks}}

    def _metrics_slice(self, metric: str, week_offset: int = 0,
                       filters: dict | None = None) -> pd.DataFrame:
        df = self.repo.metrics
        df = df[(df["metric"] == metric) & (df["week_offset"] == week_offset)]
        for k, v in (filters or {}).items():
            if k in df.columns:
                df = df[df[k] == v]
        return df
