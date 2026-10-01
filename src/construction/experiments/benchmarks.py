from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    """A deterministic benchmark case for evaluating CMIDO engines."""

    case_id: str
    description: str
    expected_duration_days: int
    expected_critical_path: tuple[str, ...]
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected_critical_path"] = list(self.expected_critical_path)
        data["tags"] = list(self.tags)
        return data


BENCHMARK_CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        case_id="baseline_cmido_demo",
        description="Baseline CMIDO demonstration project.",
        expected_duration_days=74,
        expected_critical_path=(
            "A001", "A002", "A003", "A004", "A006",
            "A007", "A008", "A009", "A011",
        ),
        tags=("baseline", "cpm", "regression"),
    ),
)


def get_benchmark_cases() -> list[dict[str, Any]]:
    """Return benchmark cases as plain dictionaries."""
    return [case.to_dict() for case in BENCHMARK_CASES]


def get_benchmark_case(case_id: str) -> dict[str, Any]:
    """Return one benchmark case or raise ValueError."""
    for case in BENCHMARK_CASES:
        if case.case_id == case_id:
            return case.to_dict()
    raise ValueError(f"Unknown benchmark case: {case_id}")
