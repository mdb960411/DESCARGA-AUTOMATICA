import base64, re
from pathlib import Path
from urllib.parse import unquote

def decode_base64url(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))

def safe_filename(name):
    clean = unquote(name or "").strip()
    clean = re.sub(r'[\\/*?:"<>|]+', "_", clean).replace("\r", "").replace("\n", "")
    return clean[:180] or "archivo"

def unique_path(path):
    if not path.exists():
        return path
    for i in range(2, 10000):
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("No fue posible generar nombre único")

def extension_allowed(filename, allowed):
    return not allowed or Path(filename).suffix.lower() in allowed
