"""Parse sample records from uploaded CSV/JSON bytes (shared by analyze & schema routes)."""

import csv
import io
import json
from typing import Any, List


def load_records_from_bytes(content: bytes, filename: str) -> List[dict[str, Any]]:
    """Load list of record dicts from CSV or JSON file content.

    Raises:
        ValueError: Unsupported format or invalid structure.
    """
    lower = filename.lower()
    content_str = content.decode("utf-8")

    if lower.endswith(".json"):
        data = json.loads(content_str)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        raise ValueError("JSON must be an array of objects or a single object")

    if lower.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(content_str))
        return list(reader)

    raise ValueError("Unsupported file format. Use .json or .csv")
