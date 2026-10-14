# ASTRA-CP17-FIN-02 — Klaim laundry dilunasi sebelum sumber dan utangnya ada

**TERBUKTI, S0: saldo utang vendor bertanggal negatif dan laba masuk ke hari sebelum sumber klaim.** Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, FULL composition. Petunjuk Fable R3-03; oracle, fixture sah, dan eksekusi independen Astra sesudah exposure yang diizinkan owner. Berbeda native owner dari FIN01, sehingga dicatat sebagai akar terpisah.

Run `38568716349`, job `115867957632`, control commit `c547c196d092776df7580298bbc780120ccefc32`. Original artifact `11897120989`, SHA256 `11379d4eff3e8261aff5b2a82f1cf840e57794f87d56fb32dbaac1d3e08b3928`. Source dan manifest dikunci sebelum run. `CP17-ASTRA-CLAIM-01-SAME-DAY-CONTROL` PASS; `CP17-ASTRA-CLAIM-02-BEFORE-SOURCE` COUNTEREXAMPLE. Batas database/public dipulihkan, lock nol, sesi kosong, outer restoration/advisor true. Outer INCOMPLETE berasal dari gate semua kasus harus PASS; bukan setup yang gagal mencapai writer.

## Reproduksi sah

1. Buat vendor baru, kirim 5 PCS melalui writer bisnis, terima GOOD 4 pada **9 Oktober**. Ada 1 PCS belum kembali sehingga klaim **MISSING** 1 sah; tidak memerlukan BS fiktif.
2. POST invoice vendor 4 × 20 = **80** pada 9 Oktober. Tidak ada utang vendor ini sebelum tanggal itu.
3. SAVE_CLAIM MISSING 1, opened_at 9 Oktober; kemudian ACCEPTED dengan kompensasi **20** dan resolution_date **8 Oktober**.
4. RESOLVE_CLAIM SETTLED diterima. Native menulis jurnal kompensasi 20 pada 8 Oktober, sehari sebelum invoice dan sumber klaim.

| Ukuran | Sebelum | Setelah |
|---|---:|---:|
| AP vendor cutoff 8 Oktober | 0 | **−20** |
| AP vendor sekarang | 80 | 60 |
| Liabilities laporan 8 Oktober | 1859 | **1839** |
| Net profit / current earnings 8 Oktober | 0 | **20** |
| Operating and other expense 8 Oktober | 0 | **−20** |
| Assets 8 Oktober | 1859 | 1859 |
| Balance difference | 0 | 0 |

Kontrol berbeda yang memakai fixture sama dan resolution_date **9 Oktober** berhasil: dated AP 80 → 60. Jadi kegagalan bukan izin, transaksi aborted, atau kekurangan BS seperti tiga percobaan Fable yang dibahas dalam rekap.

Original lengkap: `ASTRA_CP17_CLAIM_DATE_True_FIRST.json`, kontrol False, `CP17_OWN_CASES_CLAIM_DATE.json`, dan outer `ASTRA_CP17_OWN_INTEGRATION.json`. Ekstraksi bernama `CLAIM_DATE_OBSERVATION.json` mengikat hash Original dan hasil sebelum/sesudah.

## Detector dan batas bukti

Seluruh **135** baris detector yang diambil (18 integrity, 49 v267, 68 v268) identik sebelum/sesudah dan issue=0. Confidence serta close preflight **BLOCKED sebelum dan sesudah**, dengan delapan blocker seed yang sama: empat absensi kosong, tiga pekerjaan belum masuk payroll, satu payroll belum disetujui. Tidak ada blocker baru tentang klaim bertanggal ini. **Tidak diklaim false READY atau setiap banner browser diam.** Tidak ada browser baru atau business reversal untuk saksi ini; rollback runner dan cleanup adalah bukti pemulihan uji, bukan bukti alur reversal produk.

Kasus yang dibuktikan MISSING; varian DAMAGE dan STUCK tidak otomatis dianggap sudah terbukti. Total vendor saat ini tetap positif; cacatnya ada pada periode pengakuan dan saldo bertanggal. Nilai fixture adalah unit rupiah sederhana, bukan dampak nominal seluruh pabrik.

## Penyebab dan perbaikan

Native `erp.resolve_laundry_claim` pada `supabase/release/cp6-t3/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql` hanya membatasi tanggal masa depan. Pemeriksaan kapasitas kompensasi menjumlah **utang vendor sekarang tanpa cutoff tanggal**, lalu `post_journal` memakai resolution_date yang lebih lama. SAVE_CLAIM menyimpan tanggal tersebut tanpa mengikatnya pada kronologi sumber. Perilaku pada FULL composition membuktikan guard hilir tidak mencegah saksi ini.

Perbaiki pada native owner settlement: kompensasi harus mempunyai sumber yang sah dan utang yang tersedia pada tanggal pengakuannya; pertahankan pembedaan tanggal ekonomi dan tanggal buku untuk periode tertutup. Jangan mengganti aturan D12: kredit klaim yang datang kemudian tetap boleh melunasi tagihan vendor lain/lebih lama. Temuan ini tentang kredit yang dibukukan **sebelum klaim dan seluruh AP vendor**, bukan larangan lintas tagihan.

Penerimaan kandidat baru: kasus early asli ditolak atomik tanpa perubahan laporan/jurnal/request; kontrol same-day/later dan D12 lintas tagihan tetap selesai; MISSING/STUCK/DAMAGE yang memenuhi prasyarat, kapasitas parsial, replay, concurrent offset, closed-period correction serta reversal diuji. Periksa detector positif/negatif dan laporan cutoff sebelum/saat/sesudah, lalu browser desktop/HP + server reread. Perubahan maju; migrasi historis tidak diedit.
