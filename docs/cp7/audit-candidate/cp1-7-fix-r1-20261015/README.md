# Kandidat perbaikan CP1–CP7 r1 — uji ulang Fable, Astra, Sol

Ketiga audit penuh CP1–CP7 atas `0b7049d9` sudah dikunci (Fable, Astra: TAHAN; Sol: HOLD). Owner menjawab
D14-2..D14-7 dan berkata "lanjut", lalu D14-5 (lusin) dan D14-8..D14-11 (empat pertanyaan penulis). Folder ini berisi perbaikan penulis dan kandidat yang diserahkan untuk **uji ulang**.
Ini bukan penerimaan; setiap auditor memutuskan sendiri. `production_go:false`.

| Berkas | Isi |
|---|---|
| `README.md` | Identitas kandidat, apa yang berubah per temuan, bukti penulis, butir yang masih terbuka |
| `FINDINGS_TRACKER.md` | Daftar gabungan temuan ketiga auditor per akar masalah, rencana, dan status (bagian G) |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak teks yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua workflow dan job pada commit kandidat (dibuat `scripts/cp7_ci_receipt.py`) |
| `SG01_PICKUP_REVERSAL.md`, `SG01_PICKUP_CORRECTION_DESIGN.md` | Batal Bagi Potongan sebelum dijahit |
| `SG02_FABRIC_RETURN.md` | Kain kembali ke gudang (D14-4) dan batal/betulkan (D14-10) |
| `KASBON_D14_6.md` | Kasbon tunai (D14-6) |
| `A2_COMPARATOR_D14_8.md` | Pembanding skema `public` dengan urutan stabil (D14-8), bukti sebelum/sesudah |
| `FABLE012_D14_9_GATE.md` | Pencabutan 82 penulis ditunda ke CP7C, dengan gerbang (D14-9) |
| `RWK01_D14_11.md` | Upah rework untuk bagian yang selesai walau kasus BS terbuka (D14-11) |
| `DOC_FINDINGS_FABLE_002_003_004_RLS.md` | FABLE-002/003/004 dan 4 tabel tanpa RLS (Fable A1) |
| `FIRST_RUN_597d6778.md` | Log gagal pertama penjaga kas (disimpan, tidak diubah) |

## Identitas kandidat

- **Commit `f1a1ae6926ed563b960f476125c5e2273e750157`**, tree `982831d6e788b2a3a9404f25a4617230e0b98f0b`, cabang `claude/new-session-deapao`. Commit sesudahnya hanya dokumen
  (`git diff --name-only f1a1ae69 <head cabang>` semuanya di bawah `docs/`). Kandidat sebelumnya `55d72775` (25/25);
  yang berubah sesudahnya: D14-5, D14-8, D14-9, D14-10, D14-11 (`git diff 55d72775 f1a1ae69 -- src scripts .github`),
  ditambah tiga perbaikan alat uji yang muncul saat kualifikasi (`cp7_catalog_state.py` membaca entri D14-8;
  `cp6_av_runtime.py` mengulang penolakan "database belum kosong" seperti `change()`; uji pembanding
  `f05-timeline` diberi batas 180 detik hanya untuk proses pembanding), lihat `A2_COMPARATOR_D14_8.md` dan bagian Kualifikasi.
  Tidak ada oracle atau pengaman yang dilonggarkan.
- Tree per direktori pada kandidat:

| Direktori | Tree |
|---|---|
| `src` | `e42e0b76daf58d0b027def2ce34acbfe7e2b48a1` |
| `supabase` | `5d040436db384b4e574785376367b360a084acb7` (sama dengan pada `0b7049d9`) |
| `scripts/cp7-src` | `41432799fd3b2a47efc5586dfef16eeb3f5e17fe` |
| `scripts` | `ba2a646d24f38fcdce54eaf16af429b418da28fa` |
| `.github/workflows` | `7460072a804388b8514e7df2b3b677a51d747c9f` |
| `tests` | `18a0543319657bfa078e74a7684031395d0812d2` |

- Basis audit: `0b7049d9203bac52b47a4c89f3e0d75646067a8f` (tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`).
- `supabase/` **tidak berubah** sejak basis (`git diff --name-only 0b7049d9 <kandidat> -- supabase` kosong): paket rilis
  CP6 T3 (30 berkas AC..BF) dan semua migrasi identik byte. Semua perubahan produk ada di lapisan CP7
  (`scripts/cp7-src/`, dipasang lewat bundle F03 dengan delta Native yang dideklarasikan) dan di `src/`.
- Panduan audit: `docs/AUDIT_PANDUAN_PRO_MAX.md`, SHA-256
  `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`, sama dengan pada basis.
- Keputusan owner baru: D14-1..D14-11 di `docs/cp7/OWNER_DECISIONS_20261008.md` (D14-8..D14-11 ditulis persis).

## Apa yang berubah, per temuan

Status di bawah adalah klaim penulis yang diuji CI; auditor mengujinya ulang. ID kasus mengacu ke
`docs/cp7/cp17/CP17_FIXES.json` (deklarasi kasus dibuat sebelum dijalankan; 48 kasus: native 36, race 2, HTTP 4,
browser 6).

| Temuan | Perbaikan | Bukti penulis |
|---|---|---|
| FABLE-001, Astra FIN01 (R-FIN01) | D14-2: bayar upah (penuh, cicilan) ditolak bila tanggal bayar mendahului utang upah yang dilunasi; kasbon tetap jalur sendiri. Penjaga di perintah CP7 dan di pemicu Native transisi PAID. Detektor `cp7_guard.findings()` mendaftar data lama | `CP17_FIN01_*` (4), `CP17_DETECTOR_LISTS_LEGACY_ROWS`, `CP17_HTTP_PAYROLL_EARLY_REFUSED` |
| Sol SOL-001 (R-CASH01) | D14-3: kas/bank tidak boleh minus pada tanggal mana pun, juga sesudah pembayaran bertanggal mundur; satu penjaga bersama per rekening, dikunci per rekening. Kasus mencakup supplier, upah, vendor laundry dan kasbon | `CP17_CASH_*` (6), `CP17_RACE_TWO_PAYMENTS_ONE_BANK`, `CP17_HTTP_CASH_EMPTY_BANK_REFUSED` |
| FABLE-008, Astra FIN02 (R-FIN02) | Penyelesaian klaim laundry tidak boleh bertanggal sebelum klaim dan utang vendor sumbernya | `CP17_FIN02_*` (3) |
| Astra STK01 | Kartu stok sesudah REOPEN lalu POST ulang potongan tidak lagi minus | `CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE` |
| FABLE-006, Astra RWK01 | Upah rework yang sudah jadi utang tetap bisa masuk Nota walau semua hasil SCRAP, sekali saja. D14-11: bagian yang selesai dan terposting bisa dibayar walau kasus BS masih OPEN/PARTIAL; yang belum selesai ditahan; tidak dibayar ulang saat kasus ditutup | `CP17_RWK01_*` (3), `RWK01_D14_11.md` |
| Astra HPP01 | Kebijakan HPP yang mengubah peserta pool ACTIVE ditolak; jalur batal → pool pengganti | `CP17_HPP01_*` (3) |
| FABLE-009, Astra SG-01 | Batal Bagi Potongan yang sudah POSTED sebelum ada proses lanjutan, dengan 2 delta Native yang dideklarasikan; sesudah dijahit tetap ditolak dan penghalangnya disebut | `CP17_SG01_*` (2), `CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP`, `SG01_PICKUP_REVERSAL.md` |
| FABLE-010, Astra SG-02 | D14-4: kain kembali ke gudang per roll, nilai masuk stok lagi, biaya PO turun. D14-10: batal/betulkan dalam satu transaksi, riwayat asli tetap, pemakaian sesudahnya disebut dan menghalangi | `CP17_SG02_*` (8), `CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE`, `CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP`, `SG02_FABRIC_RETURN.md` |
| Astra SG-03 | Tanpa jalur tagihan baru (sudah diputus D06): cuci ulang produk sama tanpa tagihan vendor dibuktikan | `CP17_SG03_REWASH_SAME_PRODUCT_NO_VENDOR_BILL` |
| D14-6 kasbon | Beri kasbon tunai, potong dari payroll draf, batal bila belum dipakai; tunduk D14-3 | `CP17_KASBON_*` (3), `CP17_HTTP_KASBON_GIVE`, `CP17_BROWSER_KASBON_GIVE_DEDUCT_DESKTOP`, `KASBON_D14_6.md` |
| D14-5 lusin seri | Seperti UX demo: satu pilih menambah semua ukuran SKU yang ada stoknya, seri baru mulai 1 lusin; dua arah (3/5/4 → "1 lusin"); SKU satu ukuran: 1 lusin = 12 | Uji unit, uji panel, browser `CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP` dan `_MOBILE` |
| FABLE-007 (dugaan absensi dobel) | Tidak ada perubahan produk. Penjaganya ada di skema dasar (bukan di migrasi pohon ini): `erp.guard_payroll_period_overlap` mengunci per mandor lalu menolak payroll aktif kedua yang periodenya bertumpuk (`supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz` baris 10325-10342). Ditemukan karena uji pertama penulis ditolak penjaga ini saat menyiapkan data (run 38631233950) | `CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS`: payroll kedua di atas hari absensi ditolak; dua payroll bertumpuk dikirim bersamaan, satu lolos; tidak ada absensi di dua payroll |
| FABLE-012, Astra RBAC (R-ACC01) | Inventaris 160 fungsi `erp` yang bisa dijalankan `authenticated`; 82 penulis tanpa rujukan dari kode yang berjalan dengan hak pemanggil dibuktikan **tidak terjangkau dari Data API** (Auth nyata, 406 PGRST106, hanya skema `public` terbuka). D14-9: pencabutan EXECUTE ditunda ke CP7C sebagai pekerjaan keamanan terbuka; gerbang menolak membuka `erp` ke Data API sebelum pencabutan | `CP17_HTTP_ERP_WRITERS_NOT_REACHABLE`, `CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST`, `FABLE012_D14_9_GATE.md` |
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
| A2 penyebab dua kegagalan lama | Pembanding sudah dibetulkan (D14-8, `A2_COMPARATOR_D14_8.md`); penyebab dua kegagalan lama tetap OPEN (D13-10) |
| FABLE-012 pencabutan EXECUTE langsung | Pekerjaan keamanan terbuka di CP7C (D14-9), dijaga gerbang. Pembacaan setelan hosted oleh Fable (D14-7) |
| SG-02 batal/betulkan kain kembali | Dibuat (D14-10). Batas: dicatat pada saat disimpan; hari-hari di antaranya tetap menunjukkan angka lama |
| SG-01 tingkat (b): ganti Mandor sesudah dijahit | Tetap ditolak, sesuai rancangan |
| FABLE-011 lantai tanggal cutover | Tidak diubah tanpa keputusan owner |
| CP7C (backup awal Enteng, uji Drive) | Ditahan (D13-9a) |

## Kualifikasi satu commit

`CI_RECEIPT.json` (dibuat `scripts/cp7_ci_receipt.py f1a1ae69`): **25/25 workflow, 69/69 job sukses** pada
`f1a1ae6926ed563b960f476125c5e2273e750157`. Tidak ada grup yang diulang karena pergantian hari WIB.

- `CP6 AV Rev2 Qualification` (run 38676811934) lulus pada percobaan ke-2. Pada percobaan pertama job "AT 16 and AU 15"
  mati di langkah "Start disposable database" (`supabase start`) sebelum satu pun pengecekan berjalan. Hanya job yang
  gagal diulang, satu kali.
- Jalan menuju kandidat ini (semua log gagal tersimpan di run masing-masing; tidak ada oracle atau pengaman yang
  dilonggarkan):
  - `a3cb1beb`/`f2f5835c`: pembanding D14-8 versi pertama salah tulis `COLLATE` → 5 workflow gagal di awal; dibetulkan
    `59fc7baf`.
  - `59fc7baf` CP17 run 38666407687: 2 kasus SG-02 batal/betulkan gagal karena alat uji membaca WIP PO hanya dari jurnal
    POSTED; dibetulkan ke aturan buku besar Native di `4daee0e1` (produk tidak diubah).
  - `4daee0e1`/`a0cd5782`: langkah bukti D14-8 gagal karena pengguna CI bukan superuser; dibetulkan `ad64c4c9`.
  - `ad64c4c9` F03 Full run 38668243786: `cp7_catalog_state.py` masih membaca bentuk entri lama; dibetulkan `b13394cc`.
  - `b13394cc` AV run 38670698254: penolakan "database belum kosong" saat uji post-use; diulang seperti `change()` di
    `e8ce4b89`.
  - `e8ce4b89` Shell S0 run 38673762153: uji pembanding `f05-timeline` melewati batas 60 detik karena fungsi pendahulu
    yang dibandingkan kuadratik (produk 0,3 detik); hanya proses pembanding diberi 180 detik di `f1a1ae69`.
- Workflow yang dijalankan: Build UX, CodeQL (T3), Astra Timeline Reuse, Backup Kit Check, F03 Full, Note Correction,
  Offsite Backup, Owning Receipt Correction, P08 Physical Fabric, P12 Payroll, P13 Finance, P18 Fabric Rule, P18 Full
  Cycle, P19 Analysis Job Transport, P21 Rehearsal, PL Native Planning, Pre-freeze UI Regression, Shell S0, Supplier
  Payment Correction, Supplier Payment Create, CP17 Fixes, CP6 T3 Release Package, CP6 T3 Rollback, CP6 BE T1 Family
  Probe, CP6 AV Rev2 Qualification.
- Tidak dijalankan penulis pada kandidat ini (bukti terakhirnya di commit lama; auditor menentukan sendiri):
  workflow era CP3–CP5, `cp6-*-t1-probe` selain BE, CP6 T2 Combined Regression, CP6 Release Readiness (terikat cabang
  `cp6/release-readiness`), CP6 Auditor Scenario.
