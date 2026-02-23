# -*- coding: utf-8 -*-
"""
Skrip Pengujian Spesifik (uji.py) - Thesis Defense Edition
Fitur:
- Hardcoded Test Cases (Cover & Payloads spesifik)
- Skenario: 1, 2, 3, dan 4 Payload per Cover
- Kalkulasi Size Metrics (Cover vs Payload vs Stego)
- Output CSV Detail untuk Bab Analisis
"""

import os
import sys
import subprocess
import shutil
import logging
import time
import random
import math
import cv2
import numpy as np
import pandas as pd

# --- KONFIGURASI PATH ---
SCRIPT_DIR = r"G:\Other computers\ASUS TUF A15\Project\Tutup\app"
TOOL_SCRIPT_MAIN = os.path.join(SCRIPT_DIR, "stegano_pro_v2.py") # Asumsi nama file v2.py (isi v2.1)
TOOL_SCRIPT_COMP = os.path.join(SCRIPT_DIR, "stegano_dct.py")

OUTPUT_BASE_DIR = r"G:\Other computers\ASUS TUF A15\Project\Tutup\output\uji_1"
REPORT_CSV = os.path.join(OUTPUT_BASE_DIR, "laporan_uji_spesifik.csv")

# --- DATA UJI ---
COVERS = [
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\camera\20230901_024823.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\camera\IMG_20250930_010538.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\camera\_DSC0419.JPG",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\camera\_DSC0428.JPG",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\diamond-security-sticker (10).png",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\FB_IMG_1692038040383.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\FB_IMG_1758651058323.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\Layer 2 - 44.png",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\Layer 2 - 9.png",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\street_texture_11.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\street_texture_23.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\street_texture_24.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\street_texture_26.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\street_texture_28.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\Wow-zip 12.png",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\Wow-zip 5.png",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\random\Wow-zip 8.png",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\wa\IMG-20231113-WA0000.jpg",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\image\wa\IMG-20250508-WA0021.jpg",
]

PAYLOADS = [
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\23. Cyber Security Awareness Survey.pdf",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Audio 1.mp3",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Audio 2.mp3",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Audio 3.mp3",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\KHS 2022.pdf",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\KRS Angki 2025.pdf",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Manajemen Risiko Siber.pptx",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\PPT Proposal.pptx",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Presentasi Angki D082221008.pptx",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Surat pernyataan komitmen penyelesaian tesis.docx",
    r"G:\Other computers\ASUS TUF A15\Project\Tesis\app\data\multimedia\Tugas Metopel - Angki.docx",
]

# --- SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.StreamHandler(sys.stdout)
])

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def prepare_payload_package(file_list, temp_dir_root):
    """
    Menyalin file payload ke folder sementara agar bisa diproses sebagai folder oleh script utama.
    """
    pkg_name = f"pack_{int(time.time()*1000)}_{random.randint(100,999)}"
    pkg_path = os.path.join(temp_dir_root, pkg_name)
    ensure_dir(pkg_path)
    
    total_size = 0
    names = []
    
    for f in file_list:
        if os.path.exists(f):
            shutil.copy2(f, pkg_path)
            total_size += os.path.getsize(f)
            names.append(os.path.basename(f))
        else:
            logging.warning(f"Payload not found: {f}")
            
    return pkg_path, total_size, ", ".join(names)

def run_command(cmd_list, timeout=120):
    start = time.time()
    try:
        # Gunakan env var untuk pass dummy password jika perlu
        env = os.environ.copy()
        env["STEGO_PASS"] = "kunci_rahasia_tesis_angki_2026"
        
        result = subprocess.run(
            cmd_list, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env
        )
        duration = time.time() - start
        if result.returncode == 0:
            return True, result.stdout.decode('utf-8', errors='ignore'), duration
        else:
            return False, result.stderr.decode('utf-8', errors='ignore'), duration
    except Exception as e:
        return False, str(e), time.time() - start

def calculate_metrics_cv2(cover_path, stego_path):
    try:
        img1 = cv2.imread(cover_path)
        img2 = cv2.imread(stego_path)
        if img1 is None or img2 is None: return 0, 0
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        mse = np.mean((img1 - img2) ** 2)
        if mse == 0: return 100, 0
        psnr = 10 * np.log10(255**2 / mse)
        rmse = math.sqrt(mse)
        return round(psnr, 4), round(rmse, 4)
    except:
        return 0, 0

def main():
    ensure_dir(OUTPUT_BASE_DIR)
    
    # Direktori untuk file stego hasil
    DIR_APPEND = os.path.join(OUTPUT_BASE_DIR, "result_append")
    DIR_DCT = os.path.join(OUTPUT_BASE_DIR, "result_dct")
    DIR_SIMPLE = os.path.join(OUTPUT_BASE_DIR, "result_simple")
    # Direktori temp untuk packing payload
    DIR_TEMP_PAYLOAD = os.path.join(OUTPUT_BASE_DIR, "temp_pack")
    
    ensure_dir(DIR_APPEND)
    ensure_dir(DIR_DCT)
    ensure_dir(DIR_SIMPLE)
    ensure_dir(DIR_TEMP_PAYLOAD)
    
    results = []
    
    logging.info(f"Total Covers: {len(COVERS)}")
    logging.info(f"Total Payloads Pool: {len(PAYLOADS)}")
    
    # --- MULAI LOOPING COVER ---
    for i, cover_path in enumerate(COVERS):
        if not os.path.exists(cover_path):
            logging.warning(f"Cover missing: {cover_path}")
            continue
            
        cover_name = os.path.basename(cover_path)
        cover_size = os.path.getsize(cover_path)
        
        # --- LOOPING JUMLAH PAYLOAD (1 s.d 4) ---
        for n_pay in range(1, 5):
            logging.info(f"Processing: {cover_name} with {n_pay} Payload(s)")
            
            # Pilih payload secara acak/berurutan
            # Agar deterministik untuk reproduksi, kita gunakan seed atau slice jika cukup
            # Di sini kita ambil random sample
            current_payloads = random.sample(PAYLOADS, min(n_pay, len(PAYLOADS)))
            
            # Pack payload ke folder temp
            pack_path, payload_orig_size, payload_names = prepare_payload_package(current_payloads, DIR_TEMP_PAYLOAD)
            
            # Tentukan Output Paths
            out_append = os.path.join(DIR_APPEND, f"{n_pay}_{cover_name}.jpg")
            out_dct = os.path.join(DIR_DCT, f"{n_pay}_{cover_name}.jpg")
            out_simple = os.path.join(DIR_SIMPLE, f"{n_pay}_{cover_name}.jpg")
            
            # Siapkan baris data CSV
            row = {
                "cover_image": cover_name,
                "cover_size": cover_size,
                "payload_names": payload_names,
                "payload_size": payload_orig_size,
                # Placeholders
                "stegano_result_size": 0,
                "compressed_payload_size_total": 0,
                "time_pro_append": 0, "psnr_pro_append": 0, "rmse_pro_append": 0, "status_pro_append": "N/A",
                "time_pro_dct": 0, "psnr_pro_dct": 0, "rmse_pro_dct": 0, "status_pro_dct": "N/A",
                "time_dct_simple": 0, "psnr_dct_simple": 0, "rmse_dct_simple": 0, "status_dct_simple": "N/A",
                "time_latency": 0,
                "size_info(percent change)": 0
            }
            
            # --- 1. UJI MODE APPEND (First of File Strategy) ---
            cmd_app = [sys.executable, TOOL_SCRIPT_MAIN, "embed", 
                       "-m", "append", "-c", cover_path, "-p", pack_path, "-o", out_append, "--encrypt", "--pass-env", "STEGO_PASS"]
            
            suc, _, dur = run_command(cmd_app)
            row["time_pro_append"] = round(dur, 4)
            if suc and os.path.exists(out_append):
                p, r = calculate_metrics_cv2(cover_path, out_append)
                row["psnr_pro_append"] = p
                row["rmse_pro_append"] = r
                row["status_pro_append"] = "Success"
                
                # METRIK SIZE KHUSUS (Fokus pada Append/Main Method)
                stego_size = os.path.getsize(out_append)
                row["stegano_result_size"] = stego_size
                
                # Size tambahan (header + compressed payload)
                added_bytes = stego_size - cover_size
                row["compressed_payload_size_total"] = added_bytes
                
                # Latency Utama (Append)
                row["time_latency"] = round(dur, 4)
                
                # Efisiensi: (Stego - Cover - OriginalPayload)
                # Negatif = Hemat tempat (Kompresi berhasil mengatasi overhead)
                # Positif = Boros tempat (Overhead/Enkripsi lebih besar dari kompresi)
                efficiency_delta = added_bytes - payload_orig_size
                if payload_orig_size > 0:
                    pct_change = (efficiency_delta / payload_orig_size) * 100
                else:
                    pct_change = 0
                row["size_info(percent change)"] = round(pct_change, 2)
                
            else:
                row["status_pro_append"] = "Fail"

            # --- 2. UJI MODE DCT (Adaptive) ---
            cmd_dct = [sys.executable, TOOL_SCRIPT_MAIN, "embed", 
                       "-m", "dct", "-c", cover_path, "-p", pack_path, "-o", out_dct, "--rate", "0.05", "--encrypt", "--pass-env", "STEGO_PASS"]
            
            suc_d, log_d, dur_d = run_command(cmd_dct)
            row["time_pro_dct"] = round(dur_d, 4)
            if suc_d and os.path.exists(out_dct):
                p, r = calculate_metrics_cv2(cover_path, out_dct)
                row["psnr_pro_dct"] = p
                row["rmse_pro_dct"] = r
                row["status_pro_dct"] = "Success"
            else:
                if "No embedding positions" in log_d:
                     row["status_pro_dct"] = "Full/Skip"
                else:
                     row["status_pro_dct"] = "Fail"

            # --- 3. UJI SIMPLE DCT (Comparator) ---
            # Comparator biasanya cuma terima 1 file text. Kita buat dummy text payload seukuran total payload asli
            # atau skip jika terlalu besar (karena simple DCT kapasitasnya kecil)
            if payload_orig_size < 5000: # Batasi 5KB untuk simple DCT
                dummy_payload = os.path.join(DIR_TEMP_PAYLOAD, "dummy.txt")
                with open(dummy_payload, "w") as f:
                    f.write("A" * payload_orig_size)
                
                cmd_sim = [sys.executable, TOOL_SCRIPT_COMP, cover_path, dummy_payload, out_simple]
                suc_s, _, dur_s = run_command(cmd_sim)
                row["time_dct_simple"] = round(dur_s, 4)
                if suc_s and os.path.exists(out_simple):
                    p, r = calculate_metrics_cv2(cover_path, out_simple)
                    row["psnr_dct_simple"] = p
                    row["rmse_dct_simple"] = r
                    row["status_dct_simple"] = "Success"
                else:
                    row["status_dct_simple"] = "Fail"
            else:
                row["status_dct_simple"] = "Skip (Too Large)"

            results.append(row)
            
            # Bersihkan folder pack temp untuk iterasi berikutnya
            try:
                shutil.rmtree(pack_path)
            except:
                pass

    # --- SIMPAN CSV ---
    df = pd.DataFrame(results)
    df.to_csv(REPORT_CSV, index=False)
    print(f"\n[SELESAI] Laporan tersimpan di: {REPORT_CSV}")

if __name__ == "__main__":
    main()