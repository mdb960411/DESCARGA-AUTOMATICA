from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class RetryState:
    """Contador pequeño y persistente de intentos por mensaje de Gmail."""

    def __init__(self, state_dir: Path):
        self.path = Path(state_dir) / "message-retries.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def increment(self, message_id):
        current = self.count(message_id) + 1
        self._data[str(message_id)] = {
            "attempts": current,
            "updated_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
        }
        self._save()
        return current

    def count(self, message_id):
        value = self._data.get(str(message_id), {})
        try:
            return max(0, int(value.get("attempts", 0)))
        except (TypeError, ValueError, AttributeError):
            return 0

    def clear(self, message_id):
        if self._data.pop(str(message_id), None) is not None:
            self._save()
