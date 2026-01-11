from __future__ import annotations
import io
import logging
import os
import json
from dataclasses import dataclass
from typing import Optional, List, Tuple

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import numpy as np
except Exception:
    np = None

from .utils import read_bytes

UNIQUE_MARKER = b"::STEGA_PAYLOAD_START::"
META_LEN_BYTES = 4

CHANNEL_PRESETS = {
    'none': {},
    'whatsapp': {
        'jpeg_quality': 85,
        'rate_bpnz': 0.04
    },
    'telegram': {
        'jpeg_quality': 90,
        'rate_bpnz': 0.05
    }
}

@dataclass
class EmbedResult:
    stego_bytes: bytes
    metadata: dict


class CodecBase:
    name: str = "base"
    def embed(self, cover_path: str, payload: bytes, rate: Optional[float], channel: str) -> EmbedResult:
        raise NotImplementedError
    def extract(self, stego_path: str, meta: dict) -> bytes:
        raise NotImplementedError


class AppendCodec(CodecBase):
    name = 'append'
    def embed(self, cover_path: str, payload: bytes, rate: Optional[float], channel: str) -> EmbedResult:
        if not os.path.isfile(cover_path):
            raise FileNotFoundError(cover_path)
        cover = read_bytes(cover_path)
        meta = {
            'mode': self.name
        }
        stego = cover + UNIQUE_MARKER + len(json.dumps(meta).encode()).to_bytes(META_LEN_BYTES, 'big') + json.dumps(meta).encode() + payload
        return EmbedResult(stego, meta)

    def extract(self, stego_path: str, meta: dict) -> bytes:
        raise NotImplementedError('AppendCodec uses generic extractor by marker. No direct extract.')


class DctCodec(CodecBase):
    name = 'dct'

    @staticmethod
    def _check_deps():
        if Image is None or np is None:
            raise RuntimeError('Pillow and numpy are required for dct mode. pip install pillow numpy')

    @staticmethod
    def _to_blocks(arr: np.ndarray) -> np.ndarray:
        H, W = arr.shape
        h = (H // 8) * 8
        w = (W // 8) * 8
        arr = arr[:h, :w]
        blocks = arr.reshape(h//8, 8, w//8, 8).swapaxes(1,2)
        return blocks

    @staticmethod
    def _from_blocks(blocks: np.ndarray, H: int, W: int) -> np.ndarray:
        nbh, nbw, _, _ = blocks.shape
        arr = blocks.swapaxes(1,2).reshape(nbh*8, nbw*8)
        return arr[:H, :W]

    @staticmethod
    def _dct2(block: np.ndarray) -> np.ndarray:
        return DctCodec._dct1(DctCodec._dct1(block.T).T)

    @staticmethod
    def _idct2(block: np.ndarray) -> np.ndarray:
        return DctCodec._idct1(DctCodec._idct1(block.T).T)

    @staticmethod
    def _dct1(x: np.ndarray) -> np.ndarray:
        N = x.shape[0]
        X = np.zeros_like(x, dtype=np.float64)
        alpha = np.sqrt(2.0/N)
        c0 = np.sqrt(1.0/N)
        k = np.arange(N)
        for n in range(N):
            X[0, n] = c0 * np.sum(x[:, n])
        for u in range(1, N):
            cu = alpha
            for n in range(N):
                X[u, n] = cu * np.sum(x[:, n] * np.cos((np.pi*(2*np.arange(N)+1)*u)/(2*N)))
        return X

    @staticmethod
    def _idct1(X: np.ndarray) -> np.ndarray:
        N = X.shape[0]
        x = np.zeros_like(X, dtype=np.float64)
        alpha = np.sqrt(2.0/N)
        c0 = np.sqrt(1.0/N)
        for n in range(N):
            x[n, :] = c0 * X[0, :]
        for u in range(1, N):
            x += alpha * np.cos((np.pi*(2*np.arange(N)+1)[:, None]*u)/(2*N)) * X[u, :]
        return x

    @staticmethod
    def _cost_map(y_blocks_dct: np.ndarray) -> np.ndarray:
        mag = np.abs(y_blocks_dct)
        mask = np.ones((8,8), dtype=np.float64)
        mask[0,0] = 1e9
        cost = mask / (1 + mag)
        return cost

    @staticmethod
    def _select_positions(cost: np.ndarray, rate_bpnz: float) -> List[Tuple[int,int,int,int]]:
        nbh, nbw, _, _ = cost.shape
        candidates: List[Tuple[float, Tuple[int,int,int,int]]] = []
        for bi in range(nbh):
            for bj in range(nbw):
                for u in range(8):
                    for v in range(8):
                        if u == 0 and v == 0:
                            continue
                        candidates.append((cost[bi,bj,u,v], (bi,bj,u,v)))
        candidates.sort(key=lambda x: x[0])
        nz_est = sum(1 for _, pos in candidates)
        target = int(rate_bpnz * nz_est)
        target = max(1, target)
        return [pos for _, pos in candidates[:target]]

    def embed(self, cover_path: str, payload: bytes, rate: Optional[float], channel: str) -> EmbedResult:
        self._check_deps()
        if not os.path.isfile(cover_path):
            raise FileNotFoundError(cover_path)
        img = Image.open(cover_path).convert('YCbCr')
        W, H = img.size
        y, cb, cr = img.split()
        y_np = np.asarray(y, dtype=np.float64)
        H8 = (H//8)*8
        W8 = (W//8)*8
        y_c = y_np[:H8, :W8] - 128.0
        yb = self._to_blocks(y_c)
        yb_dct = yb.copy()
        for i in range(yb.shape[0]):
            for j in range(yb.shape[1]):
                yb_dct[i,j] = self._dct2(yb[i,j])
        cost = self._cost_map(yb_dct)
        preset = CHANNEL_PRESETS.get(channel or 'none', {})
        rate_bpnz = float(preset.get('rate_bpnz', 0.04 if rate is None else rate))
        bits = np.frombuffer(payload, dtype=np.uint8)
        bits = np.unpackbits(bits)
        pos_list = self._select_positions(cost, rate_bpnz)
        total = min(len(pos_list), len(bits))
        if total == 0:
            raise RuntimeError('No embedding positions selected. Try increasing rate or using a more textured cover.')
        embed_count = 0
        for k in range(total):
            bi,bj,u,v = pos_list[k]
            c = yb_dct[bi,bj,u,v]
            q = np.round(c)
            bit = bits[k]
            if int(q) & 1 != int(bit):
                if q >= 0:
                    q += 1
                else:
                    q -= 1
            yb_dct[bi,bj,u,v] = q
            embed_count += 1
        yb_rec = yb_dct.copy()
        for i in range(yb_rec.shape[0]):
            for j in range(yb_rec.shape[1]):
                yb_rec[i,j] = self._idct2(yb_dct[i,j])
        y_rec = self._from_blocks(yb_rec, H8, W8) + 128.0
        y_out = y_np.copy()
        y_out[:H8, :W8] = np.clip(np.round(y_rec), 0, 255)
        y_img = Image.fromarray(y_out.astype('uint8'))
        stego = Image.merge('YCbCr', (y_img, cb, cr)).convert('RGB')
        out_buf = io.BytesIO()
        quality = int(preset.get('jpeg_quality', 95))
        stego.save(out_buf, format='JPEG', quality=quality, subsampling=0, optimize=True)
        stego_bytes = out_buf.getvalue()
        meta = {
            'mode': self.name,
            'rate_bpnz': rate_bpnz,
            'jpeg_quality': quality,
            'width': W,
            'height': H,
            'embedded_bits': int(total)
        }
        logging.info(f"DCT embedded bits={total} jpeg_quality={quality} rate_bpnz={rate_bpnz}")
        return EmbedResult(stego_bytes, meta)

    def extract(self, stego_path: str, meta: dict) -> bytes:
        self._check_deps()
        img = Image.open(stego_path).convert('YCbCr')
        W, H = img.size
        y, cb, cr = img.split()
        y_np = np.asarray(y, dtype=np.float64)
        H8 = (H//8)*8
        W8 = (W//8)*8
        y_c = y_np[:H8, :W8] - 128.0
        yb = self._to_blocks(y_c)
        yb_dct = yb.copy()
        for i in range(yb.shape[0]):
            for j in range(yb.shape[1]):
                yb_dct[i,j] = self._dct2(yb[i,j])
        cost = self._cost_map(yb_dct)
        rate_bpnz = float(meta.get('rate_bpnz', 0.04))
        pos_list = self._select_positions(cost, rate_bpnz)
        total = int(meta.get('embedded_bits', len(pos_list)))
        total = min(total, len(pos_list))
        bits = []
        for k in range(total):
            bi,bj,u,v = pos_list[k]
            q = int(np.round(yb_dct[bi,bj,u,v]))
            bits.append(q & 1)
        if not bits:
            return b''
        arr = np.array(bits, dtype=np.uint8)
        pad = (-len(arr)) % 8
        if pad:
            arr = np.concatenate([arr, np.zeros(pad, dtype=np.uint8)])
        out = np.packbits(arr).tobytes()
        return out
