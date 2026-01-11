from __future__ import annotations
import hashlib
import os
import logging

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def safe_write(path: str, data: bytes):
    ensure_dir(path)
    with open(path, 'wb') as f:
        f.write(data)


def read_bytes(path: str) -> bytes:
    with open(path, 'rb') as f:
        return f.read()


def is_image_ext(path: str) -> bool:
    ext = os.path.splitext(path.lower())[1]
    return ext in {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}

def setup_logging(verbosity: int):
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format='%(asctime)s - [%(levelname)s] - %(message)s')
