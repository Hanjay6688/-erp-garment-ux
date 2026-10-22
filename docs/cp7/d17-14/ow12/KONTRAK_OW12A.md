# Kontrak modul angka keuangan/HPP untuk analisis skala pabrik (OW-12a)

Pemilik: A (Claude). Pemakai: B (Astra, OW-12b) dan laporan bertahap milik A. Versi kontrak `cp7.finance-capture.v1`.
Status: kontrak ditulis 23 Okt 2026; modul dibuat di tahap `scripts/cp7_finance_capture/` (uji Native7 di `cp7-ow12a-finance-native.yml`).
Tidak ada RPC publik khusus capture: layar membaca kemajuan lewat status job pemiliknya. B boleh menulis
pemanggilnya mengikuti kontrak ini; perubahan kontrak dicatat di sini lebih dulu.

## Masalah yang diselesaikan

Analisis langsung memasang laporan keuangan resmi (`cp7_finance.workspace`, laporan pemilik Native) plus sidik
seluruh buku besar dalam SATU statement (`cp7_analysis_native.financial_source`). Pada data skala pabrik statement itu
melewati batas 8 detik, jadi analisis bertahap menulis `financial_capture: DEFERRED` dan tidak memuat keuangan/HPP.
Modul ini menghitung angka yang sama dalam beberapa langkah pendek, dengan status kemajuan dan kelengkapan.

## Angka resmi

- Laporan dibaca sekali, dalam satu statement, dari pembaca resmi yang sama dengan layar Laporan Keuangan:
  `cp7_finance.workspace({from,to,as_of,offset:0,limit:25,filing_id:null})`. Tidak ada rumus keuangan baru.
- Hasil berbentuk sama dengan `cp7_analysis_native.financial_source` (kunci `dates`, `book_signature`, `source_hash`,
  `report`) dengan `contract_version: 'cp7.native-analysis-finance.v2'`. Metrik dibuat dengan fungsi yang sama dengan
  analisis langsung: `cp7_analysis_native.finance_apply(v, jsonb_build_object('financial_source', hasil))`.
  Jadi angka per metrik sama persis dengan laporan untuk tanggal yang sama.
- `book_signature` v2 = sidik bertahap atas baris yang sama dengan v1 (jurnal, baris jurnal, saldo harian, akun kas
  sampai `as_of`), dihitung per potongan lalu digabung. Nilainya berbeda dari v1 (cara gabung berbeda), artinya sama:
  penanda sumber.

## Tanggal dan snapshot

- `from`/`to` = `from_date`/`through_date` dari query analysis (`cp7_planning.history_query`); `as_of` = tanggal Jakarta
  dari jam capture analisis (`p_at`), sama dengan aturan analisis langsung.
- Laporan dibaca pada satu snapshot database (dicatat). Potongan sidik dibaca sesudahnya. Bila ada baris jurnal, baris
  jurnal, saldo harian atau akun kas yang berubah sesudah snapshot laporan (dicek per potongan dengan visibilitas
  transaksi, plus jumlah baris per jenis yang dicatat bersama laporan), capture GAGAL `CP7_FINANCE_CAPTURE_SOURCE_CHANGED`.
  Tidak ada campuran angka dari dua waktu.

## Fungsi (privat; dipanggil job yang berjalan sebagai pengguna itu)

| Fungsi | Isi |
|---|---|
| `cp7_finance_capture.start(p_owner_kind text, p_owner_id uuid, p_query jsonb, p_at timestamptz) returns uuid` | `p_owner_kind` `STAGED_ANALYSIS` atau `STAGED_REPORT`; satu capture per (kind, id), panggilan ulang dengan isi sama mengembalikan id yang sama, isi beda ditolak `CP7_FINANCE_CAPTURE_CHANGED` |
| `cp7_finance_capture.step(p_capture uuid) returns jsonb` | satu langkah (laporan, satu potongan sidik, atau segel); mengembalikan status |
| `cp7_finance_capture.status(p_capture uuid) returns jsonb` | lihat bawah; hanya milik pengguna itu |
| `cp7_finance_capture.result(p_capture uuid) returns jsonb` | hanya bila `READY`; selain itu `CP7_FINANCE_CAPTURE_NOT_READY` |
| `cp7_background.run_next()` | penjalan server mendapat keluarga `FINANCE` (capture `RUNNING` tertua), jadi capture jalan walau halaman ditutup |
| `cp7_finance_capture.status_of(p_owner_kind text, p_owner_id uuid)` | status capture milik job itu, atau null bila belum dimulai; dipakai status job (laporan bertahap memuatnya sebagai `finance_capture`) |

Status `cp7.finance-capture-status.v1`:
`{capture_id, owner_kind, owner_id, state: RUNNING|READY|FAILED, units_done, units_total (null sampai laporan
terbaca), report_read_at, readiness: READY|LIMITED|BLOCKED|null, failure_code, dates}`.
`readiness` mengikuti `data_confidence` laporan resmi (READY → READY, RECALC_PENDING → LIMITED, lainnya → BLOCKED), sama
dengan `finance_apply`.

## Hak dan penolakan

- Hanya OWNER/ADMIN dengan `finance.reports.view` (sama dengan laporan keuangan dan analysis langsung). Dicek saat
  `start`, setiap langkah, dan setiap baca. Hak berubah di tengah → GAGAL `CP7_FINANCE_CAPTURE_ACCESS_CHANGED`.
- Laporan lebih lama dari batas statement → GAGAL `CP7_FINANCE_REPORT_TIME_LIMIT`. Tidak ada angka pengganti.
- Kode gagal lain: `CP7_FINANCE_CAPTURE_SOURCE_CHANGED`, `CP7_FINANCE_CAPTURE_ACCESS`, `CP7_FINANCE_CAPTURE_CHANGED`,
  `CP7_FINANCE_REPORT_INCOMPLETE` (dari pembaca resmi).

## Yang dilakukan B (OW-12b) dengan kontrak ini

1. Saat permintaan analisis bertahap oleh pengguna yang berhak dan memilih keuangan: `start('STAGED_ANALYSIS', job_id,
   query, captured_at)`; header mencatat `financial_capture: 'STAGED'` dan id capture.
2. Hasil operasional tetap keluar lebih dulu, tidak menunggu keuangan.
3. Bagian keuangan menampilkan status capture (langkah selesai/total, jam laporan dibaca, kesiapan).
4. Sesudah `READY`, metrik keuangan dibuat dengan `finance_apply` atas `result`. Sebelum itu tidak ada metrik laba/biaya
   dan kesimpulan laba/biaya ditandai menunggu (bukan nol).
5. Karena header analisis disegel, bagian keuangan disimpan terpisah dan ditautkan ke run lewat id capture.

## Yang dilakukan A dengan kontrak ini

- Laporan bertahap (Business Report v2): unit ACTUALS memakai capture `STAGED_REPORT`, bukan pembacaan langsung yang
  melewati batas di skala pabrik.
- Pembanding periode: dua laporan bertahap terbit dibandingkan per metrik resmi (sesudah dikurangi sebelum), dengan
  aturan yang sama dengan pembanding laporan v1 (`cp7_analysis_native.report_compare`).

## Pembanding periode (milik A, sudah dibuat)

`public.erp_cp7_compare_reports_v2(p_before uuid, p_after uuid)` → `cp7.report-comparison.v2`: dua laporan bertahap terbit
milik pengguna itu, dibaca dengan hak yang sama seperti membukanya; baris per metrik keuangan resmi yang tersimpan di
laporan (`finance_apply` atas keuangan masing-masing), selisih = sesudah − sebelum hanya bila kedua angka diketahui; bila
hanya satu laporan memuat keuangan: `FINANCE_NOT_IN_BOTH_REPORTS`. Layar: "Bandingkan dengan laporan" di panel laporan
bertahap.
