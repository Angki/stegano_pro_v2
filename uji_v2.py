# -*- coding: utf-8 -*-
"""
Skrip Pengujian Batch/Recursive (uji_v2.py) - Thesis Defense Edition
Fitur:
- Scanning direktori rekursif (Dataset Besar: Van Gogh)
- Payload Pool Dinamis
- Kolom Analisis Lengkap (Latency, Compression Delta, Size Info)
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
TOOL_SCRIPT_MAIN = os.path.join(SCRIPT_DIR, "stegano_pro_v2.py")
TOOL_SCRIPT_COMP = os.path.join(SCRIPT_DIR, "stegano_dct.py")

OUTPUT_BASE_DIR = r"G:\Other computers\ASUS TUF A15\Project\Tutup\output\uji_2"
REPORT_CSV = os.path.join(OUTPUT_BASE_DIR, "laporan_uji_batch.csv")

# --- DATA UJI ---
SOURCE_COVER_DIR = r"F:\SoulSeek Downloads\complete\Thylarox\200 Amazing Vincent Van Gogh Artworks"
PAYLOADS_POOL = [
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

# --- UTILS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def is_image(filename):
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))

def prepare_payload_package(file_list, temp_dir_root):
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
    return pkg_path, total_size, ", ".join(names)

def run_command(cmd_list, timeout=120):
    start = time.time()
    try:
        env = os.environ.copy()
        env["STEGO_PASS"] = "batch_test_pass"
        result = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=env)
        return result.returncode == 0, result.stderr.decode('utf-8', errors='ignore'), time.time() - start
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
    DIR_APPEND = os.path.join(OUTPUT_BASE_DIR, "result_append")
    DIR_DCT = os.path.join(OUTPUT_BASE_DIR, "result_dct")
    DIR_TEMP_PAYLOAD = os.path.join(OUTPUT_BASE_DIR, "temp_pack")
    
    ensure_dir(DIR_APPEND)
    ensure_dir(DIR_DCT)
    ensure_dir(DIR_TEMP_PAYLOAD)
    
    # Kumpulkan semua file cover secara rekursif
    all_covers = []
    for root, dirs, files in os.walk(SOURCE_COVER_DIR):
        for f in files:
            if is_image(f):
                all_covers.append(os.path.join(root, f))
    
    logging.info(f"Total Images Found: {len(all_covers)}")
    random.shuffle(all_covers) # Acak urutan biar variatif jika di-stop di tengah
    
    results = []
    
    # Batasi jumlah cover jika perlu (misal max 50 untuk tes cepat), hapus slice [:50] untuk full
    for i, cover_path in enumerate(all_covers): 
        cover_name = os.path.basename(cover_path)
        cover_size = os.path.getsize(cover_path)
        
        # Skenario acak: 1 sampai 4 payload
        # Dalam batch besar, kita rotasi jumlah payload: (i % 4) + 1
        n_pay = (i % 4) + 1 
        
        logging.info(f"[{i+1}/{len(all_covers)}] Proc: {cover_name} ({n_pay} Payloads)")
        
        current_payloads = random.sample(PAYLOADS_POOL, min(n_pay, len(PAYLOADS_POOL)))
        pack_path, payload_orig_size, payload_names = prepare_payload_package(current_payloads, DIR_TEMP_PAYLOAD)
        
        out_append = os.path.join(DIR_APPEND, f"batch_{i}_{cover_name}.jpg")
        out_dct = os.path.join(DIR_DCT, f"batch_{i}_{cover_name}.jpg")
        
        row = {
            "cover_image": cover_name,
            "cover_size": cover_size,
            "payload_names": payload_names,
            "payload_size": payload_orig_size,
            "stegano_result_size": 0,
            "compressed_payload_size_total": 0,
            "time_pro_append": 0, "psnr_pro_append": 0, "rmse_pro_append": 0, "status_pro_append": "N/A",
            "time_pro_dct": 0, "psnr_pro_dct": 0, "rmse_pro_dct": 0, "status_pro_dct": "N/A",
            "time_dct_simple": 0, "psnr_dct_simple": 0, "rmse_dct_simple": 0, "status_dct_simple": "Skip",
            "time_latency": 0,
            "size_info(percent change)": 0
        }
        
        # 1. APPEND
        cmd_app = [sys.executable, TOOL_SCRIPT_MAIN, "embed", 
                   "-m", "append", "-c", cover_path, "-p", pack_path, "-o", out_append, "--encrypt", "--pass-env", "STEGO_PASS"]
        suc, _, dur = run_command(cmd_app)
        row["time_pro_append"] = round(dur, 4)
        if suc and os.path.exists(out_append):
            p, r = calculate_metrics_cv2(cover_path, out_append)
            row["psnr_pro_append"] = p
            row["rmse_pro_append"] = r
            row["status_pro_append"] = "Success"
            
            # MATH METRICS
            stego_size = os.path.getsize(out_append)
            row["stegano_result_size"] = stego_size
            added_bytes = stego_size - cover_size
            row["compressed_payload_size_total"] = added_bytes
            row["time_latency"] = round(dur, 4)
            
            efficiency_delta = added_bytes - payload_orig_size
            pct_change = (efficiency_delta / payload_orig_size * 100) if payload_orig_size > 0 else 0
            row["size_info(percent change)"] = round(pct_change, 2)
        else:
            row["status_pro_append"] = "Fail"
            
        # 2. DCT (Optional di batch besar karena lambat)
        cmd_dct = [sys.executable, TOOL_SCRIPT_MAIN, "embed", 
                   "-m", "dct", "-c", cover_path, "-p", pack_path, "-o", out_dct, "--rate", "0.05", "--encrypt", "--pass-env", "STEGO_PASS"]
        suc_d, _, dur_d = run_command(cmd_dct)
        row["time_pro_dct"] = round(dur_d, 4)
        if suc_d and os.path.exists(out_dct):
             p, r = calculate_metrics_cv2(cover_path, out_dct)
             row["psnr_pro_dct"] = p
             row["rmse_pro_dct"] = r
             row["status_pro_dct"] = "Success"
        else:
             row["status_pro_dct"] = "Fail"
             
        results.append(row)
        
        # Cleanup temp payload per loop
        try: shutil.rmtree(pack_path)
        except: pass

        # Auto-save CSV setiap 10 iterasi (biar data aman kalau crash)
        if i % 10 == 0:
            pd.DataFrame(results).to_csv(REPORT_CSV, index=False)

    # Final Save
    pd.DataFrame(results).to_csv(REPORT_CSV, index=False)
    print(f"\n[SELESAI BATCH] Laporan tersimpan di: {REPORT_CSV}")

if __name__ == "__main__":
    main()