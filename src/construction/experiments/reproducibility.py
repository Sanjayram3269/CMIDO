from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(payload: Any) -> str:
    """Return a stable SHA-256 fingerprint for experiment metadata."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_metadata(
    experiment_id: str,
    seed: int,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic metadata identifying one experiment setup."""
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id must be a non-empty string")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")

    fingerprint = stable_hash(
        {
            "experiment_id": experiment_id,
            "seed": seed,
            "parameters": parameters,
        }
    )

    return {
        "experiment_id": experiment_id,
        "seed": seed,
        "parameters": dict(parameters),
        "configuration_fingerprint": fingerprint,
    }
