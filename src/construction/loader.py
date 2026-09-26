from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_project_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Project file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Project file must contain a JSON object")

    return data
