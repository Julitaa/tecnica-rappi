"""OpenAI function-calling schemas for each toolbox method."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "top_n_zones",
            "description": "Devuelve top N zonas para una métrica en una semana dada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "n": {"type": "integer", "default": 5},
                    "week_offset": {"type": "integer", "default": 0,
                                    "description": "0=L0W (semana actual), 8=L8W"},
                    "filters": {"type": "object",
                                "description": "ej {country: 'CO', zone_type: 'Wealthy'}"},
                    "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_segments",
            "description": "Compara una métrica entre segmentos (group_by puede ser country, zone_type, zone_prioritization).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "group_by": {"type": "string"},
                    "filters": {"type": "object"},
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["metric", "group_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "metric_trend",
            "description": "Evolución temporal de una métrica en una zona específica (últimas N semanas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "country": {"type": "string"},
                    "zone": {"type": "string"},
                    "weeks": {"type": "integer", "default": 9},
                },
                "required": ["metric", "country", "zone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate",
            "description": "Agrega una métrica por una dimensión (mean/median/sum/min/max/std).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "group_by": {"type": "string"},
                    "agg": {"type": "string",
                            "enum": ["mean", "median", "sum", "min", "max", "std"],
                            "default": "mean"},
                    "filters": {"type": "object"},
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["metric", "group_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multivariable_filter",
            "description": "Encuentra zonas que cumplen múltiples condiciones sobre distintas métricas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "metric": {"type": "string"},
                                "op": {"type": "string",
                                       "enum": [">", "<", ">=", "<=", "=="]},
                                "value": {"type": "number"},
                            },
                            "required": ["metric", "op", "value"],
                        },
                    },
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correlate_metrics",
            "description": "Correlación de Pearson entre dos métricas a través del panel de zonas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_a": {"type": "string"},
                    "metric_b": {"type": "string"},
                    "scope": {"type": "object",
                              "description": "filtros opcionales: country, zone_type, ..."},
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["metric_a", "metric_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "growth_explainer",
            "description": "Identifica zonas con mayor crecimiento en órdenes y compara sus métricas vs el resto para hipotetizar causas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "default": "Orders"},
                    "weeks": {"type": "integer", "default": 5},
                    "top_n": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Fallback: ejecuta un SELECT SQL sobre las tablas metrics_df y "
                "orders_df (ver schemas más abajo). Usar solo si las otras "
                "tools no cubren la pregunta. Tablas disponibles:\n"
                "metrics_df(country, city, zone, zone_type, zone_prioritization, metric, week_offset, value)\n"
                "orders_df(country, city, zone, metric, week_offset, value)"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string",
                              "description": "SQL SELECT (DuckDB syntax)"},
                },
                "required": ["query"],
            },
        },
    },
]
