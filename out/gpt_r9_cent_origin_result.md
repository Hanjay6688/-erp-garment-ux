# CP6 W8 — uji independen tiga sumber yang tidak bertumpuk

## Identitas beku

- Workflow: [GPT CP6 W8 Isolated Source Cent Audit, run 36132246344](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36132246344), job `108061962769`, `SUCCESS` / native `RUN_COMPLETE`.
- Commit pemicu audit: `8d4edc4283de2d6a61dfed222a775248be5cebef`; tool head: `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`; `product_ref`: `61d88ee5224b2fb2da2af6f4df214fbaacf9f161`; fase `after`.
- Skenario: `audit/scenarios/r9_cent_origin/gpt_cent_origin.py`; sha256 `c31bae57e613699d9dafdf7e84b75ec3543e8b384387eda50755dd8856bd4f89`; workflow sha256 `6b21b09ce5fa93362a5ac9c49a8642bafe4b22e27b8781fe3e707a3b5bc8e5e8`. Oracle pra-run di `out/gpt_r9_cent_origin_oracle.md` pada commit pemicu.
- Log mencetak `primary_unchanged=true`, `clone_remaining=0`, `production_go=false`, dan `release_evidence=false`. Kasus berjalan di salinan, bukan hosted.

## Hasil kasus (dari JSON Actions, bukan dari dokumen writer)

| ID | Harga sumber sebelum → sesudah | WIP per PO yang diharapkan | WIP per PO teramati | Total WIP | Status |
|---|---|---|---|---:|---|
| `G9O:THREE_STAGGERED_INVOICE_REVERSE_ORDER_UP` | tiga nota 10,00 → 10,005; urutan 3→1→2 | 10,01 / 10,01 / 10,01 | 10,01 / 10,01 / 10,01 | 30,03 | PASS |
| `G9O:THREE_STAGGERED_INVOICE_REVERSE_ORDER_DOWN` | tiga nota 10,01 → 10,004; urutan 3→1→2 | 10,00 / 10,00 / 10,00 | 10,00 / 10,00 / 10,00 | 30,00 | PASS |
| `G9O:THREE_STAGGERED_ONLY_MIDDLE_CORRECTED` | hanya nota tengah 10,00 → 10,015 | 10,00 / 10,02 / 10,00 | 10,00 / 10,02 / 10,00 | 30,02 | PASS |

Ketiga kasus memastikan stok fisik `0.000000` **setelah setiap potong, sebelum pembelian berikutnya**, nilai akhir bahan `0.00`, total WIP benar, dan prefix nilai stok harian tidak negatif. Dokumen sumber dan PO punya ID terpisah; log mencatat sebelum koreksi setiap PO berisi nominal awal, dan koreksi hanya dokumen tengah tidak menggeser dua PO lain.

## Perbedaan dari Fable, dan tafsir terbatas

Fable `xaudit_8.py` run `36123155393`/job `108033136977` mencatat semua tiga penerimaan **sebelum** setiap potong. Pada kondisi stok tercampur itu dua kasus bernilai `COUNTEREXAMPLE` untuk ekspektasi setiap PO sama persis dengan nota sumbernya, walau stok habis dan total WIP benar. Di sini tiap sumber sudah habis sebelum sumber berikutnya datang, sehingga tidak ada pool rata-rata bergerak lintas penerimaan pada saat potong. **Hasil 3/3 PASS tidak menghapus dua COUNTEREXAMPLE beku Fable**, dan tidak membuktikan mereka merupakan bug produk atau memang pembagian sen yang diizinkan kontrak.

Review terbatas `supabase/dev/cp6_ba_t1_family.sql:690–727` menunjukkan implementasi BA memakai rata-rata bergerak dan memperhitungkan selisih nilai sen dokumen pembelian dari stok rata-rata sejak konsumsi sebelumnya. Ini **inferensi dari source**, belum bukti bahwa seluruh jejak HPP per PO benar untuk stok campuran. Master Pulih M:485 memang mengizinkan pembagian sen deterministik untuk *satu biaya kain kantong* antar kelompok jahit; tidak secara eksplisit mengesahkan setiap selisih lintas PO dari tiga nota pembelian. Master M:6632 meminta total, tanggal, dan jejak sumber. Klasifikasi selisih pooled per PO sebagai P3 yang pasti non-blocker masih **UNVERIFIED**. Uji lanjutan yang dapat memutusnya harus menetapkan oracle kontrak biaya rata-rata dan menelusuri koreksi dokumen → movement → PO → FG/COGS, bukan sekadar mencocokkan tiga nilai PO ke tiga nota.

## Errata oracle sendiri (tidak disembunyikan)

Teks oracle prarun di docstring skenario menyebut biaya koreksi harus mencapai PO **"on the cut date"**. Itu redaksi yang keliru untuk nota yang bertanggal sesudah potong: aturan tanggal M:3820 dan keputusan AZ memakai tanggal yang lebih akhir antara invoice dan pemakaian pada periode terbuka. Dalam log, WIP bertambah pada **22 Sep 2026** (tanggal invoice), bukan 17–19 Sep (tanggal potong). Skenario ini **tidak** membandingkan tanggal koreksi ke tanggal potong; assertion PASS menguji nilai per PO, nilai total, stok akhir, dan tidak ada nilai stok harian negatif. File/oracle pra-run, hash dan status tiga kasus tidak diubah; klaim cakupan tanggal dibatasi pada fakta yang benar-benar tercatat di log. Bila perlu penerimaan gate tanggal, buat oracle dan run baru.

## LANGKAH BERIKUTNYA

1. Simpan run/job/status dan errata ke `AUDIT_PROGRESS.md`, commit+push report ini.
2. Untuk mengadili selisih 1 sen Fable pada sumber campuran, turunkan oracle moving-average per movement dan jejak dokumen→PO→FG/COGS dari tiga kontrak, baru tulis skenario lain. Jangan memberi PASS retroaktif atau mengubah dua `COUNTEREXAMPLE` Fable.
3. Semua run baru untuk BB–BE wajib mem-pin head masing-masing; bukti di sini hanya BA pada `d1bc8ad`. CP6 tetap HOLD, `audit_complete=false`, `production_go=false`.
