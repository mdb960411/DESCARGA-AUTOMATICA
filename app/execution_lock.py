from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass
class ExecutionLock:
    path: Path
    owner: str

    @classmethod
    def acquire(cls, base_dir, ttl_seconds):
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / ".gmail-downloader-execution.lock"

        for _ in range(2):
            owner = uuid4().hex
            try:
                descriptor = os.open(
                    path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                try:
                    age = time.time() - path.stat().st_mtime
                except OSError:
                    return None
                if age <= ttl_seconds:
                    return None
                try:
                    path.unlink()
                except OSError:
                    return None
                continue

            try:
                payload = json.dumps(
                    {
                        "owner": owner,
                        "createdAt": int(time.time()),
                    }
                ).encode("utf-8")
                os.write(descriptor, payload)
            except Exception:
                try:
                    path.unlink()
                except OSError:
                    pass
                raise
            finally:
                os.close(descriptor)
            return cls(path=path, owner=owner)

        return None

    def release(self):
        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return

        if payload.get("owner") != self.owner:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
