"""Safe parsing of uploaded CSV/JSON tables.

No uploaded code is executed.  Files are size-limited before they are read,
parsed with the standard library / pandas text readers only, and rejected with
a readable error if the format is unsupported, malformed, or exceeds the row /
column guards.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .contracts import MAX_COLUMNS, MAX_ROWS, MAX_UPLOAD_BYTES, SUPPORTED_EXTENSIONS


class ParseError(ValueError):
    """A readable, user-facing parsing failure. Never exposes a server path."""


@dataclass
class ParsedTable:
    """A parsed upload plus the metadata needed for preview and profiling."""

    frame: pd.DataFrame
    filename: str
    file_format: str  # "csv" | "json"
    size_bytes: int

    @property
    def shape(self) -> tuple[int, int]:
        return self.frame.shape


def _extension(filename: str) -> str:
    name = (filename or "").strip().lower()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1]


def _check_size(size_bytes: int) -> None:
    if size_bytes <= 0:
        raise ParseError("The uploaded file is empty.")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise ParseError(
            f"The file is {size_bytes:,} bytes, which exceeds the "
            f"{MAX_UPLOAD_BYTES:,}-byte upload limit."
        )


def _guard_shape(frame: pd.DataFrame) -> pd.DataFrame:
    rows, cols = frame.shape
    if cols == 0:
        raise ParseError("The table has no columns.")
    if cols > MAX_COLUMNS:
        raise ParseError(
            f"The table has {cols} columns, which exceeds the {MAX_COLUMNS}-column limit."
        )
    if rows > MAX_ROWS:
        raise ParseError(
            f"The table has {rows:,} rows, which exceeds the {MAX_ROWS:,}-row limit."
        )
    return frame


def _parse_csv(payload: bytes) -> pd.DataFrame:
    try:
        frame = pd.read_csv(io.BytesIO(payload))
    except Exception as exc:  # noqa: BLE001 - normalised to a readable error
        raise ParseError(f"Could not parse the CSV file: {exc}") from exc
    return frame


def _parse_json(payload: bytes) -> pd.DataFrame:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParseError("The JSON file is not valid UTF-8 text.") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Could not parse the JSON file: {exc.msg}") from exc

    if isinstance(data, list):
        if not data:
            raise ParseError("The JSON array is empty.")
        if not all(isinstance(row, dict) for row in data):
            raise ParseError(
                "A JSON array must contain objects (one object per row)."
            )
        return pd.DataFrame(data)
    if isinstance(data, dict):
        # Accept a single record object, or a {column: [values]} mapping.
        if all(isinstance(v, list) for v in data.values()) and data:
            try:
                return pd.DataFrame(data)
            except Exception as exc:  # noqa: BLE001
                raise ParseError(
                    "The JSON column mapping has inconsistent column lengths."
                ) from exc
        if data:
            return pd.DataFrame([data])
        raise ParseError("The JSON object has no fields.")
    raise ParseError("The JSON top level must be an array of objects or an object.")


def parse_upload(filename: str, payload: bytes) -> ParsedTable:
    """Parse an uploaded file into a :class:`ParsedTable`.

    Raises :class:`ParseError` with a user-readable message on any failure.
    Never executes uploaded code and never echoes a server filesystem path.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise ParseError("The uploaded payload is not binary data.")
    payload = bytes(payload)
    _check_size(len(payload))

    ext = _extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ParseError(
            f"Unsupported file type '.{ext or '?'}'. "
            f"Accepted types: {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    if ext == "csv":
        frame = _parse_csv(payload)
    else:
        frame = _parse_json(payload)

    frame = _guard_shape(frame)
    return ParsedTable(
        frame=frame,
        filename=filename,
        file_format=ext,
        size_bytes=len(payload),
    )
