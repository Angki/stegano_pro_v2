from __future__ import annotations
import zlib
import logging
from typing import Tuple, Dict, List

# simple custom LZ78 for demonstration, not a standard format
LZ78_SIG = b'LZ78\x00'

def lz78_compress(data: bytes) -> bytes:
    d: Dict[bytes, int] = {}
    idx = 1
    w = b''
    out = bytearray(LZ78_SIG)
    def emit(i: int, sym: int):
        out.extend(i.to_bytes(4, 'big'))
        out.append(sym)
    for c in data:
        wc = w + bytes([c])
        if wc in d:
            w = wc
        else:
            emit(d.get(w, 0), c)
            d[wc] = idx
            idx += 1
            w = b''
    if w:
        emit(d.get(w, 0), 0)
    return bytes(out)


def lz78_decompress(comp: bytes) -> bytes:
    if not comp.startswith(LZ78_SIG):
        raise ValueError('Invalid LZ78 signature')
    pos = len(LZ78_SIG)
    dict_list: List[bytes] = [b'']
    out = bytearray()
    while pos + 5 <= len(comp):
        i = int.from_bytes(comp[pos:pos+4], 'big'); pos += 4
        sym = comp[pos]; pos += 1
        if i >= len(dict_list):
            raise ValueError('Corrupt LZ78 stream')
        seq = dict_list[i]
        if sym != 0:
            entry = seq + bytes([sym])
            out += entry
            dict_list.append(entry)
        else:
            out += seq
            dict_list.append(seq)
    return bytes(out)


class AdaptiveCompressor:
    @staticmethod
    def compress_auto(data: bytes) -> Tuple[bytes, str, float]:
        # LZ77
        lz77 = zlib.compress(data, level=zlib.Z_BEST_COMPRESSION)
        # LZ78
        try:
            lz78 = lz78_compress(data)
        except Exception as e:
            logging.warning(f"LZ78 compression error: {e}")
            lz78 = b'\x00'
        size77 = len(lz77)
        size78 = len(lz78)
        choose = 'lz77' if size77 <= size78 else 'lz78'
        chosen = lz77 if choose == 'lz77' else lz78
        ratio = 0.0
        if len(data):
            ratio = (1 - len(chosen) / len(data)) * 100.0
        logging.info(f"Compression chosen={choose} ratio={ratio:.2f}% sizes orig={len(data)} lz77={size77} lz78={size78}")
        return chosen, choose, ratio

    @staticmethod
    def decompress(comp: bytes, method: str) -> bytes:
        if method == 'lz77':
            return zlib.decompress(comp)
        if method == 'lz78':
            return lz78_decompress(comp)
        raise ValueError(f"Unknown method {method}")
