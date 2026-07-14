"""
Structured, exportable audit log.

Every signal (clean or not) is written as a structured JSON record — the
"Immune Signal event" shape from docs/architecture.md, section 5. In a real
deployment this would ship to a SIEM; here it's kept in memory and dumped
to a .jsonl file, which is the same shape a downstream tool would receive.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone


class AuditLog:
    def __init__(self):
        self.records: list[dict] = []

    def log(self, **fields) -> dict:
        record = {
            "signal_id": f"SIG-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self.records.append(record)
        return record

    def save(self, path: str) -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            for record in self.records:
                f.write(json.dumps(record) + "\n")
