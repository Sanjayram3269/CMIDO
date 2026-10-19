"""Run lineage, isolation and export for uploaded-data analyses.

Every successful run is recorded with a unique run identifier, the input-file
fingerprint (SHA-256 of the raw upload), the schema mapping, the validation
report, the run configuration and seed, execution timing and status, and the
output artifact locations.  Runs are written to an isolated workspace that is
*outside* the canonical ``results/`` tree, so uploaded-data outputs can never
overwrite canonical research artifacts.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: Default workspace root for uploaded-data runs (relative to the repo root).
#: Deliberately NOT under ``results/`` so canonical artifacts are untouched.
DEFAULT_RUN_ROOT = "results" + "/external_data_runs"

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

#: Maximum bytes for any single exported artifact.
MAX_EXPORT_BYTES = 50 * 1024 * 1024


def safe_filename(name: str, fallback: str = "upload") -> str:
    """Return a filesystem-safe basename with no path separators."""
    base = Path(str(name)).name
    cleaned = _SAFE_CHARS.sub("_", base).strip("._")
    return cleaned or fallback


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 hex digest of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


@dataclass
class RunRecord:
    """Lineage metadata for one uploaded-data run."""

    run_id: str
    analysis_key: str
    input_filename: str
    input_sha256: str
    input_size_bytes: int
    row_count: int
    column_count: int
    mapping: dict[str, str]
    validation: dict[str, Any]
    seed: int
    resamples: int
    provenance_class: str
    started_utc: str
    finished_utc: str = ""
    duration_seconds: float = 0.0
    status: str = "RUNNING"
    error: str = ""
    output_dir: str = ""
    outputs: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_run_id() -> str:
    """Return a short, unique, filesystem-safe run identifier."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{stamp}_{uuid.uuid4().hex[:8]}"


class RunStore:
    """Isolated, per-run workspace for uploaded-data analyses.

    The store is rooted outside ``results/`` (see :data:`DEFAULT_RUN_ROOT`) so
    that uploaded-data outputs never collide with canonical research artifacts.
    Each run lives in its own subdirectory keyed by ``run_id``.
    """

    def __init__(self, root: str | Path | None = None):
        if root is None:
            # Resolve relative to the current working directory (repo root).
            root = Path.cwd() / DEFAULT_RUN_ROOT
        self.root = Path(root)

    def run_dir(self, run_id: str) -> Path:
        return self.root / safe_filename(run_id, fallback="run")

    def ensure(self, run_id: str) -> Path:
        path = self.run_dir(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, run_id: str, name: str, payload: Any) -> str:
        """Write a JSON artifact into the run directory; return its path."""
        directory = self.ensure(run_id)
        target = directory / safe_filename(name, fallback="artifact.json")
        text = json.dumps(payload, indent=2, sort_keys=True, default=str)
        _guard_size(text)
        # newline="" writes the serialised text verbatim: on Windows the
        # default text-mode translation would otherwise rewrite every "\n"
        # into "\r\n" and turn a pandas "\r\n" into "\r\r\n", so the
        # persisted bytes would no longer match the exported payload.
        target.write_text(text, encoding="utf-8", newline="")
        return str(target)

    def write_text(self, run_id: str, name: str, text: str) -> str:
        directory = self.ensure(run_id)
        target = directory / safe_filename(name, fallback="artifact.txt")
        _guard_size(text)
        target.write_text(text, encoding="utf-8", newline="")
        return str(target)

    def write_csv(self, run_id: str, name: str, rows: list[dict[str, Any]]) -> str:
        import pandas as pd

        directory = self.ensure(run_id)
        target = directory / safe_filename(name, fallback="artifact.csv")
        frame = pd.DataFrame(rows)
        # lineterminator is pinned to "\n" so the persisted table is identical
        # on every platform and byte-identical to the download the page offers.
        csv_text = frame.to_csv(index=False, lineterminator="\n")
        _guard_size(csv_text)
        target.write_text(csv_text, encoding="utf-8", newline="")
        return str(target)

    def list_runs(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())

    def read_run_record(self, run_id: str) -> dict[str, Any] | None:
        path = self.run_dir(run_id) / "run_record.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None


def _guard_size(text: str) -> None:
    if len(text.encode("utf-8")) > MAX_EXPORT_BYTES:
        raise ValueError(
            f"An export exceeded the {MAX_EXPORT_BYTES:,}-byte limit; the run "
            "result is too large to persist."
        )


def start_record(
    *,
    analysis_key: str,
    input_filename: str,
    payload: bytes,
    row_count: int,
    column_count: int,
    mapping: dict[str, str],
    validation: dict[str, Any],
    seed: int,
    resamples: int,
    provenance_class: str,
) -> RunRecord:
    """Create a :class:`RunRecord` with the start timestamp set."""
    return RunRecord(
        run_id=new_run_id(),
        analysis_key=analysis_key,
        input_filename=safe_filename(input_filename),
        input_sha256=sha256_bytes(payload),
        input_size_bytes=len(payload),
        row_count=row_count,
        column_count=column_count,
        mapping=dict(mapping),
        validation=validation,
        seed=seed,
        resamples=resamples,
        provenance_class=provenance_class,
        started_utc=datetime.now(timezone.utc).isoformat(),
    )


def finish_record(record: RunRecord, started_monotonic: float, *, ok: bool, error: str = "") -> None:
    """Stamp the finish time, duration and status onto ``record``."""
    record.finished_utc = datetime.now(timezone.utc).isoformat()
    record.duration_seconds = round(time.monotonic() - started_monotonic, 4)
    record.status = "SUCCEEDED" if ok else "FAILED"
    record.error = error
