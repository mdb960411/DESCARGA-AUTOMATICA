from __future__ import annotations

import fcntl
import shutil
from datetime import datetime, timezone
from pathlib import Path


class ExecutionLock:
    """Bloqueo exclusivo para impedir dos trabajadores simultáneos."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._handle = None
        self.acquired = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(
                self._handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            self._handle.close()
            self._handle = None
            return False

        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(
            datetime.now(timezone.utc).isoformat(timespec="seconds")
        )
        self._handle.flush()
        self.acquired = True
        return True

    def __exit__(self, exc_type, exc_value, traceback):
        if self._handle is not None:
            if self.acquired:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
        self._handle = None
        self.acquired = False


def cleanup_stale_runs(download_dir: Path, max_age_hours: int):
    """Elimina únicamente carpetas run_* abandonadas por una caída anterior."""

    if max_age_hours <= 0 or not download_dir.exists():
        return 0

    threshold = datetime.now(timezone.utc).timestamp() - (
        max_age_hours * 3600
    )
    removed = 0
    for candidate in download_dir.glob("run_*"):
        try:
            if candidate.is_dir() and candidate.stat().st_mtime < threshold:
                shutil.rmtree(candidate)
                removed += 1
        except OSError:
            continue
    return removed
