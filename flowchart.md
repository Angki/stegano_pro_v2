# Flowchart Sistem

Dokumen ini berisi diagram alur (flowchart) untuk memvisualisasikan cara kerja komponen utama dalam proyek **Steganography Suite v2.1**. Semua diagram menggunakan sintaks Mermaid.

<details>
<summary><b>1. Arsitektur Umum Stegano Pro v2.1</b></summary>

```mermaid
graph TD
    CLI(["CLI (argparse)"]) --> Parse[Parsing Argumen]
    Parse --> Mode{Mode Operasi?}
    
    Mode -->|embed| Embed[embed_pipeline]
    Mode -->|extract| Extract[extract_pipeline]
    Mode -->|metrics| Metrics[metrics_pipeline]
    Mode -->|bench| Bench[bench_pipeline]
    
    %% Alur Embed
    Embed --> LoadPayload[load_payload]
    LoadPayload -->|Jika Direktori| AutoTar(Auto TAR in-memory)
    LoadPayload -->|Jika File| ReadFile(Baca File)
    AutoTar --> Comp(AdaptiveCompressor.compress_auto)
    ReadFile --> Comp
    
    Comp --> Race{LZ77 vs LZ78}
    Race -->|Hitung delta| BestComp(Pilih output terkecil)
    BestComp --> Encrypt{"--encrypt? (AES-GCM)"}
    
    Encrypt -->|Ya| AES(AES-256-GCM)
    Encrypt -->|Tidak| NoEnc(Plain)
    AES --> Wrap[Wrap + Metadata JSON + SHA256]
    NoEnc --> Wrap
    
    Wrap --> Codec{Pilih Codec}
    Codec -->|append| App[AppendCodec]
    Codec -->|dct| DCT[DctCodec]
    
    App --> Out[Simpan Stego Image]
    DCT --> Out
```

</details>

<details>
<summary><b>2. Algoritma Adaptive Compression Engine</b></summary>

```mermaid
graph TD
    Input([Input Data]) --> Parallel
    
    subgraph Adaptive Selector
        Parallel --> LZ77[Zlib / LZ77]
        Parallel --> LZ78[Custom LZ78]
        
        LZ77 --> Size77(Hitung Ukuran)
        LZ78 --> Size78(Hitung Ukuran)
        
        Size77 --> Compare{Size77 <= Size78?}
        Size78 --> Compare
        
        Compare -->|Ya| Ret77(Return LZ77 & Metadata 'lz77')
        Compare -->|Tidak| Ret78(Return LZ78 & Metadata 'lz78')
    end
    
    Ret77 --> Output([Output Data Kompresi])
    Ret78 --> Output
```

</details>

<details>
<summary><b>3. Pemrosesan DCT Kustom (NumPy)</b></summary>

```mermaid
graph TD
    Cover([Citra Cover RGB]) --> YCbCr[Konversi YCbCr]
    YCbCr --> Split[Ambil Channel Y Luma]
    Split --> Blocks(Bagi ke blok 8x8)
    
    Blocks --> DCT2[2D-DCT numpy custom]
    DCT2 --> CostMap(Evaluasi Cost-Map / AC coefficients)
    CostMap --> EmbedBits[Sisipkan bit pada koefisien terpilih]
    
    EmbedBits --> IDCT2[2D-IDCT numpy custom]
    IDCT2 --> Merge(Gabungkan blok 8x8)
    Merge --> RGB[Konversi kembali ke RGB]
    RGB --> Out([Stego Image Terkomputasi])
```

</details>

<details>
<summary><b>4. Flowchart Comparator (stegano_dct.py)</b></summary>

```mermaid
graph TD
    Start(["Mulai Comparator"]) --> ReadImg(Baca Image -> YCbCr -> Y)
    ReadImg --> ReadText(Konversi payload string ke biner)
    ReadText --> DCTBlocks(Bagi 8x8 -> `scipy.fftpack.dct`)
    
    DCTBlocks --> LSB[Embed LSB di AC coefficients spesifik]
    LSB --> IDCTBlocks(`scipy.fftpack.idct`)
    IDCTBlocks --> Merge(Gabungkan ke RGB)
    Merge --> Save(["Simpan Stego Image"])
    
    style DCTBlocks fill:#f9d0c4,stroke:#333,stroke-width:2px
    style IDCTBlocks fill:#f9d0c4,stroke:#333,stroke-width:2px
```
*> Blok merah menggunakan library `scipy`, yang menjadi titik ukur pembanding terhadap implementasi NumPy kustom di v2.1.*

</details>
