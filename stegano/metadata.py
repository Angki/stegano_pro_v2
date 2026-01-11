from __future__ import annotations
import json
import os
from .utils import sha256_hex

VERSION = "2.0.0"

def build_meta(filename: str, comp_payload: bytes, comp_method: str, is_archive: bool, mode: str, extra: dict) -> bytes:
    meta = {
        'filename': os.path.basename(filename),
        'size': len(comp_payload),
        'method': comp_method,
        'sha256': sha256_hex(comp_payload),
        'is_archive': is_archive,
        'archive_format': 'tar' if is_archive else None,
        'version': VERSION,
        'mode': mode,
    }
    meta.update(extra or {})
    return json.dumps(meta, ensure_ascii=False).encode('utf-8')
