# Spec: Report Refactor — Fast Food + Retail, Nuevas Zonas, Stats Dinámicos

**Fecha:** 2026-05-13  
**Rama:** competitive-intelligence  
**Archivo objetivo:** `report/generate_report.py`

---

## Contexto

El reporte HTML original fue generado con datos parciales: McDonald's (6 zonas, Rappi+UE)
y OXXO inicial (12 filas). Se agregaron:
- Más datos OXXO (nuevas zonas, mejor cobertura)
- UberEats mejorado (más disponibilidad, mejor matching)
- Nuevas direcciones

Los gráficos del reporte son dinámicos (leen el CSV), pero el texto narrativo
("Lectura:", INSIGHTS, exec summary) tiene números hardcodeados que ya no reflejan
la nueva realidad.

---

## Objetivo

Actualizar `generate_report.py` para:
1. Separar el análisis en dos verticales: **Fast Food (McDonald's)** y **Retail (OXXO)**
2. Hacer dinámicos los números en el texto narrativo vía `compute_stats(df)`
3. Incorporar automáticamente todas las zonas que haya en el CSV
4. Mantener los 5 requisitos mínimos del brief para ambas verticales

---

## Estructura del reporte

```
Cover + Executive Summary
│  ├── Fast food: precio, ETA, fees, promos
│  └── Retail: disponibilidad, precio, promos

── FAST FOOD (McDonald's) ────────────────────────────
01  Posicionamiento de precios (barras: SKU × plataforma)
02  Tiempos de entrega — ETA (heatmap: zona × plataforma)
03  Estructura de fees (stacked bar: ticket composition)
04  Estrategia promocional (barra % + tabla textos)

── RETAIL (OXXO) ─────────────────────────────────────
05  Precios retail (barras: SKU × plataforma)
06  Disponibilidad por zona (heatmap: zona × plataforma, bool)
07  Fees retail (barra: delivery fee por plataforma)
08  Promos retail (barra % + tabla textos)

── ANÁLISIS CRUZADO ──────────────────────────────────
09  Variabilidad geográfica (ticket fast food por zona; tabla cobertura cross-vertical)

── CONCLUSIONES ──────────────────────────────────────
    Top 5 Insights Accionables (editorial hardcodeado)
    Limitaciones + próximos pasos
```

---

## compute_stats(df) — métricas calculadas dinámicamente

```python
stats = {
    # Fast food
    "ff_eta_rappi_min": ...,      # ETA mínimo Rappi (fast food)
    "ff_eta_rappi_max": ...,      # ETA máximo Rappi (fast food)
    "ff_eta_ue_min": ...,         # ETA mínimo UberEats
    "ff_eta_ue_max": ...,         # ETA máximo UberEats
    "ff_price_bigmac_rappi": ..., # Precio promedio Big Mac Rappi
    "ff_price_bigmac_ue": ...,    # Precio promedio Big Mac UE
    "ff_promo_pct_rappi": ...,    # % filas con promo Rappi (fast food)
    "ff_promo_pct_ue": ...,       # % filas con promo UE (fast food)
    "ff_delivery_fee_rappi": ..., # Delivery fee promedio Rappi (fast food)
    "ff_delivery_fee_ue": ...,    # Delivery fee promedio UE (fast food)
    "ff_discount_rappi": ...,     # Descuento promedio Rappi (fast food)

    # Retail
    "rt_avail_rappi": ...,        # Disponibles Rappi OXXO (n)
    "rt_total_rappi": ...,        # Total scraped Rappi OXXO
    "rt_avail_ue": ...,           # Disponibles UE OXXO (n)
    "rt_total_ue": ...,           # Total scraped UE OXXO
    "rt_price_coca_rappi": ...,   # Precio Coca-Cola Rappi (rango: min–max)
    "rt_promo_pct_rappi": ...,    # % filas con promo Rappi (retail)

    # Coverage
    "zones": [...],               # Lista de zonas con datos disponibles
    "n_total": ...,               # Total filas
    "n_available": ...,           # Filas available=True
    "snapshot_date": ...,         # Fecha del primer timestamp
}
```

---

## Gráficos nuevos (retail)

| ID | Tipo | Datos |
|----|------|-------|
| `chart-retail-prices` | Bar agrupado | avg unit_price por SKU retail × plataforma |
| `chart-retail-avail` | Heatmap booleano | disponibilidad (True/False) por zona × plataforma |
| `chart-retail-fees` | Bar simple | avg delivery_fee por plataforma (retail) |
| `chart-retail-promos` | Bar % | % has_promo por plataforma (retail) |

---

## Texto narrativo (Lectura) — usa variables de stats

Cada párrafo "Lectura:" en las secciones de fast food usa f-strings sobre el dict `stats`.

Ejemplo actual (hardcodeado):
```
"Uber Eats entrega entre 10 y 23 min; Rappi entre 14 y 49 min"
```

Ejemplo nuevo (dinámico):
```python
f"Uber Eats entrega entre {stats['ff_eta_ue_min']:.0f} y {stats['ff_eta_ue_max']:.0f} min; "
f"Rappi entre {stats['ff_eta_rappi_min']:.0f} y {stats['ff_eta_rappi_max']:.0f} min"
```

---

## INSIGHTS — actualización

Los 5 insights son editoriales (hardcodeados), pero los números dentro de `finding`
se sustituyen por variables del dict `stats`. La lógica editorial (impacto, recomendación)
no cambia.

Se revisa si los insights siguen siendo los 5 más relevantes con la nueva data
(especialmente insight 5 sobre OXXO, que ahora tiene más datos).

---

## Exec summary table

La tabla tiene 2 filas separadas para cada vertical:
- Fast food: precio, ETA, fees, promos
- Retail: disponibilidad, precio (donde haya datos)

Las descripciones de texto siguen siendo editoriales pero usan variables de stats
para los números concretos.

---

## Qué NO cambia

- CSS / estilos del reporte
- Sidebar navigation (se agregan items para nuevas secciones)
- Estructura base de `compose_html()`
- Gráficos existentes (fast food): siguen siendo dinámicos, solo se renombran/reordenan

---

## Archivos afectados

- `report/generate_report.py` — único archivo modificado
- `report/competitive_intelligence_2026.html` — regenerado (no es código fuente)
