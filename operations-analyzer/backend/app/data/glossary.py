"""Metric glossary with business semantics."""

GLOSSARY: dict[str, dict] = {
    "% PRO Users Who Breakeven": {
        "description": "Usuarios Pro cuyo valor generado cubre el costo de su membresía / Total usuarios Pro.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Pro",
    },
    "% Restaurants Sessions With Optimal Assortment": {
        "description": "Sesiones con >=40 restaurantes / Total sesiones.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Restaurants",
    },
    "Gross Profit UE": {
        "description": "Margen bruto de ganancia / Total de ordenes.",
        "higher_is_better": True,
        "format": "currency",
        "category": "Unit Economics",
    },
    "Lead Penetration": {
        "description": "Tiendas habilitadas / (leads + habilitadas + salidas).",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Supply",
    },
    "MLTV Top Verticals Adoption": {
        "description": "Usuarios con ordenes en multiples verticales / Total usuarios.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Verticals",
    },
    "Non-Pro PTC > OP": {
        "description": "Conversion No-Pro de Proceed to Checkout a Order Placed.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Perfect Orders": {
        "description": "Ordenes sin cancelaciones/defectos/demoras / Total ordenes.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Quality",
    },
    "Pro Adoption": {
        "description": "Usuarios Pro / Total usuarios.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Pro",
    },
    "Restaurants Markdowns / GMV": {
        "description": "Descuentos en ordenes restaurantes / GMV Restaurantes.",
        "higher_is_better": False,
        "format": "percentage",
        "category": "Restaurants",
    },
    "Restaurants SS > ATC CVR": {
        "description": "Conversion Select Store a Add to Cart en restaurantes.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Restaurants SST > SS CVR": {
        "description": "Conversion Store Selection Type a Select Store en restaurantes.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Retail SST > SS CVR": {
        "description": "Conversion Store Selection Type a Select Store en retail.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Turbo Adoption": {
        "description": "Usuarios que compran en Turbo / Total usuarios con Turbo disponible.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Verticals",
    },
    "Orders": {
        "description": "Volumen total de ordenes en la zona.",
        "higher_is_better": True,
        "format": "integer",
        "category": "Volume",
    },
}


def get_glossary_entry(metric_name: str) -> dict | None:
    return GLOSSARY.get(metric_name)


def glossary_for_prompt() -> str:
    """Format glossary as compact string for LLM system prompt."""
    lines = []
    for name, entry in GLOSSARY.items():
        direction = "higher is better" if entry["higher_is_better"] else "lower is better"
        lines.append(f"- **{name}** ({direction}): {entry['description']}")
    return "\n".join(lines)
