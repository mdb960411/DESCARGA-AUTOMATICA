from __future__ import annotations

import hashlib
from pathlib import Path


def source_file_key(filename):
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()[:32]


def file_md5(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.md5(usedforsecurity=False)
    with Path(path).open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_content_duplicate(path, candidates):
    path = Path(path)
    local_size = path.stat().st_size
    same_size = [
        candidate
        for candidate in candidates
        if candidate.get("size")
        and int(candidate["size"]) == local_size
        and candidate.get("md5Checksum")
    ]
    if not same_size:
        return None

    local_md5 = file_md5(path)
    for candidate in same_size:
        if candidate["md5Checksum"].lower() == local_md5:
            return candidate
    return None
