# Fable — Putaran 14 (finisher CP6): BF dengan oracle sendiri + rerun bukti BF penulis di runtime auditor

Tanggal: 2026-10-01 (UTC). Status: **FINAL**. Kandidat: head alat `10a8347`, produk `434b182` (pin r13 tetap). Fase `after` memasang AN..BE lalu BF
(`INSTALL_BF=True`, badan dev sha d5e66d22…; badan paket rilis BF memuat badan dev itu utuh kecuali satu baris deskripsi ledger — INDEPENDENT_SOURCE_REVIEW).
Oracle laundry: **D13** (owner ke auditor, 1 Okt): tarif dari vendor, bukan SKU; SKU hanya riwayat biaya untuk dilihat lagi.

## 1. Skenario Fable `audit/scenarios/round14_fable/xaudit_14_bf.py` (sha 83813915…) — run 36808105014 — INDEPENDENT_NATIVE_RERUN

| Kasus | Oracle auditor | Hasil |
|---|---|---|
| `XA14:RANGE_MOVE_WRITES_NO_PHYSICAL` | pindah ukuran 34 dari SKU z ke SKU a setelah lot ada: baris `fg_stock_movements`, `fg_lots`, `products` identik (md5), jumlah jurnal tetap (19), buku FG/COGS/WIP tetap (520 / 0 / 1759); keanggotaan hanya berubah menurut waktu, riwayat lama tetap terbaca | **PASS** (9/9 cek) |
| `XA14:SKU_AT_TIMELINE_NO_GAP` | `bf_commercial_sku_at_v1` total & kontinu: 60 sampel waktu semua terjawab, z sebelum pindah / a sejak pindah, batas tepat di detik pindah; rantai versi tiap SKU `effective_to` = `effective_from` berikutnya, ekor terbuka; versi z ditutup tepat di waktu pindah | **PASS** (6/6) |
| `XA14:HPP_VALUE_CONSERVED_ACROSS_GROUPING` | laporan HPP: qty 20 & nilai 520 sama sebelum/sesudah regrouping; 4 lot; semua di a, z kosong | **PASS** (5/5) |
| `XA14:SUPPLIER_CREDIT_AP_CONSERVED` | kredit retur 20 pada nota 1 (AP 80/100/60): alokasi 5 → 85/95/60, 20 → 100/80/60, kosong → semula; Σ AP = 240 di semua keadaan; GL AP_SUPPLIER, stok & nilai bahan tidak berubah; nominal negatif ditolak (`BD_AMOUNT_INVALID`) dan alokasi 21 > 20 ditolak (`BF_CREDIT_EXCEEDS_RETURN`) tanpa perubahan | **PASS** (8/8) |

## 2. Bukti BF penulis dijalankan ulang lewat `cp6-auditor-scenario.yml` (after, head 10a8347) — INDEPENDENT_NATIVE_RERUN atas skenario penulis

| Paket | Run | Hasil | Catatan |
|---|---|---|---|
| `cp6_bf_combined_modes.py` + `cp6_bf_browser.mjs` | 36808112738 | **154/154 PASS** (97 native, 26 balapan, 8 HTTP, 23 browser) | probe final independen, riwayat konversi (R10), R03–R14, vendor, supplier |
| `cp6_bf_vendor_modes.py` + `cp6_bf_vendor_browser.mjs` | 36808128920 | **133/133 PASS** (76/22/8/27) | `VENDOR:AUTHORITY_WITH_LEGACY_SKU_OVERRIDE` PASS = D13(1); `PR30:D03_HISTORICAL_WORKSPACE` PASS = D13(2) |
| `cp6_bf_modes.py` + `cp6_bf_supplier_browser.mjs` | 36808136834 | **67/67 PASS** (38/20/7/2) | |
| `cp6_bf_free_modes.py` + `cp6_bf_free_browser.mjs` | 36808120840 | 116 PASS + **9 INCOMPLETE** | lihat §3 |

## 3. Satu hasil non-PASS: skenario penulis yang kedaluwarsa oleh aturan owner (D13), bukan cacat produk

9 kasus `SKU01:*` / `SKU01_RACE:*` / `SKU01_HTTP:*` / `SKU01_BROWSER:*` INCOMPLETE pada satu penolakan produk:
`BF_LAUNDRY_VENDOR_AUTHORITY: harga laundry diatur pada vendor; riwayat SKU hanya referensi pemilihan` (paket BF baris 414–415: setiap `laundry_rates`
pada master SKU ditolak). Dua kasus browser menunggu tombol "Tambah tarif laundry" yang memang sudah tidak ada di halaman Produk & SKU.
Skenario SKU-01 ditulis saat BF masih memasang tarif FREE/WAIVED di master SKU (sebelum koreksi owner 28 Sep → R16). Produk kini menegakkan D13.
Jalur FREE/WAIVED yang sah ada di master vendor BD dan **lulus**: `BF_REG_BD:REV:OWN02_FREE_WAIVED_LEGAL_PATH`, `BD_REV_BROWSER:FREE_MASTER_THEN_PHYSICAL_DESKTOP`,
`…WAIVED_MASTER_THEN_PHYSICAL_MOBILE`. Klasifikasi: **SUPERSEDED_BY_OWNER_RULE**. Untuk penulis: tandai `cp6_bf_free_modes.py`/`cp6_bf_free_browser.mjs`
historis atau tulis ulang SKU-01 di tingkat vendor; jangan "memperbaiki" produk agar skenario lama lulus.

## 4. Putusan putaran 14 dan penutupan CP6 dari sisi Fable

- BF lolos oracle Fable (4/4) dan rerun bukti penulis (354/354 pada tiga paket yang berlaku). D13 ditegakkan produk dan riwayat SKU tersedia.
- F3/D08: tinjauan sumber cukup (`/i` kanonik di dua berkas).
- Register keputusan dikoreksi: GBD-03 = opsi 1, D11 lima diputuskan + delapan isian aplikasi, UI-01 dijadwalkan owner. Tidak ada pertanyaan bisnis CP6 yang terbuka.
- **CP6 selesai dari sisi auditor Fable.** Yang tersisa hanya tindakan owner: isi 8 pengaturan di aplikasi (rekomendasi di indeks) dan keputusan `production_go` (tetap false sampai owner bilang go). Siap lanjut CP7.
