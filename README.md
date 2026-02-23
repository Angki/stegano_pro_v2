# Steganography Suite

> **Program steganografi Python end-to-end** — penelitian tesis untuk menyembunyikan file rahasia di dalam gambar dengan dukungan multi-metode, enkripsi, dan kompresi adaptif.

---

## Daftar Isi

- [Tentang Proyek](#tentang-proyek)
- [Fitur Utama](#fitur-utama)
- [Arsitektur](#arsitektur)
- [Persyaratan Sistem](#persyaratan-sistem)
- [Instalasi](#instalasi)
- [Penggunaan CLI](#penggunaan-cli)
  - [Embed (Sisipkan)](#embed-sisipkan)
  - [Extract (Ekstrak)](#extract-ekstrak)
  - [Metrics (Metrik Kualitas)](#metrics-metrik-kualitas)
  - [Bench (Batch Benchmark)](#bench-batch-benchmark)
- [File Dalam Proyek](#file-dalam-proyek)
- [Exit Codes](#exit-codes)
- [Changelog](#changelog)

---

## Tentang Proyek

**Steganography Suite** adalah program Python yang dikembangkan sebagai bagian dari penelitian **tesis** di bidang keamanan informasi. Program ini mengimplementasikan dan membandingkan dua metode steganografi:

- **Append (First-of-File / FoF)** — menyisipkan payload sebagai suffix setelah EOF marker gambar.
- **DCT (Domain Frekuensi)** — menyembunyikan bit ke dalam koefisien DCT mid-frequency pada channel luminansi (Y) gambar JPEG.

Fokus utama penelitian:
- Evaluasi perbandingan kualitas visual (PSNR, RMSE) antara kedua metode.
- Efisiensi kompresi payload menggunakan algoritma adaptif LZ77 dan LZ78.
- Keamanan data dengan enkripsi **AES-256-GCM**.
- Pengujian batch terhadap dataset gambar skala besar (koleksi Van Gogh).

---

## Fitur Utama

| Fitur | Keterangan |
|---|---|
| **Dual Codec** | Mode `append` (EOF marker) dan `dct` (domain frekuensi 8×8 blok luminansi) |
| **Adaptive Compression** | Otomatis memilih antara LZ77 (zlib) dan LZ78 (custom) berdasarkan rasio kompresi terbaik |
| **AES-256-GCM Encryption** | Enkripsi opsional dengan password (via argumen atau environment variable) |
| **Folder Payload** | Direktori otomatis di-*pack* menjadi TAR sebelum disisipkan |
| **Channel Presets** | Predefined mode untuk WhatsApp (`--channel whatsapp`) dan Telegram (`--channel telegram`) |
| **Strong Metadata** | Setiap stego menyimpan metadata JSON (checksum SHA-256, metode kompresi, ukuran, versi) |
| **Metrics** | Subcommand `metrics` untuk menghitung PSNR dan RMSE antara cover dan stego |
| **Bench Harness** | Subcommand `bench` untuk pengujian batch rekursif dengan output laporan CSV |
| **Logging Bertingkat** | Level log dapat dikontrol dengan `-v` (INFO) atau `-vv` (DEBUG) |
| **Exit Codes Eksplisit** | Setiap skenario error memiliki kode keluar tersendiri |

---

## Arsitektur

```
CLI (argparse)
    │
    ├─ embed_pipeline()
    │       ├─ load_payload()            ← auto-TAR jika direktori
    │       ├─ AdaptiveCompressor        ← LZ77 vs LZ78, pilih terbaik
    │       ├─ maybe_encrypt()           ← AES-256-GCM (opsional)
    │       └─ Codec (AppendCodec / DctCodec)
    │               └─ EmbedResult → stego bytes + metadata JSON
    │
    ├─ extract_pipeline()
    │       ├─ Temukan UNIQUE_MARKER (::STEGA_PAYLOAD_START::)
    │       ├─ Baca metadata JSON + verifikasi SHA-256
    │       ├─ maybe_decrypt()
    │       └─ AdaptiveCompressor.decompress()
    │
    ├─ metrics_pipeline()    ← PSNR & RMSE (Pillow + NumPy)
    └─ bench_pipeline()      ← Batch embed + metrics → CSV report
```

### Codec Interface

```
CodecBase
├── AppendCodec   — menyisipkan payload sebagai suffix setelah EOF marker
└── DctCodec      — menyisipkan bit ke koefisien DCT mid-frequency (Y channel)
                    menggunakan 2D-DCT custom (tanpa dependensi scipy)
```

---

## Persyaratan Sistem

- **Python** 3.9+
- **Pillow** — untuk image I/O (semua mode)
- **NumPy** — untuk mode DCT dan metrics
- **cryptography** — hanya jika menggunakan `--encrypt`

```bash
pip install pillow numpy cryptography
```

> `cryptography` bersifat **opsional** — hanya diimpor saat flag `--encrypt` digunakan.

---

## Instalasi

```bash
git clone <repo-url>
cd app
pip install pillow numpy cryptography
```

---

## Penggunaan CLI

### Embed (Sisipkan)

**Mode Append — file/folder payload:**
```bash
python stegano_pro_v2.1.py embed -m append -c cover.jpg -p secret.pdf -o stego.jpg
```

**Mode Append — folder (auto TAR):**
```bash
python stegano_pro_v2.1.py embed -m append -c cover.jpg -p "C:\path\folder" -o stego.jpg
```

**Mode DCT — dengan enkripsi dan preset WhatsApp:**
```bash
python stegano_pro_v2.1.py embed -m dct -c cover.jpg -p secret.zip -o stego.jpg \
    --rate 0.04 --encrypt --pass-env STEGO_PASS --channel whatsapp
```

**Mode DCT — dengan password langsung:**
```bash
python stegano_pro_v2.1.py embed -m dct -c cover.jpg -p secret.zip -o stego.jpg \
    --rate 0.05 --encrypt --password "mysecretpassword"
```

| Argumen | Keterangan |
|---|---|
| `-m, --mode` | `append` atau `dct` (wajib) |
| `-c, --container` | Path gambar cover |
| `-p, --payload` | Path file atau direktori yang akan disisipkan |
| `-o, --output` | Path output stego image |
| `--rate` | (DCT only) Rate kontrol dalam bits per non-zero AC (default: 0.04) |
| `--channel` | Preset channel: `none`, `whatsapp`, `telegram` |
| `--encrypt` | Aktifkan enkripsi AES-256-GCM |
| `--password` | Password plaintext untuk derivasi kunci |
| `--pass-env` | Nama environment variable yang berisi password |

---

### Extract (Ekstrak)

```bash
python stegano_pro_v2.1.py extract -s stego.jpg -o ./output_dir
```

**Dengan dekripsi (environment variable):**
```bash
set STEGO_PASS=mysecretpassword
python stegano_pro_v2.1.py extract -s stego.jpg -o ./output_dir --pass-env STEGO_PASS
```

| Argumen | Keterangan |
|---|---|
| `-s, --stego-image` | Path stego image |
| `-o, --output-dir` | Direktori output untuk payload |
| `--password` | Password dekripsi (jika payload dienkripsi) |
| `--pass-env` | Nama env var untuk password |

---

### Metrics (Metrik Kualitas)

Menghitung **PSNR** (Peak Signal-to-Noise Ratio) dan **RMSE** (Root Mean Square Error) antara gambar cover dan stego.

```bash
python stegano_pro_v2.1.py metrics --cover cover.jpg --stego stego.jpg
```

Output contoh:
```
PSNR: 42.1337 dB
RMSE: 1.9823
```

---

### Bench (Batch Benchmark)

Melakukan embed dan kalkulasi metrik secara batch terhadap seluruh gambar dalam satu folder, lalu menyimpan hasilnya ke CSV.

```bash
python stegano_pro_v2.1.py bench \
    --covers ./covers_dir \
    --payload secret.bin \
    -m dct \
    --rate 0.04 \
    --report bench_report.csv
```

| Argumen | Keterangan |
|---|---|
| `--covers` | Direktori yang berisi gambar-gambar cover |
| `--payload` | File payload yang akan digunakan untuk semua cover |
| `-m, --mode` | `append` atau `dct` |
| `--rate` | Rate kontrol (DCT) |
| `--report` | Path output file CSV laporan |

---

### Verbosity

```bash
python stegano_pro_v2.1.py -v embed ...     # INFO level
python stegano_pro_v2.1.py -vv embed ...    # DEBUG level
```

---

## File Dalam Proyek

| File | Peran | Keterangan |
|---|---|---|
| `stegano_pro_v2.1.py` | **Program Utama** | Implementasi utama steganografi — digunakan sebagai objek penelitian |
| `stegano_dct.py` | **Tool Pembanding** | Implementasi DCT-LSB sederhana menggunakan `scipy.fftpack`, digunakan sebagai baseline perbandingan dalam penelitian |
| `uji.py` | **Script Pengujian** | Batch testing generasi pertama |
| `uji_v2.py` | **Script Pengujian v2** | Batch testing rekursif skala besar — scanning dataset, dynamic payload pool, laporan CSV dengan kolom latency, compression delta, dan metrik kualitas |

---

## Exit Codes

| Kode | Konstanta | Skenario |
|---|---|---|
| `0` | `EXIT_OK` | Sukses |
| `2` | `EXIT_ARG` | Argumen tidak valid |
| `3` | `EXIT_RUNTIME` | Error saat proses (kompresi/enkripsi/embed) |
| `4` | `EXIT_IO` | Error baca/tulis file |
| `5` | `EXIT_INTEGRITY` | Marker tidak ditemukan atau checksum SHA-256 gagal |

---

## Changelog

### v2.1.0 — Custom Compression Engine (Current)

**Perubahan utama dari v2.0 ke v2.1:**

#### ✨ Kompresi Adaptif Tanpa Library Eksternal

Di versi **v2.0**, kompresi DCT mengandalkan library eksternal `scipy.fftpack` untuk fungsi DCT/IDCT, khususnya pada `stegano_dct.py`. Hal ini menciptakan ketergantungan tambahan dan keterbatasan fleksibilitas.

Di versi **v2.1**, seluruh fungsi kompresi dan transformasi DCT **diimplementasikan sendiri** secara *from scratch*:

- **`lz78_compress(data)`** — Implementasi kustom algoritma LZ78 dalam Python murni. Menggunakan dictionary-based phrase encoding dan output format biner dengan signature `LZ78\x00`.
- **`lz78_decompress(comp)`** — Fungsi dekompresi pasangan LZ78 dengan validasi signature dan stream integrity check.
- **`AdaptiveCompressor.compress_auto(data)`** — Fungsi pemilihan kompresi adaptif yang menjalankan **kedua** algoritma (LZ77 via `zlib` dan LZ78 kustom) lalu secara otomatis memilih hasil dengan rasio kompresi terbaik.
- **`DctCodec._dct1()` / `_idct1()`** — Implementasi DCT-II dan IDCT-II 1D from scratch menggunakan NumPy, **tanpa scipy**, sehingga dependensi berkurang satu paket.
- **`DctCodec._dct2()` / `_idct2()`** — DCT-II 2D separable dibangun di atas `_dct1` dan `_idct1`.

#### Perbandingan v2.0 vs v2.1

| Aspek | v2.0 | v2.1 |
|---|---|---|
| DCT/IDCT | `scipy.fftpack.dct / idct` | Implementasi kustom NumPy (tanpa scipy) |
| Algoritma kompresi | Hanya LZ77 (`zlib`) | LZ77 + LZ78 kustom, dipilih adaptif |
| Dependensi compression | `zlib` (stdlib) | `zlib` (stdlib) + kode sendiri |
| Dependensi DCT | `scipy` | Tidak ada (dihapus) |
| Pemilihan algoritma | Manual / tetap | Otomatis berdasarkan rasio terkecil |

#### 🔧 Perbaikan & Peningkatan Lain

- Metadata stego kini menyertakan field `comp` (metode kompresi yang dipilih) dan `comp_ratio` (persentase penghematan ukuran).
- Logging lebih informatif: saat kompresi selesai, ditampilkan metode yang dipilih, rasio, dan perbandingan ukuran LZ77 vs LZ78.
- Penanganan error LZ78 yang lebih robust: jika kompresi LZ78 gagal, fallback otomatis ke LZ77.

---

### v2.0.0

- Dual codec: `AppendCodec` dan `DctCodec`.
- Enkripsi AES-256-GCM dengan derivasi kunci SHA-256.
- Metadata JSON dengan checksum SHA-256 dan unique marker.
- Subcommand `metrics` (PSNR, RMSE) dan `bench` (batch CSV report).
- Channel presets: WhatsApp, Telegram.
- Folder payload otomatis di-TAR.

---

*Author: Angki — untuk keperluan penelitian Tesis.*
