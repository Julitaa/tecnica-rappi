from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Literal

Category = Literal["anomaly", "trend", "benchmark", "correlation", "opportunity"]


@dataclass
class Finding:
    category: Category
    severity: float
    metric: str
    headline: str
    zone: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
