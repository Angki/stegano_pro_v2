from __future__ import annotations
import argparse
import logging
import os
import sys
from typing import List, Optional, Tuple

from stegano import core, codecs, utils
from stegano.compression import AdaptiveCompressor
from stegano.crypto import maybe_encrypt
from stegano.metadata import build_meta
from stegano.utils import is_image_ext, safe_write, ensure_dir

try:
    from PIL import Image
    import numpy as np
except ImportError:
    Image = None
    np = None

EXIT_OK = 0
EXIT_ARG = 2
EXIT_RUNTIME = 3

def psnr_rmse(cover_path: str, stego_path: str) -> Tuple[float, float]:
    if Image is None or np is None:
        raise RuntimeError('Pillow and numpy required for metrics. pip install pillow numpy')
    c = Image.open(cover_path).convert('RGB')
    s = Image.open(stego_path).convert('RGB')
    c = np.asarray(c, dtype=np.float64)
    s = np.asarray(s, dtype=np.float64)
    if c.shape != s.shape:
        raise ValueError('Cover and stego resolution mismatch')
    mse = np.mean((c - s) ** 2)
    if mse == 0:
        return float('inf'), 0.0
    psnr = 10.0 * np.log10((255.0**2) / mse)
    rmse = float(np.sqrt(mse))
    return float(psnr), rmse

def metrics_pipeline(args) -> int:
    try:
        ps, rm = psnr_rmse(args.cover, args.stego)
    except Exception as e:
        logging.error(f'Metrics error: {e}')
        return EXIT_RUNTIME
    print(f'PSNR: {ps:.4f} dB')
    print(f'RMSE: {rm:.4f}')
    return EXIT_OK


def bench_pipeline(args) -> int:
    if Image is None or np is None:
        logging.error('Pillow and numpy required for bench')
        return EXIT_RUNTIME
    covers = []
    for root, _, files in os.walk(args.covers):
        for f in files:
            p = os.path.join(root, f)
            if is_image_ext(p):
                covers.append(p)
    if not covers:
        logging.error('No covers found')
        return EXIT_ARG

    payload_raw, original_name, is_archive = core.load_payload(args.payload)
    comp_payload, comp_method, ratio = AdaptiveCompressor.compress_auto(payload_raw)
    if args.encrypt:
        comp_payload, _ = maybe_encrypt(comp_payload, True, args.pass_env, args.password)

    channel = args.channel or 'none'
    codec: codecs.CodecBase
    if args.mode == 'append':
        codec = codecs.AppendCodec()
    elif args.mode == 'dct':
        codec = codecs.DctCodec()
    else:
        logging.error(f'Unknown mode {args.mode}')
        return EXIT_ARG

    rows = ["cover,psnr,rmse,notes\n"]
    for cpath in covers:
        try:
            if args.mode == 'append':
                cover_bytes = utils.read_bytes(cpath)
                meta = {'mode':'append'}
                meta_buf = build_meta(original_name, comp_payload, comp_method, is_archive, 'append', {'codec_meta': meta, 'enc': args.encrypt})
                stego_bytes = cover_bytes + codecs.UNIQUE_MARKER + len(meta_buf).to_bytes(codecs.META_LEN_BYTES,'big') + meta_buf + comp_payload
                tmp_stego = cpath + '.stego.jpg'
                safe_write(tmp_stego, stego_bytes)
            else:
                er = codec.embed(cpath, comp_payload, rate=args.rate, channel=channel)
                tmp_stego = cpath + '.stego.jpg'
                safe_write(tmp_stego, er.stego_bytes)

            ps, rm = psnr_rmse(cpath, tmp_stego)
            rows.append(f"{cpath},{ps:.4f},{rm:.4f},ok\n")
        except Exception as e:
            logging.warning(f'Bench failed on {cpath}: {e}')
            rows.append(f"{cpath},,,'fail {str(e).replace(',', ' ')}'\n")

    if args.report:
        ensure_dir(args.report)
        with open(args.report, 'w', encoding='utf-8') as f:
            f.writelines(rows)
        print(f"Saved report to {args.report}")
    else:
        print(''.join(rows))
    return EXIT_OK

def build_cli():
    p = argparse.ArgumentParser(description='Steganography Suite with append and DCT modes.')
    p.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity -v or -vv')
    sub = p.add_subparsers(dest='cmd', required=True)

    pe = sub.add_parser('embed', help='Embed payload into cover')
    pe.add_argument('-m', '--mode', choices=['append','dct'], required=True)
    pe.add_argument('-c', '--container', required=True)
    pe.add_argument('-p', '--payload', required=True)
    pe.add_argument('-o', '--output', required=True)
    pe.add_argument('--rate', type=float, default=None, help='Rate control for DCT mode in bits per non-zero AC estimate')
    pe.add_argument('--channel', choices=list(codecs.CHANNEL_PRESETS.keys()), default='none')
    pe.add_argument('--encrypt', action='store_true', help='Encrypt payload with AES-256-GCM')
    pe.add_argument('--password', type=str, default=None, help='Password string for key derivation')
    pe.add_argument('--pass-env', type=str, default=None, help='Env var to read password')

    px = sub.add_parser('extract', help='Extract payload from stego')
    px.add_argument('-s', '--stego-image', required=True)
    px.add_argument('-o', '--output-dir', required=True)
    px.add_argument('--password', type=str, default=None)
    px.add_argument('--pass-env', type=str, default=None)

    pm = sub.add_parser('metrics', help='Compute PSNR and RMSE')
    pm.add_argument('--cover', required=True)
    pm.add_argument('--stego', required=True)

    pb = sub.add_parser('bench', help='Batch embed metrics over a folder of covers')
    pb.add_argument('--covers', required=True)
    pb.add_argument('--payload', required=True)
    pb.add_argument('-m', '--mode', choices=['append','dct'], required=True)
    pb.add_argument('--rate', type=float, default=None)
    pb.add_argument('--channel', choices=list(codecs.CHANNEL_PRESETS.keys()), default='none')
    pb.add_argument('--encrypt', action='store_true')
    pb.add_argument('--password', type=str, default=None)
    pb.add_argument('--pass-env', type=str, default=None)
    pb.add_argument('--report', type=str, default=None)

    return p

def main(argv: Optional[List[str]] = None) -> int:
    cli = build_cli()
    args = cli.parse_args(argv)
    utils.setup_logging(args.verbose)

    try:
        if args.cmd == 'embed':
            return core.embed_pipeline(args)
        if args.cmd == 'extract':
            return core.extract_pipeline(args)
        if args.cmd == 'metrics':
            return metrics_pipeline(args)
        if args.cmd == 'bench':
            return bench_pipeline(args)
        logging.error('Unknown command')
        return EXIT_ARG
    except KeyboardInterrupt:
        logging.error('Interrupted')
        return EXIT_RUNTIME

if __name__ == '__main__':
    sys.exit(main())
