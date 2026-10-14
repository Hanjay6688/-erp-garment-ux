# Kandidat perbaikan CP1–CP7 r1 — uji ulang Fable, Astra, Sol

Ketiga audit penuh CP1–CP7 atas `0b7049d9` sudah dikunci (Fable, Astra: TAHAN; Sol: HOLD). Owner menjawab
D14-2..D14-7 dan berkata "lanjut". Folder ini berisi perbaikan penulis dan kandidat yang diserahkan untuk **uji ulang**.
Ini bukan penerimaan; setiap auditor memutuskan sendiri. `production_go:false`.

| Berkas | Isi |
|---|---|
| `README.md` | Identitas kandidat, apa yang berubah per temuan, bukti penulis, butir yang masih terbuka |
| `FINDINGS_TRACKER.md` | Daftar gabungan temuan ketiga auditor per akar masalah, rencana, dan status (bagian G) |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak teks yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua workflow dan job pada commit kandidat (dibuat `scripts/cp7_ci_receipt.py`) |
| `SG01_PICKUP_REVERSAL.md`, `SG01_PICKUP_CORRECTION_DESIGN.md` | Batal Bagi Potongan sebelum dijahit |
| `SG02_FABRIC_RETURN.md` | Kain kembali ke gudang (D14-4) |
| `KASBON_D14_6.md` | Kasbon tunai (D14-6) |
| `DOC_FINDINGS_FABLE_002_003_004_RLS.md` | FABLE-002/003/004 dan 4 tabel tanpa RLS (Fable A1) |
| `FIRST_RUN_597d6778.md` | Log gagal pertama penjaga kas (disimpan, tidak diubah) |

## Identitas kandidat

Diisi pada saat kualifikasi, lihat bagian akhir berkas ini ("Kualifikasi satu commit").

- Basis audit: `0b7049d9203bac52b47a4c89f3e0d75646067a8f` (tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`).
- `supabase/` **tidak berubah** sejak basis (`git diff --name-only 0b7049d9 <kandidat> -- supabase` kosong): paket rilis
  CP6 T3 (30 berkas AC..BF) dan semua migrasi identik byte. Semua perubahan produk ada di lapisan CP7
  (`scripts/cp7-src/`, dipasang lewat bundle F03 dengan delta Native yang dideklarasikan) dan di `src/`.
- Panduan audit: `docs/AUDIT_PANDUAN_PRO_MAX.md`, SHA-256
  `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`, sama dengan pada basis.
- Keputusan owner baru: D14-1..D14-7 di `docs/cp7/OWNER_DECISIONS_20261008.md`.

## Apa yang berubah, per temuan

Status di bawah adalah klaim penulis yang diuji CI; auditor mengujinya ulang. ID kasus mengacu ke
`docs/cp7/cp17/CP17_FIXES.json` (deklarasi kasus dibuat sebelum dijalankan; 40 kasus: native 31, race 2, HTTP 4,
browser 3).

| Temuan | Perbaikan | Bukti penulis |
|---|---|---|
| FABLE-001, Astra FIN01 (R-FIN01) | D14-2: bayar upah (penuh, cicilan) ditolak bila tanggal bayar mendahului utang upah yang dilunasi; kasbon tetap jalur sendiri. Penjaga di perintah CP7 dan di pemicu Native transisi PAID. Detektor `cp7_guard.findings()` mendaftar data lama | `CP17_FIN01_*` (4), `CP17_DETECTOR_LISTS_LEGACY_ROWS`, `CP17_HTTP_PAYROLL_EARLY_REFUSED` |
| Sol SOL-001 (R-CASH01) | D14-3: kas/bank tidak boleh minus pada tanggal mana pun, juga sesudah pembayaran bertanggal mundur; satu penjaga bersama per rekening, dikunci per rekening. Kasus mencakup supplier, upah, vendor laundry dan kasbon | `CP17_CASH_*` (6), `CP17_RACE_TWO_PAYMENTS_ONE_BANK`, `CP17_HTTP_CASH_EMPTY_BANK_REFUSED` |
| FABLE-008, Astra FIN02 (R-FIN02) | Penyelesaian klaim laundry tidak boleh bertanggal sebelum klaim dan utang vendor sumbernya | `CP17_FIN02_*` (3) |
| Astra STK01 | Kartu stok sesudah REOPEN lalu POST ulang potongan tidak lagi minus | `CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE` |
| FABLE-006, Astra RWK01 | Upah rework yang sudah jadi utang tetap bisa masuk Nota walau semua hasil SCRAP, sekali saja | `CP17_RWK01_*` (3) |
| Astra HPP01 | Kebijakan HPP yang mengubah peserta pool ACTIVE ditolak; jalur batal → pool pengganti | `CP17_HPP01_*` (3) |
| FABLE-009, Astra SG-01 | Batal Bagi Potongan yang sudah POSTED sebelum ada proses lanjutan, dengan 2 delta Native yang dideklarasikan; sesudah dijahit tetap ditolak dan penghalangnya disebut | `CP17_SG01_*` (2), `CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP`, `SG01_PICKUP_REVERSAL.md` |
| FABLE-010, Astra SG-02 | D14-4: kain kembali ke gudang per roll, nilai masuk stok lagi, biaya PO turun | `CP17_SG02_*` (4), `CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE`, `SG02_FABRIC_RETURN.md` |
| Astra SG-03 | Tanpa jalur tagihan baru (sudah diputus D06): cuci ulang produk sama tanpa tagihan vendor dibuktikan | `CP17_SG03_REWASH_SAME_PRODUCT_NO_VENDOR_BILL` |
| D14-6 kasbon | Beri kasbon tunai, potong dari payroll draf, batal bila belum dipakai; tunduk D14-3 | `CP17_KASBON_*` (3), `CP17_HTTP_KASBON_GIVE`, `CP17_BROWSER_KASBON_GIVE_DEDUCT_DESKTOP`, `KASBON_D14_6.md` |
| D14-5 lusin seri | Bagi lusin otomatis ke satu seri ukuran, dua arah, di draf penjualan | Uji unit `src/sales/seriesDozens.test.ts` dan uji panel `src/SalesDraftPanel.dom.test.tsx`. **Belum ada uji browser khusus** (lihat butir terbuka) |
| FABLE-007 (dugaan absensi dobel) | Tidak ada perubahan produk. Penjaganya ada di skema dasar (bukan di migrasi pohon ini): `erp.guard_payroll_period_overlap` mengunci per mandor lalu menolak payroll aktif kedua yang periodenya bertumpuk (`supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz` baris 10325-10342). Ditemukan karena uji pertama penulis ditolak penjaga ini saat menyiapkan data (run 38631233950) | `CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS`: payroll kedua di atas hari absensi ditolak; dua payroll bertumpuk dikirim bersamaan, satu lolos; tidak ada absensi di dua payroll |
| FABLE-012, Astra RBAC (R-ACC01) | Inventaris 160 fungsi `erp` yang bisa dijalankan `authenticated`; 82 penulis tanpa rujukan dari kode yang berjalan dengan hak pemanggil dibuktikan **tidak terjangkau dari Data API** (Auth nyata, 406 PGRST106, hanya skema `public` terbuka). Pencabutan EXECUTE belum dilakukan (pertanyaan owner) | `CP17_HTTP_ERP_WRITERS_NOT_REACHABLE`, `scripts/cp7_access_inventory.py` |
| FABLE-002/003/004, Fable A1 (R-DOC01..05) | Pemeriksaan salinan paket rilis (30 berkas) dari sumber; komentar basi dibetulkan; bukti CP1/CP2 dibawa ke pohon dengan hash; 4 tabel tanpa RLS dijelaskan dari riwayat migrasi | `scripts/cp7_release_copy_check.py`, `docs/evidence/cp1-cp2/`, `DOC_FINDINGS_FABLE_002_003_004_RLS.md` |
| FABLE-005 (R-DOC04) | Pemetaan 75 C6 + 22 ALL sudah dibuat Astra; penulis hanya menautkan | `audit/astra_cp17/followup-681dd7a9/C6_75_ALL22_CROSSWALK.md` di cabang Astra (`d4a83b42`) |
| Sol SOL-002 (R-EV01) | Folder keluaran BE tidak lagi dipindah saat impor AV; gerbang unggah memeriksa himpunan ID, status, dan hasil akhir | `scripts/cp6_av_probe.py`, `scripts/cp6_be_probe.py` |
| Sol SOL-003, OPEN-AZ-FIRST (R-EV02) | Diagnosis PostgreSQL disimpan di berkas terpisah (termasuk proses lain di database saat gagal). Penyebab paling mungkin kegagalan pertama di AZ: autovacuum masuk ke database yang sudah ditutup, dan blok pertama AZ menolak. Log Sol tidak menyebut blok mana yang menolak, jadi ini **belum terbukti**. Pemasang menunggu proses lain keluar sebelum tiap berkas dan hanya mengulang penolakan `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE` (teks pengaman tidak berubah) | `scripts/cp6_readiness_owner_install.py`, `scripts/cp6_readiness_owner_drain_test.py` (6 kasus, juga jalan di workflow CP17) |

Perbaikan lain yang ditemukan saat mengerjakan putaran ini:
- Data uji lama di `CP7 P08 Physical Fabric` (job `attention284`, 4 kasus) membayar dari rekening kosong dan kini ditolak
  penjaga kas D14-3 (run 38633926468, log disimpan). Data uji diberi modal owner lewat jurnal Native; penjaga tidak diubah.
- Panel kasbon menutup diri dan menghapus pesan "kasbon tercatat" saat halaman payroll memuat ulang (uji DOM baru).
- Di HP, panel kain kembali membuat halaman Bagi Potongan 722 piksel di layar 412 piksel; sekarang muat di layar.
- Workflow `CP6 T3 Release Package`: bagian browser merah sejak 6 Okt karena memasang tampilan CP7 di atas database
  CP6 saja. Sekarang memakai tampilan CP6 beku `e43e0ed4` yang dulu lulus 31/31; tidak ada assertion yang diubah.

## Butir terbuka (bukan diklaim selesai)

| Butir | Status |
|---|---|
| A2 urutan daftar fungsi di pembanding (`cp6_auditor_runner.py:35`, `order by 1`) | Akar masalah ditemukan; perubahan menunggu izin owner (D13-11) |
| FABLE-012 pencabutan EXECUTE langsung | Menunggu owner: sekitar 700 pemanggilan langsung di 194 berkas alat uji lama ikut tertolak. Pembacaan setelan hosted oleh Fable (D14-7) |
| RWK01 kasus BS OPEN/PARTIAL | Upah tetap belum bisa dibayar sampai owner memutuskan |
| SG-02 pembatalan kain kembali | Belum ada (Native juga tidak punya); pertanyaan owner |
| SG-01 tingkat (b): ganti Mandor sesudah dijahit | Tetap ditolak, sesuai rancangan |
| D14-5 uji browser khusus seri lusin | Belum; butuh fixture stok 3 ukuran satu SKU |
| FABLE-011 lantai tanggal cutover | Tidak diubah tanpa keputusan owner |
| CP7C (backup awal Enteng, uji Drive) | Ditahan (D13-9a) |

## Kualifikasi satu commit

Diisi setelah semua workflow selesai pada commit kandidat.
