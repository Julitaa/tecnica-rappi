"""Thresholds for detectors (tunable)."""
ANOMALY_PCT_CHANGE = 0.10           # >10% wow delta
TREND_MIN_STREAK = 3                # ≥3 consecutive weeks of deterioration
CORRELATION_MIN_ABS_R = 0.6
CORRELATION_MIN_N = 30
BENCHMARK_LOW_PCT = 10              # below p10 → flagged
BENCHMARK_HIGH_PCT = 90             # above p90 → flagged
TOP_K_TOTAL = 18                    # findings across categories
PER_CATEGORY_CAP = 5                # max per category
