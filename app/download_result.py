from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DownloadResult:
    """
    Resultado normalizado de un enlace.

    Un enlace puede entregar más de un archivo (por ejemplo, SendAllFiles) y
    también puede terminar parcialmente: algunos archivos correctos y otros
    fallidos.
    """

    paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_value(cls, value, default_error):
        if isinstance(value, cls):
            if not value.paths and not value.errors:
                value.errors.append(default_error)
            return value

        if value is None:
            return cls(errors=[default_error])

        if isinstance(value, (list, tuple, set)):
            paths = [Path(item) for item in value if item is not None]
            return cls(
                paths=paths,
                errors=[] if paths else [default_error],
            )

        return cls(paths=[Path(value)])
