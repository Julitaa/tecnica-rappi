"""Fusiona scrapes.csv del tramo 5 (McDonald's exitoso) con la corrida actual.

Race condition: en tramo 7 (este script) Uber Eats empezó a detectar bots y
McDonald's está sesgado por horario desayuno (~7-11 AM CST). La data buena
para McDonald's está en el commit 66573dd (anteayer ~21:58 CST). Fusionamos:

  - McDonald's (rappi + ubereats + didi): de 66573dd con brand_id="mcdonalds"
  - OXXO (rappi + ubereats): de la corrida actual con brand_id="oxxo"

Ambos snapshots respetan el mismo schema (excepto brand_id que ahora es
columna obligatoria). El resultado se escribe a data/scrapes.{csv,json}.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OLD = Path(r"C:\Users\julib\AppData\Local\Temp\old-scrapes.csv")
CUR = ROOT / "data" / "scrapes.csv"
OUT_CSV = ROOT / "data" / "scrapes.csv"
OUT_JSON = ROOT / "data" / "scrapes.json"


def main() -> None:
    old = pd.read_csv(OLD)
    cur = pd.read_csv(CUR)

    # OLD no tiene brand_id (era pre-Brand). Asignar mcdonalds a todas las filas
    # porque ese snapshot solo cubrió fast_food.
    if "brand_id" not in old.columns:
        old["brand_id"] = "mcdonalds"

    # OXXO de la corrida actual: solo retail (coca, agua).
    retail_skus = {"cocacola_500ml", "agua_1l"}
    oxxo = cur[
        (cur["brand_id"] == "oxxo") & (cur["product_sku"].isin(retail_skus))
    ].copy()

    # McDonald's del snapshot viejo: solo fast food (big_mac, combo, nuggets).
    fast_skus = {"big_mac", "mcombo_bigmac_med", "mcnuggets_10"}
    mcd = old[old["product_sku"].isin(fast_skus)].copy()

    merged = pd.concat([mcd, oxxo], ignore_index=True)
    # Re-ordenar columnas según el schema actual
    cols = list(cur.columns)
    merged = merged.reindex(columns=cols)

    merged.to_csv(OUT_CSV, index=False)
    merged.to_json(OUT_JSON, orient="records", indent=2, force_ascii=False)

    print(f"merged: {len(merged)} filas · {int(merged['available'].sum())} disponibles")
    print(
        merged.groupby(["platform", "brand_id", "product_sku"])["available"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "avail", "count": "total"})
        .to_string()
    )


if __name__ == "__main__":
    main()
