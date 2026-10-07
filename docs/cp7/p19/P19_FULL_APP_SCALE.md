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

## 2. Run ketiga — 37565310513 (head `eb2e0927`; run kedua 37564127281 di `3eafa83e` gagal dengan pola yang sama)

Browser desktop, login Auth nyata, data diisi lewat writer biasa (waktu isi: 100 → 4,1 dtk; 300 → 9,1 dtk; 1000 → 37,9 dtk; tidak termasuk latensi):

| Target | Riwayat | Klik → status pertama | Klik → hasil/penolakan tampil | Keadaan |
|---|---|---|---|---|
| 100 | 1 / 30 / 100 hari | 4,1–5,2 ms | **5.267–5.940 ms** (ambil 5,3–5,6 dtk; latar belakang 5,5–5,9 dtk) | hasil lengkap, Original ±4,2 MB, 3 segmen |
| 300 | 1 / 30 / 100 hari | 2,8–4,8 ms | **8.031–8.061 ms** | **ditolak jujur di batas 8 dtk** (`HONEST_CAP_REFUSAL`) |
| 1000 | 1 / 30 / 100 hari | 4,1–6,5 ms | **8.022–8.063 ms** | **ditolak jujur di batas 8 dtk** |
| 5000 | — | — | — | belum terukur: pengisian gagal (lihat bawah) |

Status "Sedang dihitung sejak jam …" pada mode latar belakang tampil dalam 18–37 ms di semua ukuran. Tanda terima pertama < 1 dtk terpenuhi; hasil lengkap ≤ 3 dtk **tidak** terpenuhi bahkan di 100 target.

**Kegagalan harness yang dicatat (bukan perilaku aplikasi):** tangga SQL native dan pengisian 5.000 target berhenti dengan `out of shared memory / max_locks_per_transaction`. Penyebab: fixture memanggil ribuan writer (setiap writer CP7 mengambil `pg_advisory_xact_lock` per request) dalam **satu** transaksi, sedangkan aplikasi nyata menjalankan satu RPC per transaksi. Perbaikan: commit per halaman writer dan tangga SQL + profil fase dijalankan pada salinan ter-commit per ukuran. Setelan lock dan batas aplikasi **tidak** diubah. Kode penolakan sisi server 300/1000 tercatat di dalam `verdict` setiap klik: capture biasa → SQLSTATE `57014` dari `erp_cp7_capture_analysis_v1`; mode latar belakang → `CP7_ANALYSIS_JOB_STOPPED` (SQLSTATE 57014) dari `erp_cp7_run_analysis_job_v1`; batas `STATEMENT_TIMEOUT_8S`. Kini juga ditulis di tingkat atas witness.

**Kesimpulan saat ini:** pada batas 8 dtk yang tidak diubah dan tanpa worker di luar request, alur aplikasi penuh menghasilkan analisis untuk ±100 target; 300 dan 1000 target ditolak jujur di 8 dtk. Langkah yang dominan sedang diukur dengan profil fase. Perbaikan kernel yang sudah masuk sesudah head run ini (PL-8 normalisasi `b001bf4f`, netting `083c90e3`) dan yang sedang dikerjakan (`allocate`) diukur ulang di run berikutnya.

