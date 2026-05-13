#!/usr/bin/env python3
"""
Competitive Intelligence HTML Report Generator.
Reads ../scrapes.csv and writes competitive_intelligence_2026.html.
Run from any directory: python -m report.generate_report
"""
import pathlib
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = pathlib.Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "scrapes.csv"
OUTPUT_PATH = pathlib.Path(__file__).parent / "competitive_intelligence_2026.html"

PLATFORM_COLORS = {"rappi": "#FF441F", "ubereats": "#06C167", "didi": "#FF7900"}
PLATFORM_LABELS = {"rappi": "Rappi", "ubereats": "Uber Eats", "didi": "DiDi Food"}
SKU_LABELS = {
    "big_mac": "Big Mac",
    "mcombo_bigmac_med": "Combo Big Mac med.",
    "mcnuggets_10": "McNuggets 10pz",
    "cocacola_500ml": "Coca-Cola 500ml",
    "agua_1l": "Agua 1L",
}
NUMERIC_COLS = [
    "unit_price_mxn", "delivery_fee_mxn", "service_fee_mxn",
    "discount_mxn", "total_final_mxn", "eta_min", "eta_min_low", "eta_min_high",
]

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


def _css() -> str:
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 14px;
        color: #1A1A2E;
        background: #fff;
        display: flex;
    }

    /* ── Sidebar ─────────────────────────────────── */
    .sidebar {
        position: fixed;
        top: 0; left: 0;
        width: 220px; height: 100vh;
        background: #F8F9FA;
        border-right: 1px solid #E5E7EB;
        padding: 24px 16px;
        overflow-y: auto;
        z-index: 100;
    }
    .sidebar-brand {
        font-size: 18px;
        font-weight: 700;
        color: #FF441F;
        margin-bottom: 24px;
        letter-spacing: -0.5px;
    }
    .sidebar-brand span { color: #1A1A2E; }
    .sidebar nav a {
        display: block;
        padding: 6px 8px;
        border-radius: 4px;
        color: #6B7280;
        text-decoration: none;
        font-size: 12.5px;
        margin-bottom: 2px;
        transition: background 0.15s, color 0.15s;
    }
    .sidebar nav a:hover { background: #FF441F18; color: #FF441F; }
    .sidebar nav .section-group { margin-top: 16px; }
    .sidebar nav .section-label {
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #9CA3AF;
        padding: 0 8px;
        margin-bottom: 4px;
    }

    /* ── Main content ────────────────────────────── */
    .content {
        margin-left: 220px;
        flex: 1;
        max-width: 960px;
        padding: 0 40px 80px;
    }

    /* ── Cover ───────────────────────────────────── */
    .cover {
        background: linear-gradient(135deg, #FF441F 0%, #FF6B47 100%);
        color: white;
        padding: 60px 40px 48px;
        margin: 0 -40px 48px;
    }
    .cover-tag {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        opacity: 0.85;
        margin-bottom: 16px;
    }
    .cover h1 {
        font-size: 32px;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }
    .cover-meta {
        font-size: 13px;
        opacity: 0.85;
        margin-top: 24px;
    }
    .cover-meta span { margin-right: 24px; }

    /* ── Section headings ────────────────────────── */
    section { margin-bottom: 56px; }
    section h2 {
        font-size: 20px;
        font-weight: 700;
        color: #1A1A2E;
        border-bottom: 2px solid #FF441F;
        padding-bottom: 8px;
        margin-bottom: 20px;
        letter-spacing: -0.3px;
    }
    section h3 {
        font-size: 15px;
        font-weight: 600;
        color: #374151;
        margin: 24px 0 10px;
    }
    .section-number {
        display: inline-block;
        background: #FF441F;
        color: white;
        font-size: 11px;
        font-weight: 700;
        border-radius: 3px;
        padding: 1px 7px;
        margin-right: 8px;
        vertical-align: middle;
    }

    /* ── Exec summary table ──────────────────────── */
    .exec-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    .exec-table th {
        background: #F3F4F6;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 10px 14px;
        text-align: left;
        color: #6B7280;
        border-bottom: 1px solid #E5E7EB;
    }
    .exec-table td {
        padding: 10px 14px;
        border-bottom: 1px solid #F3F4F6;
        font-size: 13px;
        vertical-align: middle;
    }
    .exec-table tr:last-child td { border-bottom: none; }
    .exec-table tr:hover td { background: #FAFAFA; }
    .badge {
        display: inline-block;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 11.5px;
        font-weight: 600;
    }
    .badge-green { background: #D1FAE5; color: #065F46; }
    .badge-yellow { background: #FEF3C7; color: #92400E; }
    .badge-red { background: #FEE2E2; color: #991B1B; }

    /* ── Reading paragraphs ──────────────────────── */
    .reading {
        background: #F8F9FA;
        border-left: 3px solid #FF441F;
        padding: 14px 18px;
        border-radius: 0 6px 6px 0;
        font-size: 13.5px;
        line-height: 1.65;
        color: #374151;
        margin-top: 16px;
    }
    .reading strong { color: #1A1A2E; }

    /* ── Promo text table ────────────────────────── */
    .promo-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    .promo-table th {
        background: #F3F4F6;
        font-size: 12px;
        font-weight: 600;
        padding: 8px 12px;
        text-align: left;
        color: #6B7280;
        border-bottom: 1px solid #E5E7EB;
    }
    .promo-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #F3F4F6;
        font-size: 12.5px;
    }
    .platform-dot {
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }

    /* ── Insight cards ───────────────────────────── */
    .insights-grid { display: flex; flex-direction: column; gap: 20px; margin-top: 8px; }
    .insight-card {
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .insight-header {
        padding: 14px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .insight-number {
        font-size: 22px;
        font-weight: 700;
        opacity: 0.25;
        line-height: 1;
        flex-shrink: 0;
    }
    .insight-title {
        font-size: 14px;
        font-weight: 600;
        line-height: 1.3;
    }
    .insight-body { padding: 0 20px 18px; }
    .insight-row { margin-top: 12px; }
    .insight-label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #9CA3AF;
        margin-bottom: 3px;
    }
    .insight-text { font-size: 13px; line-height: 1.6; color: #374151; }

    /* Urgency colors */
    .urgency-high .insight-header { background: #FFF1F0; border-left: 4px solid #FF441F; }
    .urgency-high .insight-number { color: #FF441F; }
    .urgency-med .insight-header { background: #FFFBEB; border-left: 4px solid #F59E0B; }
    .urgency-med .insight-number { color: #F59E0B; }
    .urgency-low .insight-header { background: #F0FDF4; border-left: 4px solid #10B981; }
    .urgency-low .insight-number { color: #10B981; }

    /* ── Limitations ─────────────────────────────── */
    .limitations ul { padding-left: 20px; }
    .limitations li { font-size: 13px; line-height: 1.7; color: #6B7280; }
    .next-steps { margin-top: 20px; }
    .next-steps h3 { color: #374151; font-size: 14px; margin-bottom: 8px; }
    .next-steps ol { padding-left: 20px; }
    .next-steps li { font-size: 13px; line-height: 1.7; color: #374151; }

    /* ── Footer ──────────────────────────────────── */
    footer {
        margin-top: 60px;
        padding: 24px 0;
        border-top: 1px solid #E5E7EB;
        font-size: 12px;
        color: #9CA3AF;
        line-height: 1.6;
    }

    /* ── Print ───────────────────────────────────── */
    @media print {
        body { display: block; font-size: 12px; }
        .sidebar { display: none; }
        .content { margin-left: 0; padding: 0 20px 40px; max-width: 100%; }
        .cover { margin: 0 -20px 32px; padding: 40px 20px; }
        section { page-break-inside: avoid; }
        .insight-card { page-break-inside: avoid; }
    }
    """


def _fig_div(fig: go.Figure, div_id: str) -> str:
    """Serialize a Plotly figure to an embeddable HTML div."""
    return pio.to_html(fig, full_html=False, include_plotlyjs=False, div_id=div_id)


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


def _exec_summary_html(df: pd.DataFrame, stats: dict) -> str:
    rappi_count = stats["n_rappi_avail"]
    ue_count    = stats["n_ue_avail"]
    didi_count  = stats["n_didi_avail"]

    rows = [
        (f"🍔 Fast Food — Precios",
         f"Paridad exacta: Big Mac ~${stats['ff_price_bigmac_rappi']:.0f} (Rappi) vs ~${stats['ff_price_bigmac_ue']:.0f} (UE). Sin diferenciación en precio de producto.",
         "badge-yellow", "Paridad"),
        (f"🍔 Fast Food — ETA",
         f"Rappi {stats['ff_eta_rappi_min']}–{stats['ff_eta_rappi_max']} min vs UberEats {stats['ff_eta_ue_min']}–{stats['ff_eta_ue_max']} min. Rappi solo empata en Roma Norte y Santa Fe (12 min).",
         "badge-red", "Desventaja"),
        (f"🍔 Fast Food — Fees",
         f"Mismo ticket neto. Rappi fee ${stats['ff_delivery_rappi']:.0f} + descuento ${stats['ff_discount_rappi']:.0f} = $0. UE $0 directo. UE gana la narrativa: '{stats['ff_promo_pct_ue']:.0f}% filas con promo visible' vs Rappi {stats['ff_promo_pct_rappi']:.0f}%.",
         "badge-yellow", "Desventaja narrativa"),
        (f"🛒 Retail (OXXO) — Precios",
         f"Rappi más barato: Coca-Cola ${stats['rt_price_coca_rappi']:.1f} vs UE ${stats['rt_price_coca_ue']:.1f} (+{((stats['rt_price_coca_ue']/stats['rt_price_coca_rappi'])-1)*100:.0f}%). Agua ${stats['rt_price_agua_rappi']:.1f} vs UE ${stats['rt_price_agua_ue']:.1f} (+{((stats['rt_price_agua_ue']/stats['rt_price_agua_rappi'])-1)*100:.0f}%).",
         "badge-green", "Ventaja precio"),
        (f"🛒 Retail (OXXO) — Cobertura",
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
        f'3 plataformas x {len(stats["zones"])} zonas x 5 SKUs</p>'
    )
    return header + body + "</tbody></table>" + footer_note


def _insights_html() -> str:
    cards = []
    for i, ins in enumerate(INSIGHTS, 1):
        urgency = ins["urgency"]
        cards.append(f"""
        <div class="insight-card urgency-{urgency}">
          <div class="insight-header">
            <span class="insight-number">{i:02d}</span>
            <span class="insight-title">{ins['title']}</span>
          </div>
          <div class="insight-body">
            <div class="insight-row">
              <div class="insight-label">Finding</div>
              <div class="insight-text">{ins['finding']}</div>
            </div>
            <div class="insight-row">
              <div class="insight-label">Impacto</div>
              <div class="insight-text">{ins['impact']}</div>
            </div>
            <div class="insight-row">
              <div class="insight-label">Recomendación</div>
              <div class="insight-text">{ins['recomendacion']}</div>
            </div>
          </div>
        </div>""")
    return f'<div class="insights-grid">{"".join(cards)}</div>'


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["has_promo"] = df["promo_text"].notna() & (df["promo_text"].astype(str).str.len() > 0)
    return df


def compute_stats(df: pd.DataFrame) -> dict:
    """Compute all dynamic metrics used in narrative text."""
    av = df[df["available"] == True]
    ff = av[av["brand_id"] == "mcdonalds"]
    rt = av[av["brand_id"] == "oxxo"]
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

    ff_rappi_fees = ff[ff["platform"] == "rappi"]
    ff_delivery_rappi = round(ff_rappi_fees["delivery_fee_mxn"].mean(), 1) if len(ff_rappi_fees) else 0
    ff_discount_rappi = round(ff_rappi_fees["discount_mxn"].mean(), 1) if len(ff_rappi_fees) else 0

    def _price_range(sub, platform, sku):
        vals = sub[(sub["platform"] == platform) & (sub["product_sku"] == sku)]["unit_price_mxn"].dropna()
        if len(vals) == 0:
            return (None, None)
        return (round(vals.min(), 1), round(vals.max(), 1))

    return {
        "ff_eta_rappi_min": ff_eta_rappi[0],
        "ff_eta_rappi_max": ff_eta_rappi[1],
        "ff_eta_ue_min":    ff_eta_ue[0],
        "ff_eta_ue_max":    ff_eta_ue[1],
        "ff_price_bigmac_rappi":  _avg_price(ff, "rappi", "big_mac"),
        "ff_price_bigmac_ue":     _avg_price(ff, "ubereats", "big_mac"),
        "ff_price_nuggets_rappi": _avg_price(ff, "rappi", "mcnuggets_10"),
        "ff_price_nuggets_ue":    _avg_price(ff, "ubereats", "mcnuggets_10"),
        "ff_price_combo_rappi":   _avg_price(ff, "rappi", "mcombo_bigmac_med"),
        "ff_price_combo_ue":      _avg_price(ff, "ubereats", "mcombo_bigmac_med"),
        "ff_delivery_rappi": ff_delivery_rappi,
        "ff_discount_rappi": ff_discount_rappi,
        "ff_promo_pct_rappi": _promo_pct(ff, "rappi"),
        "ff_promo_pct_ue":    _promo_pct(ff, "ubereats"),
        "rt_promo_pct_rappi": _promo_pct(rt, "rappi"),
        "rt_promo_pct_ue":    _promo_pct(rt, "ubereats"),
        "rt_price_coca_rappi":       _avg_price(rt, "rappi", "cocacola_500ml"),
        "rt_price_coca_ue":          _avg_price(rt, "ubereats", "cocacola_500ml"),
        "rt_price_agua_rappi":       _avg_price(rt, "rappi", "agua_1l"),
        "rt_price_agua_ue":          _avg_price(rt, "ubereats", "agua_1l"),
        "rt_price_coca_rappi_range": _price_range(rt, "rappi", "cocacola_500ml"),
        "rt_price_agua_rappi_range": _price_range(rt, "rappi", "agua_1l"),
        "rt_avail_rappi": int(len(df_rt_all[(df_rt_all["platform"] == "rappi") & (df_rt_all["available"] == True)])),
        "rt_total_rappi": int(len(df_rt_all[df_rt_all["platform"] == "rappi"])),
        "rt_avail_ue":    int(len(df_rt_all[(df_rt_all["platform"] == "ubereats") & (df_rt_all["available"] == True)])),
        "rt_total_ue":    int(len(df_rt_all[df_rt_all["platform"] == "ubereats"])),
        "zones":       sorted(av["address_label"].unique().tolist()),
        "n_total":     len(df),
        "n_available": len(av),
        "n_rappi_avail":    int(len(av[av["platform"] == "rappi"])),
        "n_ue_avail":       int(len(av[av["platform"] == "ubereats"])),
        "n_didi_avail":     int(len(av[av["platform"] == "didi"])),
        "snapshot_date": df["timestamp_utc"].dropna().iloc[0][:10] if "timestamp_utc" in df.columns else "2026-05-13",
    }


def make_price_chart(df: pd.DataFrame) -> go.Figure:
    """Bar chart: unit price by SKU × platform (fast food only, available rows)."""
    av = df[(df["available"] == True) & (df["brand_id"] == "mcdonalds")]
    fast_food_skus = ["big_mac", "mcnuggets_10", "mcombo_bigmac_med"]

    fig = go.Figure()
    for platform in ["rappi", "ubereats"]:
        pdata = av[av["platform"] == platform]
        prices = pdata.groupby("product_sku")["unit_price_mxn"].mean()
        x_labels = [SKU_LABELS[s] for s in fast_food_skus if s in prices.index]
        y_vals = [prices[s] for s in fast_food_skus if s in prices.index]
        fig.add_trace(go.Bar(
            name=PLATFORM_LABELS[platform],
            x=x_labels,
            y=y_vals,
            marker_color=PLATFORM_COLORS[platform],
            text=[f"${v:.0f}" for v in y_vals],
            textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=340,
        margin=dict(l=20, r=20, t=10, b=40),
        yaxis_title="MXN",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig


def make_eta_chart(df: pd.DataFrame) -> go.Figure:
    """Heatmap: average ETA by zone × platform. Darker = faster."""
    av = df[(df["available"] == True) & df["eta_min"].notna()]
    pivot = (
        av.groupby(["address_label", "platform"])["eta_min"]
        .mean()
        .round(0)
        .unstack("platform")
        .reindex(columns=["rappi", "ubereats", "didi"])
        .dropna(axis=1, how="all")
    )

    z = pivot.values
    text = [[f"{v:.0f}" if not pd.isna(v) else "N/D" for v in row] for row in z]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[PLATFORM_LABELS.get(c, c) for c in pivot.columns],
        y=list(pivot.index),
        colorscale="YlOrRd_r",
        text=text,
        texttemplate="%{text} min",
        showscale=True,
        colorbar=dict(title="min", thickness=12),
    ))
    fig.update_layout(
        template="plotly_white",
        height=300,
        margin=dict(l=20, r=20, t=10, b=20),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig


def make_fees_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar: average ticket composition by platform."""
    av = df[(df["available"] == True) & df["unit_price_mxn"].notna()]
    fee_cols = ["unit_price_mxn", "delivery_fee_mxn", "service_fee_mxn", "discount_mxn"]
    fees = av.groupby("platform")[fee_cols].mean().round(1)

    fee_labels = {
        "unit_price_mxn": "Precio producto",
        "delivery_fee_mxn": "Delivery fee",
        "service_fee_mxn": "Service fee",
        "discount_mxn": "Descuento",
    }
    fee_colors = ["#4C72B0", "#DD8452", "#937860", "#C44E52"]

    fig = go.Figure()
    for col, color in zip(fee_cols, fee_colors):
        fig.add_trace(go.Bar(
            name=fee_labels[col],
            x=[PLATFORM_LABELS.get(p, p) for p in fees.index],
            y=fees[col].tolist(),
            marker_color=color,
        ))

    totals = av.groupby("platform")["total_final_mxn"].mean().round(1)
    for i, platform in enumerate(fees.index):
        if platform in totals.index:
            fig.add_annotation(
                x=PLATFORM_LABELS.get(platform, platform),
                y=totals[platform] + 5,
                text=f"<b>Total: ${totals[platform]:.0f}</b>",
                showarrow=False,
                font=dict(size=11),
            )

    fig.update_layout(
        barmode="stack",
        template="plotly_white",
        height=350,
        margin=dict(l=20, r=20, t=30, b=40),
        yaxis_title="MXN",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig


def make_promos_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: % of rows with visible promo text, by platform."""
    pct = df.groupby("platform")["has_promo"].mean().mul(100).round(1)
    platforms = list(pct.index)

    fig = go.Figure(go.Bar(
        x=[PLATFORM_LABELS.get(p, p) for p in platforms],
        y=pct.tolist(),
        marker_color=[PLATFORM_COLORS.get(p, "#888") for p in platforms],
        text=[f"{v:.0f}%" for v in pct],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=20, r=20, t=10, b=40),
        yaxis=dict(title="%", range=[0, 120]),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig


def make_geo_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar: average total ticket by zone × platform (fast food only for apples-to-apples)."""
    av = df[(df["available"] == True) & (df["brand_id"] == "mcdonalds") & df["total_final_mxn"].notna()]
    geo = (
        av.groupby(["address_label", "platform"])["total_final_mxn"]
        .mean()
        .round(1)
        .unstack("platform")
    )

    fig = go.Figure()
    for platform in ["rappi", "ubereats"]:
        if platform not in geo.columns:
            continue
        y_vals = geo[platform].tolist()
        text_vals = [f"${v:.0f}" if not pd.isna(v) else "" for v in y_vals]
        fig.add_trace(go.Bar(
            name=PLATFORM_LABELS[platform],
            x=list(geo.index),
            y=y_vals,
            marker_color=PLATFORM_COLORS[platform],
            text=text_vals,
            textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        template="plotly_white",
        height=350,
        margin=dict(l=20, r=20, t=10, b=60),
        yaxis_title="MXN",
        xaxis_tickangle=-20,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, system-ui, sans-serif", size=12),
    )
    return fig


def make_retail_price_chart(df: pd.DataFrame) -> go.Figure:
    """Bar chart: avg unit price by retail SKU x platform (available rows only)."""
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


def make_retail_avail_chart(df: pd.DataFrame) -> go.Figure:
    """Heatmap: OXXO availability (1=yes, 0=no) by zone x platform."""
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


def compose_html(df: pd.DataFrame) -> str:
    """Build and return the complete HTML report string."""
    stats = compute_stats(df)

    figs = {
        "chart-ff-prices":  make_price_chart(df),
        "chart-ff-eta":     make_eta_chart(df),
        "chart-ff-fees":    make_fees_chart(df),
        "chart-ff-promos":  make_promos_chart(df),
        "chart-rt-prices":  make_retail_price_chart(df),
        "chart-rt-avail":   make_retail_avail_chart(df),
        "chart-rt-fees":    make_retail_fees_chart(df),
        "chart-rt-promos":  make_retail_promos_chart(df),
        "chart-geo":        make_geo_chart(df),
    }
    cd = {k: _fig_div(v, k) for k, v in figs.items()}
    s = stats

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
      <span>Snapshot: {s['snapshot_date']}</span>
      <span>Julieta Pages</span>
      <span>Rappi AI Engineer Challenge</span>
    </div>
  </div>

  <!-- EXECUTIVE SUMMARY -->
  <section id="exec-summary">
    <h2>Executive Summary</h2>
    {_exec_summary_html(df, s)}
  </section>

  <!-- FAST FOOD SECTIONS -->
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

  <!-- RETAIL SECTIONS -->
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
      Verde = disponible · amarillo = parcial · rojo = no disponible
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
      Dado que Rappi tiene ventaja real de precio ({((s['rt_price_coca_ue']/s['rt_price_coca_rappi'])-1)*100:.0f}%–{((s['rt_price_agua_ue']/s['rt_price_agua_rappi'])-1)*100:.0f}% más barato),
      el silencio promocional en retail es la mayor oportunidad de comunicación sin costo incremental.
    </div>
  </section>

  <!-- GEO -->
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
      El análisis cubre {len(s['zones'])} zonas: {', '.join(s['zones'][:8])}{'...' if len(s['zones']) > 8 else ''}.
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


def main():
    df = load_data()
    av = df[df["available"] == True]
    print(f"Loaded {len(df)} rows | {len(av)} available")
    html = compose_html(df)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Report written: {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
