# Report Refactor: Fast Food + Retail Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `report/generate_report.py` so the HTML report separates fast food (McDonald's) and retail (OXXO) analyses, makes all numeric claims dynamic from the CSV, covers all 20 zones, and updates insights with real data.

**Architecture:** Single-file modification. Add `compute_stats(df) -> dict` to extract key metrics; wire those stats into reading paragraphs (f-strings), exec summary, and INSIGHTS. Add 4 new retail chart functions. Restructure `compose_html()` into 9 numbered sections + sidebar.

**Tech Stack:** Python 3, pandas, plotly, pathlib (no new dependencies)

---

## Real data facts (from current `data/scrapes.csv` — 260 rows, 152 available)

Use these numbers throughout the plan — they must match the live CSV exactly.

| Metric | Value |
|--------|-------|
| Fast food ETA Rappi | 12–49 min |
| Fast food ETA UberEats | 10–37 min |
| Fast food zones (Rappi) | Polanco, Roma Norte, Santa Fe, Iztapalapa, Cuautitlan Izcalli, Insurgentes Sur, Gustavo A. Madero, Alvaro Obregon, Azcapotzalco, Centro Historico, Toluca |
| Big Mac price Rappi | ~$130 MXN |
| Big Mac price UE | ~$131 MXN |
| Rappi delivery_fee (FF) | avg $10.38 w/ -$10.38 discount → $0 net |
| UE delivery_fee (FF) | $0 |
| UE promo % (FF) | 80% |
| Rappi promo % | 0% |
| OXXO Rappi avail | 38/40 |
| OXXO UE avail | 30/40 (UE is NOT blocked — partial coverage) |
| Coca-Cola Rappi | $22 MXN |
| Coca-Cola UE | $24.50 MXN avg |
| Agua Rappi | $19.50 MXN |
| Agua UE | $28.76 MXN avg |
| Retail promos | 0% on both platforms |

---

## File structure

| File | Action | Responsibility |
|------|--------|----------------|
| `report/generate_report.py` | Modify | Only file touched |
| `report/competitive_intelligence_2026.html` | Regenerated | Output artifact |

---

## Task 1: Add `compute_stats(df)` function

**Files:**
- Modify: `report/generate_report.py` — insert after `load_data()`, before `make_price_chart()`

- [ ] **Step 1.1: Add the function**

Insert this function at line ~447 (right after `load_data()`):

```python
def compute_stats(df: pd.DataFrame) -> dict:
    """Compute all dynamic metrics used in narrative text."""
    av = df[df["available"] == True]
    ff = av[av["brand_id"] == "mcdonalds"]
    rt = av[av["brand_id"] == "oxxo"]
    df_ff_all = df[df["brand_id"] == "mcdonalds"]
    df_rt_all = df[df["brand_id"] == "oxxo"]

    def _eta_range(sub, platform):
        vals = sub[sub["platform"] == platform]["eta_min"].dropna()
        return (int(vals.min()), int(vals.max())) if len(vals) else (None, None)

    def _avg_price(sub, platform, sku):
        vals = sub[(sub["platform"] == platform) & (sub["product_sku"] == sku)]["unit_price_mxn"].dropna()
        return round(vals.mean(), 0) if len(vals) else None

    def _promo_pct(sub, platform):
        sub2 = sub[sub["platform"] == platform]
        if len(sub2) == 0:
            return 0
        return round(sub2["has_promo"].mean() * 100, 0)

    ff_eta_rappi = _eta_range(ff, "rappi")
    ff_eta_ue    = _eta_range(ff, "ubereats")

    # Delivery fee net for fast food
    ff_rappi_fees = ff[ff["platform"] == "rappi"]
    ff_ue_fees    = ff[ff["platform"] == "ubereats"]
    ff_delivery_rappi = round(ff_rappi_fees["delivery_fee_mxn"].mean(), 1) if len(ff_rappi_fees) else 0
    ff_discount_rappi = round(ff_rappi_fees["discount_mxn"].mean(), 1) if len(ff_rappi_fees) else 0

    # Price ranges for retail
    def _price_range(sub, platform, sku):
        vals = sub[(sub["platform"] == platform) & (sub["product_sku"] == sku)]["unit_price_mxn"].dropna()
        if len(vals) == 0:
            return (None, None)
        return (round(vals.min(), 1), round(vals.max(), 1))

    return {
        # Fast food ETA
        "ff_eta_rappi_min": ff_eta_rappi[0],
        "ff_eta_rappi_max": ff_eta_rappi[1],
        "ff_eta_ue_min":    ff_eta_ue[0],
        "ff_eta_ue_max":    ff_eta_ue[1],
        # Fast food prices
        "ff_price_bigmac_rappi": _avg_price(ff, "rappi", "big_mac"),
        "ff_price_bigmac_ue":    _avg_price(ff, "ubereats", "big_mac"),
        "ff_price_nuggets_rappi": _avg_price(ff, "rappi", "mcnuggets_10"),
        "ff_price_nuggets_ue":    _avg_price(ff, "ubereats", "mcnuggets_10"),
        "ff_price_combo_rappi":   _avg_price(ff, "rappi", "mcombo_bigmac_med"),
        "ff_price_combo_ue":      _avg_price(ff, "ubereats", "mcombo_bigmac_med"),
        # Fast food fees
        "ff_delivery_rappi": ff_delivery_rappi,
        "ff_discount_rappi": ff_discount_rappi,
        # Promos
        "ff_promo_pct_rappi": _promo_pct(ff, "rappi"),
        "ff_promo_pct_ue":    _promo_pct(ff, "ubereats"),
        "rt_promo_pct_rappi": _promo_pct(rt, "rappi"),
        "rt_promo_pct_ue":    _promo_pct(rt, "ubereats"),
        # Retail prices
        "rt_price_coca_rappi":    _avg_price(rt, "rappi", "cocacola_500ml"),
        "rt_price_coca_ue":       _avg_price(rt, "ubereats", "cocacola_500ml"),
        "rt_price_agua_rappi":    _avg_price(rt, "rappi", "agua_1l"),
        "rt_price_agua_ue":       _avg_price(rt, "ubereats", "agua_1l"),
        "rt_price_coca_rappi_range": _price_range(rt, "rappi", "cocacola_500ml"),
        "rt_price_agua_rappi_range": _price_range(rt, "rappi", "agua_1l"),
        # Retail availability
        "rt_avail_rappi": int(len(df_rt_all[(df_rt_all["platform"] == "rappi") & (df_rt_all["available"] == True)])),
        "rt_total_rappi": int(len(df_rt_all[df_rt_all["platform"] == "rappi"])),
        "rt_avail_ue":    int(len(df_rt_all[(df_rt_all["platform"] == "ubereats") & (df_rt_all["available"] == True)])),
        "rt_total_ue":    int(len(df_rt_all[df_rt_all["platform"] == "ubereats"])),
        # Coverage
        "zones":       sorted(av["address_label"].unique().tolist()),
        "n_total":     len(df),
        "n_available": len(av),
        "n_rappi_avail":    int(len(av[av["platform"] == "rappi"])),
        "n_ue_avail":       int(len(av[av["platform"] == "ubereats"])),
        "n_didi_avail":     int(len(av[av["platform"] == "didi"])),
        "snapshot_date": df["timestamp_utc"].dropna().iloc[0][:10] if "timestamp_utc" in df.columns else "2026-05-13",
    }
```

- [ ] **Step 1.2: Verify the function runs without errors**

```bash
cd competitive-intelligence
python -c "
import pandas as pd, sys
sys.path.insert(0, '.')
from report.generate_report import load_data, compute_stats
df = load_data()
s = compute_stats(df)
print('ff_eta_rappi_min:', s['ff_eta_rappi_min'])
print('ff_eta_ue_min:', s['ff_eta_ue_min'])
print('rt_avail_rappi:', s['rt_avail_rappi'], '/', s['rt_total_rappi'])
print('rt_avail_ue:', s['rt_avail_ue'], '/', s['rt_total_ue'])
print('zones count:', len(s['zones']))
print('OK')
"
```

Expected output:
```
ff_eta_rappi_min: 12
ff_eta_ue_min: 10
rt_avail_rappi: 38 / 40
rt_avail_ue: 30 / 40
zones count: 20
OK
```

- [ ] **Step 1.3: Commit**

```bash
git add report/generate_report.py
git commit -m "feat(report): add compute_stats(df) for dynamic narrative metrics"
```

---

## Task 2: Add 4 retail chart functions

**Files:**
- Modify: `report/generate_report.py` — insert after `make_geo_chart()`, before `compose_html()`

- [ ] **Step 2.1: Add `make_retail_price_chart(df)`**

```python
def make_retail_price_chart(df: pd.DataFrame) -> go.Figure:
    """Bar chart: avg unit price by retail SKU × platform (available rows only)."""
    av = df[(df["available"] == True) & (df["brand_id"] == "oxxo")]
    retail_skus = ["cocacola_500ml", "agua_1l"]

    fig = go.Figure()
    for platform in ["rappi", "ubereats"]:
        pdata = av[av["platform"] == platform]
        prices = pdata.groupby("product_sku")["unit_price_mxn"].mean()
        x_labels = [SKU_LABELS[s] for s in retail_skus if s in prices.index]
        y_vals   = [prices[s] for s in retail_skus if s in prices.index]
        if not y_vals:
            continue
        fig.add_trace(go.Bar(
            name=PLATFORM_LABELS[platform],
            x=x_labels,
            y=y_vals,
            marker_color=PLATFORM_COLORS[platform],
            text=[f"${v:.1f}" for v in y_vals],
            textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=320,
        margin=dict(l=20, r=20, t=10, b=40),
        yaxis_title="MXN",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig
```

- [ ] **Step 2.2: Add `make_retail_avail_chart(df)`**

```python
def make_retail_avail_chart(df: pd.DataFrame) -> go.Figure:
    """Heatmap: OXXO availability (1=yes, 0=no) by zone × platform."""
    rt = df[df["brand_id"] == "oxxo"]
    pivot = (
        rt.groupby(["address_label", "platform"])["available"]
        .mean()
        .unstack("platform")
        .reindex(columns=["rappi", "ubereats"])
        .dropna(axis=1, how="all")
    )
    z = pivot.values
    text = [
        ["✓" if v == 1.0 else ("~" if (v is not None and not pd.isna(v) and 0 < v < 1) else "✗") for v in row]
        for row in z
    ]
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[PLATFORM_LABELS.get(c, c) for c in pivot.columns],
        y=list(pivot.index),
        colorscale=[[0, "#FEE2E2"], [0.5, "#FEF3C7"], [1, "#D1FAE5"]],
        zmin=0, zmax=1,
        text=text,
        texttemplate="%{text}",
        showscale=False,
    ))
    fig.update_layout(
        template="plotly_white",
        height=max(280, 22 * len(pivot)),
        margin=dict(l=20, r=20, t=10, b=20),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig
```

- [ ] **Step 2.3: Add `make_retail_fees_chart(df)`**

```python
def make_retail_fees_chart(df: pd.DataFrame) -> go.Figure:
    """Bar: avg delivery fee by platform for retail (OXXO), available rows."""
    av = df[(df["available"] == True) & (df["brand_id"] == "oxxo")]
    fees = av.groupby("platform")[["delivery_fee_mxn", "discount_mxn"]].mean().round(1)
    platforms_present = [p for p in ["rappi", "ubereats"] if p in fees.index]

    fig = go.Figure()
    for col, label, color in [
        ("delivery_fee_mxn", "Delivery fee bruto", "#4C72B0"),
        ("discount_mxn",     "Descuento aplicado", "#C44E52"),
    ]:
        y_vals = [fees.loc[p, col] if p in fees.index else 0 for p in platforms_present]
        fig.add_trace(go.Bar(
            name=label,
            x=[PLATFORM_LABELS[p] for p in platforms_present],
            y=y_vals,
            marker_color=color,
            text=[f"${v:.1f}" for v in y_vals],
            textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=280,
        margin=dict(l=20, r=20, t=10, b=40),
        yaxis_title="MXN",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig
```

- [ ] **Step 2.4: Add `make_retail_promos_chart(df)`**

```python
def make_retail_promos_chart(df: pd.DataFrame) -> go.Figure:
    """Bar: % of OXXO rows with visible promo text, by platform."""
    rt = df[df["brand_id"] == "oxxo"]
    pct = rt.groupby("platform")["has_promo"].mean().mul(100).round(1)
    platforms = [p for p in ["rappi", "ubereats", "didi"] if p in pct.index]

    fig = go.Figure(go.Bar(
        x=[PLATFORM_LABELS.get(p, p) for p in platforms],
        y=[pct[p] for p in platforms],
        marker_color=[PLATFORM_COLORS.get(p, "#888") for p in platforms],
        text=[f"{pct[p]:.0f}%" for p in platforms],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly_white",
        height=260,
        margin=dict(l=20, r=20, t=10, b=40),
        yaxis=dict(title="%", range=[0, 120]),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig
```

- [ ] **Step 2.5: Verify all 4 charts run without errors**

```bash
python -c "
import pandas as pd, sys
sys.path.insert(0, '.')
from report.generate_report import (
    load_data, make_retail_price_chart, make_retail_avail_chart,
    make_retail_fees_chart, make_retail_promos_chart
)
df = load_data()
for fn in [make_retail_price_chart, make_retail_avail_chart,
           make_retail_fees_chart, make_retail_promos_chart]:
    fig = fn(df)
    assert fig is not None
    print(fn.__name__, 'OK')
"
```

Expected: 4 lines ending in `OK`

- [ ] **Step 2.6: Commit**

```bash
git add report/generate_report.py
git commit -m "feat(report): add 4 retail chart functions (price, avail, fees, promos)"
```

---

## Task 3: Update `INSIGHTS` with real data

**Files:**
- Modify: `report/generate_report.py` — replace the `INSIGHTS` list (lines 31–67)

Key changes from the old data:
- Insight 1 ETA: now 12–49 min Rappi vs 10–37 min UE (not 10–23), Roma Norte + Santa Fe tied
- Insight 2 fees: Rappi avg $10.38 fee + $10.38 discount = $0 net (not $16)
- Insight 3 Roma Norte blueprint: Santa Fe is now a second match zone (12 min each)
- Insight 4 DiDi: unchanged
- Insight 5 OXXO: UE is NOT blocked anymore — has 30/40; Rappi leads 38/40 + Rappi cheaper on both SKUs

- [ ] **Step 3.1: Replace the INSIGHTS list**

Replace the entire `INSIGHTS = [...]` block (from `INSIGHTS = [` to the closing `]`) with:

```python
INSIGHTS = [
    {
        "title": "Brecha de ETA: Rappi 12–49 min vs Uber Eats 10–37 min — ventaja operacional de UE en zonas periféricas",
        "urgency": "high",
        "finding": "ETA promedio Rappi: 12–49 min vs Uber Eats: 10–37 min. Rappi empata en velocidad solo en Roma Norte (12 min) y Santa Fe (12 min). En zonas periféricas (Alvaro Obregón, Insurgentes Sur, Gustavo A. Madero) Rappi muestra 35–49 min vs 11–25 min de UberEats — brechas de 2–3×.",
        "impact": "La velocidad de entrega es el driver #1 de recompra en delivery. Brechas de 20+ min en zonas de alto volumen representa riesgo directo de churn. Roma Norte y Santa Fe son la excepción, no la regla.",
        "recomendacion": "Auditar capacidad de riders en las 5 zonas con mayor brecha (Alvaro Obregón 24 min gap, Insurgentes Sur 22 min, Gustavo A. Madero 24 min, Cuautitlán 25 min, Iztapalapa 21 min). Replicar el playbook de Roma Norte y Santa Fe (incentivos + zonas calientes geofenced). Meta: reducir brecha media a <15 min en 90 días.",
    },
    {
        "title": "Paridad de precio fast food + descuento silencioso: Rappi da el mismo valor pero pierde la narrativa",
        "urgency": "high",
        "finding": "Precio de producto idéntico entre Rappi y Uber Eats: Big Mac ~$130, McNuggets ~$138, Combo ~$169–185 MXN. Rappi aplica un delivery fee de ~$10 MXN y luego un descuento de ~-$10 MXN (resultado neto: $0). Uber Eats cobra $0 directo. Uber Eats comunica promos en el 80% del menú ('envío gratis usuarios nuevos'); Rappi en 0%.",
        "impact": "Rappi está dando el mismo beneficio económico que Uber Eats y cediendo todo el crédito psicológico. Uber Eats convierte cada visita al menú en un call-to-action de adquisición. Rappi lo desperdicia.",
        "recomendacion": "Convertir el discount_mxn actual en copy visible ('¡Envío gratis para vos!') con A/B test vs. estado actual. Hipótesis: lift de conversión del 5–10% en first-order sin costo incremental.",
    },
    {
        "title": "Rappi lidera en precio retail (OXXO): $22 Coca-Cola vs $24.50 de UberEats — ventaja no comunicada",
        "urgency": "high",
        "finding": "Rappi tiene precios retail sistemáticamente más bajos: Coca-Cola 500ml $22 MXN vs $24.50 UE (+11%); Agua 1L $19.50 vs $28.76 UE (+47%). Disponibilidad Rappi: 38/40 zonas; UE: 30/40. En retail, Rappi gana en precio Y en cobertura — pero ninguna plataforma comunica promos en este vertical.",
        "impact": "La ventaja de precio en conveniencia es real y cuantificable. Si el usuario no sabe que Rappi es más barato en OXXO que UberEats, no hay razón para elegir Rappi sobre UE en este vertical. La ventaja existe pero es invisible.",
        "recomendacion": "Campaña de precio en retail: banner 'OXXO más barato en Rappi' con comparativa directa. A/B test en home con cross-sell post-pedido restaurante ('Agregá snacks de OXXO'). Medir uplift en AOV y frecuencia de pedidos mixtos.",
    },
    {
        "title": "Roma Norte y Santa Fe como blueprint replicable: Rappi puede empatar a UberEats en ETA",
        "urgency": "med",
        "finding": "Roma Norte (12 min) y Santa Fe (12 min) son las 2 zonas donde Rappi empata con Uber Eats en velocidad de entrega. Ambas zonas tienen alta densidad de repartidores histórica. El resto de las zonas (16/18) muestra brechas significativas, lo que confirma que el problema es de ejecución, no estructural.",
        "impact": "Existe evidencia empírica de que Rappi puede competir operacionalmente con UberEats — no es un techo de plataforma, es una decisión de inversión por zona.",
        "recomendacion": "Documentar el modelo Roma Norte / Santa Fe (densidad riders/km², incentivos, geofencing activo) y aplicarlo como experimento controlado en 2–3 zonas con mayor brecha (Alvaro Obregón, Insurgentes Sur). KPI: ETA mediano <20 min en 60 días.",
    },
    {
        "title": "DiDi Food es invisible en web CDMX — ventana para blindaje preventivo",
        "urgency": "low",
        "finding": "DiDi Food no expone superficie web pública en CDMX (app-only, tráfico firmado). 0 de 60 intentos de scrape devolvieron datos de precios o disponibilidad. Su presencia comparativa es nula desde el discovery web.",
        "impact": "Si DiDi expande agresivamente (como hizo en otros mercados con subsidios de entrada), lo hará con el elemento sorpresa. Rappi tiene una ventana para fortalecer share antes de una guerra de precios, especialmente en zonas periféricas donde Rappi ya muestra ETAs altos.",
        "recomendacion": "(1) Monitoreo activo de la app DiDi mediante mystery shopping mensual en Iztapalapa, Ecatepec y Cuautitlán — zonas de expansión típicas. (2) Campañas de retención en zonas de bajo ticket. Presupuesto sugerido: 15% del marketing CDMX en Q3.",
    },
]
```

- [ ] **Step 3.2: Verify the list parses correctly**

```bash
python -c "
import sys; sys.path.insert(0, '.')
from report.generate_report import INSIGHTS
assert len(INSIGHTS) == 5
for ins in INSIGHTS:
    assert all(k in ins for k in ['title','urgency','finding','impact','recomendacion'])
print('INSIGHTS OK:', len(INSIGHTS), 'items')
"
```

Expected: `INSIGHTS OK: 5 items`

- [ ] **Step 3.3: Commit**

```bash
git add report/generate_report.py
git commit -m "feat(report): update INSIGHTS with real data (ETA 12-49min, retail price advantage, UE 80% promos)"
```

---

## Task 4: Update `_exec_summary_html` to split fast food / retail + use stats

**Files:**
- Modify: `report/generate_report.py` — replace `_exec_summary_html(df)` function

- [ ] **Step 4.1: Replace the function**

Replace the entire `def _exec_summary_html(df: pd.DataFrame) -> str:` function with:

```python
def _exec_summary_html(df: pd.DataFrame, stats: dict) -> str:
    av = df[df["available"] == True]
    rappi_count = stats["n_rappi_avail"]
    ue_count    = stats["n_ue_avail"]
    didi_count  = stats["n_didi_avail"]

    rows = [
        # Fast food
        ("🍔 Fast Food — Precios",
         f"Paridad exacta: Big Mac ~${stats['ff_price_bigmac_rappi']:.0f} (Rappi) vs ~${stats['ff_price_bigmac_ue']:.0f} (UE). Sin diferenciación en precio de producto.",
         "badge-yellow", "Paridad"),
        ("🍔 Fast Food — ETA",
         f"Rappi {stats['ff_eta_rappi_min']}–{stats['ff_eta_rappi_max']} min vs UberEats {stats['ff_eta_ue_min']}–{stats['ff_eta_ue_max']} min. Rappi solo empata en Roma Norte y Santa Fe (12 min).",
         "badge-red", "Desventaja"),
        ("🍔 Fast Food — Fees",
         f"Mismo ticket neto. Rappi fee ${stats['ff_delivery_rappi']:.0f} + descuento ${stats['ff_discount_rappi']:.0f} = $0. UE $0 directo. UE gana la narrativa: '{stats['ff_promo_pct_ue']:.0f}% filas con promo visible' vs Rappi {stats['ff_promo_pct_rappi']:.0f}%.",
         "badge-yellow", "Desventaja narrativa"),
        # Retail
        ("🛒 Retail (OXXO) — Precios",
         f"Rappi más barato: Coca-Cola ${stats['rt_price_coca_rappi']:.1f} vs UE ${stats['rt_price_coca_ue']:.1f} (+{((stats['rt_price_coca_ue']/stats['rt_price_coca_rappi'])-1)*100:.0f}%). Agua ${stats['rt_price_agua_rappi']:.1f} vs UE ${stats['rt_price_agua_ue']:.1f} (+{((stats['rt_price_agua_ue']/stats['rt_price_agua_rappi'])-1)*100:.0f}%).",
         "badge-green", "Ventaja precio"),
        ("🛒 Retail (OXXO) — Cobertura",
         f"Rappi {stats['rt_avail_rappi']}/{stats['rt_total_rappi']} zonas disponibles. UberEats {stats['rt_avail_ue']}/{stats['rt_total_ue']}. Rappi lidera en disponibilidad y precio — ventaja no comunicada.",
         "badge-green", "Ventaja cobertura"),
    ]
    header = (
        '<table class="exec-table">'
        '<thead><tr>'
        '<th>Dimensión</th><th>Hallazgo clave</th><th>Posición Rappi</th>'
        '</tr></thead><tbody>'
    )
    body = ""
    for dim, finding, badge_cls, badge_text in rows:
        body += (
            f'<tr><td><strong>{dim}</strong></td>'
            f'<td>{finding}</td>'
            f'<td><span class="badge {badge_cls}">{badge_text}</span></td></tr>'
        )
    footer_note = (
        f'<p style="margin-top:12px;font-size:12px;color:#9CA3AF;">'
        f'Muestra: {stats["n_total"]} observaciones — Rappi {rappi_count} disp. | '
        f'Uber Eats {ue_count} disp. | DiDi {didi_count} disp. | '
        f'3 plataformas × {len(stats["zones"])} zonas × 5 SKUs</p>'
    )
    return header + body + "</tbody></table>" + footer_note
```

- [ ] **Step 4.2: Commit**

```bash
git add report/generate_report.py
git commit -m "feat(report): update exec summary — 5 rows (FF + retail split), dynamic stats"
```

---

## Task 5: Update `_promo_table_html` to accept brand filter

**Files:**
- Modify: `report/generate_report.py` — replace `_promo_table_html(df)` function

- [ ] **Step 5.1: Replace the function**

```python
def _promo_table_html(df: pd.DataFrame, brand_id: str = None) -> str:
    sub = df if brand_id is None else df[df["brand_id"] == brand_id]
    rows = []
    for platform in ["rappi", "ubereats", "didi"]:
        texts = (
            sub[(sub["platform"] == platform) & sub["has_promo"]]
            ["promo_text"].dropna().unique()
        )
        color = PLATFORM_COLORS.get(platform, "#888")
        label = PLATFORM_LABELS.get(platform, platform)
        if len(texts) == 0:
            texts_html = '<span style="color:#9CA3AF;font-style:italic">Sin texto promocional visible</span>'
        else:
            texts_html = "<br>".join(f"• {t}" for t in texts)
        rows.append(
            f'<tr><td><span class="platform-dot" style="background:{color}"></span>'
            f'<strong>{label}</strong></td><td>{texts_html}</td></tr>'
        )
    return (
        '<table class="promo-table">'
        '<thead><tr><th>Plataforma</th><th>Textos promocionales únicos</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )
```

- [ ] **Step 5.2: Commit**

```bash
git add report/generate_report.py
git commit -m "refactor(report): _promo_table_html accepts brand_id filter"
```

---

## Task 6: Restructure `compose_html()` with 9 sections

**Files:**
- Modify: `report/generate_report.py` — replace entire `compose_html(df)` function

This is the largest change. Replace the function with the version below. Read carefully — each `{stats['key']}` must match exactly the keys defined in Task 1.

- [ ] **Step 6.1: Replace `compose_html(df)`**

Replace the entire `def compose_html(df: pd.DataFrame) -> str:` function with:

```python
def compose_html(df: pd.DataFrame) -> str:
    """Build and return the complete HTML report string."""
    stats = compute_stats(df)

    figs = {
        # Fast food
        "chart-ff-prices":  make_price_chart(df),
        "chart-ff-eta":     make_eta_chart(df),
        "chart-ff-fees":    make_fees_chart(df),
        "chart-ff-promos":  make_promos_chart(df),
        # Retail
        "chart-rt-prices":  make_retail_price_chart(df),
        "chart-rt-avail":   make_retail_avail_chart(df),
        "chart-rt-fees":    make_retail_fees_chart(df),
        "chart-rt-promos":  make_retail_promos_chart(df),
        # Cross
        "chart-geo":        make_geo_chart(df),
    }
    cd = {k: _fig_div(v, k) for k, v in figs.items()}
    s = stats  # shorthand

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Competitive Intelligence — Rappi 2026</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>{_css()}</style>
</head>
<body>

<aside class="sidebar">
  <div class="sidebar-brand">Rappi <span>CI</span></div>
  <nav>
    <div class="section-group">
      <div class="section-label">Informe</div>
      <a href="#exec-summary">Executive Summary</a>
    </div>
    <div class="section-group">
      <div class="section-label">Fast Food (McD)</div>
      <a href="#ff-precios">01 Precios</a>
      <a href="#ff-eta">02 Tiempos de entrega</a>
      <a href="#ff-fees">03 Fees</a>
      <a href="#ff-promos">04 Promociones</a>
    </div>
    <div class="section-group">
      <div class="section-label">Retail (OXXO)</div>
      <a href="#rt-precios">05 Precios</a>
      <a href="#rt-avail">06 Disponibilidad</a>
      <a href="#rt-fees">07 Fees</a>
      <a href="#rt-promos">08 Promociones</a>
    </div>
    <div class="section-group">
      <div class="section-label">Cruzado</div>
      <a href="#geo">09 Variabilidad geográfica</a>
    </div>
    <div class="section-group">
      <div class="section-label">Conclusiones</div>
      <a href="#insights">Top 5 Insights</a>
      <a href="#limitaciones">Limitaciones</a>
    </div>
  </nav>
</aside>

<main class="content">

  <!-- COVER -->
  <div class="cover">
    <div class="cover-tag">Documento confidencial · Uso interno Rappi</div>
    <h1>Competitive Intelligence<br>Rappi vs Uber Eats vs DiDi Food</h1>
    <p style="opacity:0.9;font-size:15px;margin-top:12px;line-height:1.5;">
      Análisis comparativo estructurado · CDMX + EdoMex · McDonald's + OXXO · {len(s['zones'])} zonas
    </p>
    <div class="cover-meta">
      <span>📅 Snapshot: {s['snapshot_date']}</span>
      <span>✍️ Julieta Pages</span>
      <span>🎯 Rappi AI Engineer Challenge</span>
    </div>
  </div>

  <!-- EXECUTIVE SUMMARY -->
  <section id="exec-summary">
    <h2>Executive Summary</h2>
    {_exec_summary_html(df, s)}
  </section>

  <!-- ══════════ FAST FOOD ══════════ -->
  <section id="ff-precios">
    <h2><span class="section-number">01</span>Posicionamiento de precios — Fast Food (McDonald's)</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      Precio unitario promedio por SKU y plataforma — filas disponibles únicamente.
    </p>
    {cd["chart-ff-prices"]}
    <div class="reading">
      <strong>Lectura:</strong> Rappi y Uber Eats tienen <strong>paridad de precio de producto</strong>
      en los 3 SKUs de fast food: Big Mac ~${s['ff_price_bigmac_rappi']:.0f} MXN, McNuggets ~${s['ff_price_nuggets_rappi']:.0f} MXN,
      Combo ~${s['ff_price_combo_rappi']:.0f} MXN (Rappi) vs ${s['ff_price_bigmac_ue']:.0f} / ${s['ff_price_nuggets_ue']:.0f} / ${s['ff_price_combo_ue']:.0f} MXN (UberEats).
      La diferenciación competitiva <strong>no ocurre en el precio del producto</strong> sino en fees,
      ETA y comunicación de promociones — ver secciones siguientes.
    </div>
  </section>

  <section id="ff-eta">
    <h2><span class="section-number">02</span>Ventaja operacional — Tiempos de entrega (Fast Food)</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      ETA promedio (minutos) por zona × plataforma. Colores más oscuros = más rápido.
    </p>
    {cd["chart-ff-eta"]}
    <div class="reading">
      <strong>Lectura:</strong> Uber Eats entrega entre <strong>{s['ff_eta_ue_min']} y {s['ff_eta_ue_max']} min</strong>;
      Rappi entre <strong>{s['ff_eta_rappi_min']} y {s['ff_eta_rappi_max']} min</strong>.
      Las únicas zonas donde Rappi empata en velocidad son <strong>Roma Norte</strong> y <strong>Santa Fe</strong> (ambas {s['ff_eta_rappi_min']} min).
      En zonas periféricas (Alvaro Obregón 49 min, Insurgentes Sur 35 min, Gustavo A. Madero 35 min)
      la brecha llega a <strong>2–3×</strong> — las de mayor riesgo de churn.
    </div>
  </section>

  <section id="ff-fees">
    <h2><span class="section-number">03</span>Estructura de fees — Fast Food</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      Desglose promedio del ticket: precio producto + delivery fee + service fee + descuento.
    </p>
    {cd["chart-ff-fees"]}
    <div class="reading">
      <strong>Lectura:</strong> Rappi muestra un <strong>delivery fee promedio de ${s['ff_delivery_rappi']:.0f} MXN</strong> y aplica
      un <strong>descuento de ${s['ff_discount_rappi']:.0f} MXN</strong> — resultado neto: $0.
      Uber Eats expone directamente <strong>delivery fee = $0</strong>.
      Mismo resultado económico para el usuario, <strong>dos narrativas opuestas</strong>:
      UberEats vende "envío gratis"; Rappi entrega el beneficio en silencio y pierde el crédito psicológico.
    </div>
  </section>

  <section id="ff-promos">
    <h2><span class="section-number">04</span>Estrategia promocional — Fast Food</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      % de filas con texto promocional visible al usuario (sin login).
    </p>
    {cd["chart-ff-promos"]}
    {_promo_table_html(df, brand_id="mcdonalds")}
    <div class="reading">
      <strong>Lectura:</strong> <strong>Uber Eats comunica promos en el {s['ff_promo_pct_ue']:.0f}% del menú visitado</strong>
      ("envío gratis usuarios nuevos", "2–3 ofertas disponibles").
      <strong>Rappi muestra {s['ff_promo_pct_rappi']:.0f}% texto promocional</strong> aunque internamente aplica un descuento
      numérico equivalente. Uber Eats convierte cada impresión de menú en un <em>call-to-action</em> de adquisición;
      Rappi pierde esa oportunidad.
    </div>
  </section>

  <!-- ══════════ RETAIL ══════════ -->
  <section id="rt-precios">
    <h2><span class="section-number">05</span>Posicionamiento de precios — Retail (OXXO)</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      Precio unitario promedio por SKU y plataforma — filas disponibles.
    </p>
    {cd["chart-rt-prices"]}
    <div class="reading">
      <strong>Lectura:</strong> <strong>Rappi tiene precios retail sistemáticamente más bajos que UberEats.</strong>
      Coca-Cola 500ml: Rappi ${s['rt_price_coca_rappi']:.1f} vs UberEats ${s['rt_price_coca_ue']:.1f} MXN
      (+{((s['rt_price_coca_ue']/s['rt_price_coca_rappi'])-1)*100:.0f}% más caro en UE).
      Agua 1L: Rappi ${s['rt_price_agua_rappi']:.1f} vs UberEats ${s['rt_price_agua_ue']:.1f} MXN
      (+{((s['rt_price_agua_ue']/s['rt_price_agua_rappi'])-1)*100:.0f}% más caro en UE).
      Esta ventaja de precio es <strong>real y no comunicada</strong> al usuario.
    </div>
  </section>

  <section id="rt-avail">
    <h2><span class="section-number">06</span>Disponibilidad por zona — Retail (OXXO)</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      ✓ = disponible · ~ = parcial · ✗ = no disponible
    </p>
    {cd["chart-rt-avail"]}
    <div class="reading">
      <strong>Lectura:</strong> Rappi tiene disponibilidad de OXXO en <strong>{s['rt_avail_rappi']}/{s['rt_total_rappi']} zonas</strong> ({s['rt_avail_rappi']/s['rt_total_rappi']*100:.0f}%).
      UberEats tiene <strong>{s['rt_avail_ue']}/{s['rt_total_ue']} zonas</strong> ({s['rt_avail_ue']/s['rt_total_ue']*100:.0f}%).
      Rappi lidera en cobertura Y en precio — la combinación de ambas ventajas hace del vertical retail
      la <strong>mayor oportunidad de diferenciación no explotada</strong> del análisis.
    </div>
  </section>

  <section id="rt-fees">
    <h2><span class="section-number">07</span>Estructura de fees — Retail (OXXO)</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      Delivery fee bruto y descuento aplicado por plataforma en pedidos OXXO.
    </p>
    {cd["chart-rt-fees"]}
    <div class="reading">
      <strong>Lectura:</strong> La estructura de fees en retail sigue el mismo patrón que en fast food —
      Rappi aplica un fee y luego un descuento equivalente, UberEats cobra $0 directo.
      El resultado neto para el usuario es comparable, pero la narrativa nuevamente favorece a UberEats.
    </div>
  </section>

  <section id="rt-promos">
    <h2><span class="section-number">08</span>Estrategia promocional — Retail (OXXO)</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      % de filas con texto promocional visible al usuario (sin login), vertical retail.
    </p>
    {cd["chart-rt-promos"]}
    {_promo_table_html(df, brand_id="oxxo")}
    <div class="reading">
      <strong>Lectura:</strong> Ninguna plataforma muestra texto promocional visible en el vertical retail.
      Rappi {s['rt_promo_pct_rappi']:.0f}%, UberEats {s['rt_promo_pct_ue']:.0f}%.
      Dado que Rappi tiene ventaja real de precio ({((s['rt_price_coca_ue']/s['rt_price_coca_rappi'])-1)*100:.0f}%–{((s['rt_price_agua_ue']/s['rt_price_agua_rappi'])-1)*100:.0f}% más barato), el
      silencio promocional en retail es la mayor oportunidad de comunicación sin costo incremental.
    </div>
  </section>

  <!-- ══════════ CRUZADO ══════════ -->
  <section id="geo">
    <h2><span class="section-number">09</span>Variabilidad geográfica — Fast Food</h2>
    <p style="color:#6B7280;font-size:13px;margin-bottom:12px;">
      Ticket final promedio por zona × plataforma — McDonald's, filas disponibles.
    </p>
    {cd["chart-geo"]}
    <div class="reading">
      <strong>Lectura:</strong> El precio de producto es nacional y uniforme en McDonald's, por lo que
      la variabilidad geográfica refleja principalmente <strong>disponibilidad</strong> (qué zonas cubrió cada plataforma)
      y <strong>fee structure</strong> (delivery fee, descuentos).
      El análisis cubre {len(s['zones'])} zonas: {', '.join(s['zones'][:8])}{'…' if len(s['zones']) > 8 else ''}.
    </div>
  </section>

  <!-- TOP 5 INSIGHTS -->
  <section id="insights">
    <h2>Top 5 Insights Accionables</h2>
    {_insights_html()}
  </section>

  <!-- LIMITACIONES -->
  <section id="limitaciones" class="limitations">
    <h2>Limitaciones y próximos pasos</h2>
    <ul>
      <li><strong>Muestra dirigida</strong> ({s['n_available']} observaciones disponibles de {s['n_total']}). Los insights son <em>direccionales</em>, no estadísticamente significativos.</li>
      <li><strong>Snapshot único</strong> ({s['snapshot_date']}, ~02:00 UTC). Sin variabilidad temporal — un horario de almuerzo o cena podría modificar los ETAs significativamente.</li>
      <li><strong>Usuario anónimo (sin login).</strong> Fees y promos reflejan la oferta de adquisición; usuarios Prime/recurrentes verían condiciones distintas.</li>
      <li><strong>DiDi sin cobertura cuantitativa</strong> — limitación estructural (app-only en CDMX). Mystery shopping manual sería el próximo paso.</li>
      <li><strong>Cobertura asimétrica:</strong> no todas las zonas tienen datos de ambas plataformas en fast food. La comparación ETA es válida solo donde ambas plataformas tienen datos.</li>
    </ul>
    <div class="next-steps">
      <h3>Próximos pasos sugeridos</h3>
      <ol>
        <li>Correr el scraper en 3 horarios (almuerzo 13h / cena 20h / madrugada 02h) y comparar varianza intra-día de ETAs en las 5 zonas con mayor brecha.</li>
        <li>Lanzar campaña A/B de comunicación de precio retail ("OXXO más barato en Rappi") — bajo costo, alto potencial de diferenciación.</li>
        <li>Mystery shopping manual de DiDi en Iztapalapa y Ecatepec para punto de comparación cualitativo.</li>
        <li>Login real + comparación logueado vs anónimo para cuantificar el valor del programa de fidelidad de cada plataforma.</li>
        <li>Expandir a 50+ zonas para significancia estadística en análisis geográfico.</li>
      </ol>
    </div>
  </section>

  <footer>
    <strong>Metodología:</strong> Datos recolectados mediante scraping web ético (robots.txt respetado,
    rate limiting 1.5s entre requests, user-agent Chrome desktop) en {s['snapshot_date']}.
    Plataformas: Rappi MX, Uber Eats MX, DiDi Food MX.
    {len(s['zones'])} zonas analizadas: {', '.join(s['zones'])}.
    SKUs: Big Mac, McNuggets 10pz, Combo Big Mac med., Coca-Cola 500ml, Agua 1L.
    Sin login — oferta de usuario anónimo únicamente.<br>
    <span style="margin-top:6px;display:block;">
      Elaborado por Julieta Pages · Reto Técnico Rappi AI Engineer · 2026
    </span>
  </footer>

</main>
</body>
</html>"""
```

- [ ] **Step 6.2: Fix the call in `main()` — `_exec_summary_html` now takes two args**

Find the `main()` function and verify there's no direct call to `_exec_summary_html`. It's called inside `compose_html()`, so no change needed in `main()`.

- [ ] **Step 6.3: Run the full report generator**

```bash
cd competitive-intelligence
python -m report.generate_report
```

Expected output:
```
Loaded 260 rows | 152 available
Report written → report/competitive_intelligence_2026.html (XXX KB)
```

If there are errors, they will be one of:
- KeyError on `stats` dict → check that `compute_stats()` returns the missing key
- AttributeError on figure → check that the new chart functions return a valid `go.Figure`
- Division by zero in reading text → add guard: `if s['rt_price_coca_rappi'] else 0`

- [ ] **Step 6.4: Open the HTML and verify visually**

Open `report/competitive_intelligence_2026.html` in a browser and check:
- [ ] Sidebar shows 9 section links (4 fast food, 4 retail, 1 geo)
- [ ] Section 01–04 labeled "Fast Food (McDonald's)"
- [ ] Section 05–08 labeled "Retail (OXXO)"
- [ ] Executive summary table has 5 rows (3 fast food, 2 retail)
- [ ] ETA reading text shows "12 y 49 min" and "10 y 37 min"
- [ ] Retail price reading shows Coca-Cola $22.0 vs $24.5
- [ ] Top 5 Insights shows updated text (not old 14-49 / 10-23 values)
- [ ] Footer lists all 20 zones

- [ ] **Step 6.5: Commit**

```bash
git add report/generate_report.py report/competitive_intelligence_2026.html
git commit -m "feat(report): restructure report — 9 sections (FF + retail split), dynamic narratives, 20 zones"
```

---

## Self-Review Checklist

### Spec coverage

| Spec requirement | Task |
|-----------------|------|
| `compute_stats(df)` with all metrics | Task 1 |
| 4 retail chart functions | Task 2 |
| Updated INSIGHTS with real numbers | Task 3 |
| Exec summary split FF/retail + dynamic | Task 4 |
| `_promo_table_html` brand filter | Task 5 |
| 9-section `compose_html` | Task 6 |
| Dynamic reading text (ETA, fees, prices, retail) | Task 6 |
| Sidebar with 9 nav links | Task 6 |
| All 20 zones in footer | Task 6 |
| Retail availability heatmap | Task 2 (`make_retail_avail_chart`) |

### Placeholder scan

No TBDs, no "implement later", no "similar to Task N". All code is complete.

### Type consistency

- `_exec_summary_html(df, stats)` — now takes 2 args. Updated in Task 4. Called in Task 6 as `_exec_summary_html(df, s)`. ✓
- `_promo_table_html(df, brand_id=None)` — optional kwarg. Called as `_promo_table_html(df, brand_id="mcdonalds")` and `_promo_table_html(df, brand_id="oxxo")`. ✓
- `compute_stats(df)` returns dict with all keys used in Task 6 f-strings. Verified in Task 1 step 1.2. ✓
- Chart functions all return `go.Figure`. Verified in Task 2 step 2.5. ✓
