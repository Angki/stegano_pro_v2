from __future__ import annotations
import io
import json
import logging
import os
import tarfile
from typing import Tuple, Optional

from . import codecs
from .compression import AdaptiveCompressor
from .crypto import maybe_encrypt, maybe_decrypt
from .metadata import build_meta
from .utils import read_bytes, safe_write, sha256_hex, is_image_ext

EXIT_OK = 0
EXIT_ARG = 2
EXIT_RUNTIME = 3
EXIT_IO = 4
EXIT_INTEGRITY = 5

def tar_from_dir(dir_path: str, arcname: Optional[str] = None) -> bytes:
    buf = io.BytesIO()
    root = arcname if arcname else os.path.basename(os.path.normpath(dir_path))
    with tarfile.open(fileobj=buf, mode='w') as tf:
        tf.add(dir_path, arcname=root, recursive=True)
    return buf.getvalue()

def load_payload(path: str) -> Tuple[bytes, str, bool]:
    if os.path.isdir(path):
        logging.info('Payload is a directory. Creating TAR archive...')
        tarb = tar_from_dir(path)
        return tarb, os.path.basename(os.path.normpath(path)) + '.tar', True
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    return read_bytes(path), os.path.basename(path), False

def embed_pipeline(args) -> int:
    if not os.path.isfile(args.container):
        logging.error(f'Container not found: {args.container}')
        return EXIT_IO
    if not is_image_ext(args.container):
        logging.warning('Container file extension not typical image. Proceeding anyway.')

    payload_raw, original_name, is_archive = load_payload(args.payload)

    comp_payload, comp_method, ratio = AdaptiveCompressor.compress_auto(payload_raw)

    try:
        comp_payload_enc, enc_method = maybe_encrypt(
            comp_payload,
            use_enc=args.encrypt,
            pass_env=args.pass_env,
            pass_str=args.password
        )
    except Exception as e:
        logging.error(f'Encryption error: {e}')
        return EXIT_RUNTIME

    channel = args.channel or 'none'
    if args.mode == 'append':
        codec: codecs.CodecBase = codecs.AppendCodec()
    elif args.mode == 'dct':
        codec = codecs.DctCodec()
    else:
        logging.error(f'Unknown mode {args.mode}')
        return EXIT_ARG

    try:
        result = codec.embed(args.container, comp_payload_enc, rate=args.rate, channel=channel)
    except Exception as e:
        logging.error(f'Embed error: {e}')
        return EXIT_RUNTIME

    extra = {
        'codec_meta': result.metadata,
        'enc': enc_method,
        'comp': comp_method,
        'comp_ratio': ratio,
    }
    meta_buf = build_meta(original_name, comp_payload_enc, comp_method, is_archive, args.mode, extra)
    meta_len = len(meta_buf)
    meta_len_b = meta_len.to_bytes(codecs.META_LEN_BYTES, 'big')

    if args.mode == 'append':
        cover_bytes = read_bytes(args.container)
        stego_bytes = cover_bytes + codecs.UNIQUE_MARKER + meta_len_b + meta_buf + comp_payload_enc
    else:
        stego_bytes = result.stego_bytes + codecs.UNIQUE_MARKER + meta_len_b + meta_buf + comp_payload_enc

    try:
        safe_write(args.output, stego_bytes)
        logging.info(f'Wrote stego to {args.output} size={len(stego_bytes)}')
    except Exception as e:
        logging.error(f'Write error: {e}')
        return EXIT_IO

    return EXIT_OK


def extract_pipeline(args) -> int:
    if not os.path.isfile(args.stego_image):
        logging.error(f'Stego not found: {args.stego_image}')
        return EXIT_IO
    blob = read_bytes(args.stego_image)
    mpos = blob.rfind(codecs.UNIQUE_MARKER)
    if mpos == -1:
        logging.error('Marker not found')
        return EXIT_INTEGRITY
    off_len_s = mpos + len(codecs.UNIQUE_MARKER)
    off_len_e = off_len_s + codecs.META_LEN_BYTES
    if off_len_e > len(blob):
        logging.error('Meta length out of bounds')
        return EXIT_INTEGRITY
    mlen = int.from_bytes(blob[off_len_s:off_len_e], 'big')
    off_meta_s = off_len_e
    off_meta_e = off_meta_s + mlen
    if off_meta_e > len(blob):
        logging.error('Meta JSON out of bounds')
        return EXIT_INTEGRITY
    try:
        meta = json.loads(blob[off_meta_s:off_meta_e].decode('utf-8'))
    except Exception as e:
        logging.error(f'Meta parse error: {e}')
        return EXIT_INTEGRITY

    size = int(meta['size'])
    off_pay_s = off_meta_e
    off_pay_e = off_pay_s + size
    if off_pay_e > len(blob):
        logging.error('Payload out of bounds')
        return EXIT_INTEGRITY
    comp_payload_enc = blob[off_pay_s:off_pay_e]
    if sha256_hex(comp_payload_enc) != meta.get('sha256'):
        logging.error('Checksum mismatch')
        return EXIT_INTEGRITY

    try:
        comp_payload = maybe_decrypt(comp_payload_enc, meta.get('enc'), args.pass_env, args.password)
    except Exception as e:
        logging.error(f'Decryption error: {e}')
        return EXIT_RUNTIME

    try:
        payload_raw = AdaptiveCompressor.decompress(comp_payload, meta.get('method', 'lz77'))
    except Exception as e:
        logging.error(f'Decompress error: {e}')
        return EXIT_RUNTIME

    os.makedirs(args.output_dir, exist_ok=True)
    out_name = meta.get('filename', 'payload.bin')
    out_path = os.path.join(args.output_dir, out_name)

    if meta.get('is_archive') and meta.get('archive_format') == 'tar':
        try:
            with tarfile.open(fileobj=io.BytesIO(payload_raw), mode='r') as tf:
                tf.extractall(args.output_dir)
            logging.info(f'Extracted archive into {args.output_dir}')
        except Exception as e:
            logging.warning(f'Archive extract failed: {e}. Saving TAR instead.')
            safe_write(out_path, payload_raw)
            logging.info(f'Saved TAR at {out_path}')
    else:
        safe_write(out_path, payload_raw)
        logging.info(f'Saved payload at {out_path}')
    return EXIT_OK
