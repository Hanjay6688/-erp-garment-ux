# P19 — skala aplikasi penuh (sumber Native nyata, Auth nyata, klik sampai tampil)

Status: bukti penulis di cabang `claude/new-session-deapao`; bukan audit independen. `full_P19_acceptance=false`, `production_go=false`. Tidak ada batas yang dinaikkan dan tidak ada data yang dicuplik/dipotong (`limits_raised=false`, `data_sampled_or_truncated=false`). Bukti di sini berjenis `FULL_APPLICATION_NATIVE`; benchmark kernel (`P19_KERNEL_JOB_TRANSPORT_CLAUDE.md`, job Shell `p19-assembly`) **tidak** dipakai sebagai bukti aplikasi.

Suite: `p19-scale5` di workflow `claude-p19-transport.yml` (deklarasi `P19_SCALE.json`, kasus `cp7_p19_scale_cases.py`, browser `cp7_p19_scale_browser.mjs`). Target diisi hanya lewat writer biasa (importer BB, draf/posting penjualan, perintah profil/SKU/kebijakan/kalender publik); waktu pengisian dicatat terpisah dari latensi.

## 1. Run pertama — 37560925773 (head `20da4de4`)

- **Kegagalan pertama (fixture):** batch BB kedua ditolak `brands_brand_name_key` karena semua batch memakai nama merek yang sama. Tangga SQL native dan browser 300/1000/5000 berhenti di pengisian. Diperbaiki di `3eafa83e` (nama master memuat kode batch); aturan ukur/oracle tidak berubah.
- **Ukuran 100 target (98 diisi + 2 yang sudah ada), browser desktop, login Auth nyata — PASS:**

| Riwayat | Tombol | Klik → status pertama | Klik → "Sedang dihitung" | Klik → progres segmen | Klik → hasil tampil | Original |
|---|---|---|---|---|---|---|
| 1 hari | Ambil analisis | 5,2 ms | 3.003 ms | — | **7.742 ms** | 4.203.290 byte |
| 1 hari | Hitung di latar belakang | 4,0 ms | 31,6 ms | 7.609 ms | **8.014 ms** | 3 segmen |
| 30 hari | Ambil analisis | 5,5 ms | 3.003 ms | — | **7.749 ms** | 4.203.448 byte |
| 30 hari | Latar belakang | 5,6 ms | 21,2 ms | 7.584 ms | **7.968 ms** | 3 segmen |
| 100 hari | Ambil analisis | 7,2 ms | 3.003 ms | — | **8.198 ms** | 4.203.547 byte |
| 100 hari | Latar belakang | 5,3 ms | 26,7 ms | 9.558 ms | **9.944 ms** | 3 segmen |

Penilaian terhadap target owner: tanda terima pertama < 1 dtk **terpenuhi**; hasil lengkap ≤ 3 dtk **tidak terpenuhi** (7,7–9,9 dtk). Pada mode latar belakang status "Sedang dihitung sejak jam …" tampil dalam ≤ 32 ms, tetapi job sisi server butuh ±7,5 dtk — sudah dekat batas 8 dtk per request pada **100** target. Pembanding lama (fixture 12 factset): capture backend 940 ms, body 659 KB.

**Kesimpulan sementara:** biaya capture analisis aplikasi penuh ±65–75 ms dan ±42 KB per target. Dengan batas 8 dtk yang tidak diubah dan tanpa worker di luar request, ±100 target adalah kisaran yang masih muat; 300 target diperkirakan berhenti di 8 dtk, dan 5.000 target ditolak oleh batas 1.000 produk per capture. Run berikutnya mengukur 300/1000/5000 dan profil per fase sisi server untuk menamai langkah yang lambat.
