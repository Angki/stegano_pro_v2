# -*- coding: utf-8 -*-
"""
Steganography Tool - DCT-LSB Method (Simple Implementation)
Version: 0.1.0

This script provides a simplified proof-of-concept implementation of steganography
by hiding data in the Least Significant Bits (LSB) of DCT coefficients of a JPEG image.

=========================================================================================
IMPLEMENTASI TESIS - MAGISTER TEKNIK INFORMATIKA, UNIVERSITAS HASANUDDIN (2026)
Peneliti: Angki (D082221008)

PERAN DALAM PENELITIAN:
- Script ini dirancang KHUSUS UNTUK TUJUAN KOMPARASI DAN EDUKASI.
- Berperan sebagai "Metode Comparator" (Sistem Pembanding) untuk menguji kinerja 
  Sistem Usulan (stegano_pro_v2.1.py) dalam pengujian skala besar (400 dataset Van Gogh).
- Hasil pengujian membuktikan sistem usulan jauh lebih superior, karena script ini 
  gagal 100% (stego size = 0) saat menerima payload biner berukuran besar.

KETERBATASAN (Sengaja dipertahankan sebagai baseline):
- Kapasitas data sangat rendah (rentan merusak gambar jika payload besar).
- Tidak memiliki mekanisme adaptif, kompresi pintar, atau enkripsi.
- Masih bergantung penuh pada library eksternal (scipy.fftpack) untuk transformasi DCT.

GAMBARAN TEKNIS:
1.  Membaca citra JPEG dan mengubah ke ruang warna YCbCr (hanya memodifikasi Luma Y).
2.  Membagi channel Luma ke dalam blok 8x8 dan menerapkan 2D-DCT via scipy.
3.  Menyembunyikan bit payload ke dalam LSB dari koefisien AC mid-frequency.
4.  Melakukan inverse DCT, merekonstruksi gambar, dan menyimpan stego-image.
=========================================================================================
"""

import argparse
import numpy as np
from PIL import Image
from scipy.fftpack import dct, idct
import logging
import time

# --- Pengaturan Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- Konstanta ---
BLOCK_SIZE = 8
TERMINATOR = "::END::" # Penanda akhir pesan

def to_bits(data):
    """Konversi data (string) ke array bit."""
    bits = []
    for char in data:
        bits.extend(format(ord(char), '08b'))
    return bits

def from_bits(bits):
    """Konversi array bit kembali ke string."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) == 8:
            chars.append(chr(int("".join(byte), 2)))
    return "".join(chars)

class SteganographerDCT:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = Image.open(image_path).convert('YCbCr')
        self.width, self.height = self.image.size
        # Pastikan dimensi gambar kelipatan 8
        if self.width % BLOCK_SIZE != 0 or self.height % BLOCK_SIZE != 0:
            raise ValueError(f"Image dimensions must be a multiple of {BLOCK_SIZE}.")
        
        y, cb, cr = self.image.split()
        self.y_channel = np.array(y, dtype=np.float32) - 128
        self.cb_channel = np.array(cb, dtype=np.float32) - 128
        self.cr_channel = np.array(cr, dtype=np.float32) - 128
        
        self.dct_blocks = self._apply_dct()

    def _apply_dct(self):
        """Menerapkan 2D-DCT ke setiap blok 8x8 pada channel Luma."""
        dct_blocks = []
        for i in range(0, self.height, BLOCK_SIZE):
            for j in range(0, self.width, BLOCK_SIZE):
                block = self.y_channel[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE]
                dct_blocks.append(dct(dct(block.T, norm='ortho').T, norm='ortho'))
        return dct_blocks

    def embed(self, payload_str: str, output_path: str):
        """Menyisipkan pesan string ke dalam koefisien DCT."""
        logging.info("Starting DCT-LSB embedding...")
        start_time = time.time()
        
        payload_bits = to_bits(payload_str + TERMINATOR)
        bit_index = 0
        
        capacity = 0
        
        new_dct_blocks = []

        for block in self.dct_blocks:
            flat_block = block.flatten()
            for i in range(1, len(flat_block)): # Lewati koefisien DC (indeks 0)
                coeff = int(flat_block[i])
                if coeff != 0 and coeff != 1: # Hanya ubah koefisien non-trivial
                    capacity += 1
                    if bit_index < len(payload_bits):
                        new_coeff = (coeff & ~1) | int(payload_bits[bit_index])
                        flat_block[i] = new_coeff
                        bit_index += 1
            new_dct_blocks.append(flat_block.reshape(BLOCK_SIZE, BLOCK_SIZE))
            
        if bit_index < len(payload_bits):
            logging.warning(f"Payload is too large for the image. Only {bit_index} bits embedded.")
            logging.warning(f"Maximum capacity is approximately {capacity // 8} bytes.")

        # Rekonstruksi gambar
        self._reconstruct_image(new_dct_blocks, output_path)
        
        end_time = time.time()
        logging.info(f"Embedding finished in {end_time - start_time:.4f} seconds.")
        logging.info(f"Stego-image saved to {output_path}")

    def _reconstruct_image(self, dct_blocks, output_path):
        """Melakukan iDCT dan menyimpan gambar."""
        new_y_channel = np.zeros_like(self.y_channel)
        block_index = 0
        for i in range(0, self.height, BLOCK_SIZE):
            for j in range(0, self.width, BLOCK_SIZE):
                block = dct_blocks[block_index]
                idct_block = idct(idct(block.T, norm='ortho').T, norm='ortho')
                new_y_channel[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE] = idct_block
                block_index += 1

        # Gabungkan kembali channel YCbCr dan simpan
        final_y = Image.fromarray(np.uint8(np.clip(new_y_channel + 128, 0, 255)))
        final_cb = Image.fromarray(np.uint8(np.clip(self.cb_channel + 128, 0, 255)))
        final_cr = Image.fromarray(np.uint8(np.clip(self.cr_channel + 128, 0, 255)))
        
        stego_image = Image.merge('YCbCr', (final_y, final_cb, final_cr)).convert('RGB')
        stego_image.save(output_path, quality=95)

def main():
    parser = argparse.ArgumentParser(description="Simple DCT-LSB Steganography Tool (for comparison).")
    parser.add_argument('container', help="Path to the container JPEG image.")
    parser.add_argument('payload_file', help="Path to the text file payload.")
    parser.add_argument('output', help="Path for the output stego-image file.")
    
    args = parser.parse_args()

    try:
        with open(args.payload_file, 'r') as f:
            payload = f.read()
        
        steganographer = SteganographerDCT(args.container)
        steganographer.embed(payload, args.output)

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
    except ValueError as e:
        logging.error(f"Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
