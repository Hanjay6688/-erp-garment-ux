# UJI ULANG FABLE r1 — kandidat dfab13bf62398a69a02bf6221c06d29075e5e40b, tree 886f8331 — 2026-10-15 (bagian A paket D14-16)

Auditor: Fable, independen, baca-saja terhadap produk. Dasar: laporan terkunci `AUDIT_FABLE_0b7049d9.md` v1.0
(sha256 7fd1ca97…) dan addendum A1, A2, A3 di cabang `audit/fable-cp1-7-0b7049d9-20261014`.
Kepala penulis saat run: `65628336` (beda dari kandidat hanya 11 berkas `docs/`; pohon produk sama, lihat `MANIFEST.md`).
Status per kasus dibaca dari baris JSON log (bukan warna job). Rincian run: `WORKLOG.md`. `production_go: false`.

## Ringkasan

12 temuan lama: **9 DITUTUP** (FABLE-003 dengan catatan), **3 MASIH TERBUKA** (FABLE-005 buktinya di luar pohon kandidat;
FABLE-011 menunggu keputusan owner; FABLE-012 ditunda ke CP7C oleh keputusan D14-9). Temuan BARU putaran ini ada di
`FINAL_FABLE.md` (FABLE-013 sampai FABLE-017). FABLE-013 menyentuh perbaikan r1 secara langsung: penjaga kas D14-3
lulus semua kasus penulis, tetapi dengan dasar tanggal yang berbeda dari laporan kas pemilik. Contoh-penyangkalnya terbukti
di run 38786227211.

## Status per temuan

| Temuan | Status | Bukti (label) |
|---|---|---|
| FABLE-001 (S1) bayar upah sebelum utangnya ada | **DITUTUP** | Sumber: `cp7_payroll.assert_payment_date` dipanggil di PAY (`settlement-write.sql`), cicilan (`installments.sql`), dan trigger `cp7_payroll_paid_date_guard` saat status menjadi PAID untuk semua pemanggil; baris PAID beku untuk pengguna aplikasi (`erp.guard_payroll_lifecycle`) (INDEPENDENT_SOURCE_REVIEW). Skenario saya yang dulu membuktikan −180 kini ditolak `CP7_PAYROLL_PAID_BEFORE_ACCRUAL` (run 38786127478 dan 38786142567, FABLE). Kasus penulis `CP17_FIN01_*` 4 PASS, `CP17_HTTP_PAYROLL_EARLY_REFUSED` PASS (run 38784255332, INDEPENDENT_NATIVE_RERUN). Catatan: superuser/service_role tetap bisa melewati penjaga lifecycle Native; itu bukan jalur aplikasi |
| FABLE-002 (S3) dua salinan migrasi AC | **DITUTUP** | `scripts/cp7_release_copy_check.py` saya jalankan sendiri di kandidat: exit 0, `"files": 30, "status": "PASS"`, hanya baris pin penjaga yang berbeda (`runs/RELEASE_COPY_CHECK_dfab13bf.txt`, FABLE). Salinan paket dinyatakan kanonik di dokumen R-DOC01 |
| FABLE-003 (S3) manifest `rollbacks: NOT_TESTED` | **DITUTUP dengan catatan** | Nilai di `supabase/release/cp6-t3/MANIFEST.json` baris 2789 tetap `NOT_TESTED` (nilai saat paket dibangun; berkas dipin hash). Penjelasan ditambahkan di generator dan `DOC_FINDINGS_FABLE_002_003_004_RLS.md`; rollback AC..BF lulus 148/148 di run 38784311913 (INDEPENDENT_NATIVE_RERUN). Pembaca yang hanya membuka manifest masih melihat `NOT_TESTED` |
| FABLE-004 (S3) bukti CP1/CP2 tidak di pohon | **DITUTUP** | `docs/evidence/cp1-cp2/` berisi 9 berkas (sidik CP1, revalidasi 1 Sep, generator/verifier/workflow restore CP2, MANIFEST, README). Tidak ada nilai rahasia; hanya mekanisme berkas kunci (INDEPENDENT_SOURCE_REVIEW). Verifikasi isi sudah saya lakukan di A1/A2 |
| FABLE-005 (S3) rencana 75 C6 + 22 ALL tanpa bukti eksekusi | **MASIH TERBUKA** | Penulis menautkan pemetaan di cabang Astra (`audit/astra_cp17/followup-681dd7a9/...`, `d4a83b42`). Pemetaan itu tidak ada di pohon kandidat, dan menurut aturan §16.7 tidak saya buka sebelum laporan ini dikunci. Bisa ditutup bila pemetaan dibawa ke pohon kandidat atau dibaca sesudah penguncian |
| FABLE-006 (dugaan) upah rework hilang bila semua hasil SCRAP | **DITUTUP** | `CP17_RWK01_ALL_SCRAP_REWORK_PAYABLE_ONCE`, `_GOOD_CONTROL`, `_OPEN_CASE_FINISHED_PART_PAID_ONCE` PASS (run 38784255332, INDEPENDENT_NATIVE_RERUN); aturan D14-11 |
| FABLE-007 (dugaan) absensi dobel di payroll bertumpuk | **DITUTUP — dugaan saya salah** | Penjaga Native `erp.guard_payroll_period_overlap` (skema dasar, bukan migrasi pohon) berlaku untuk semua pemanggil (INDEPENDENT_SOURCE_REVIEW); `CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS` PASS (run 38784255332) |
| FABLE-008 (dugaan) klaim laundry bertanggal sebelum sumbernya | **DITUTUP** | Trigger `cp7_guard_laundry_claim_date` (`CP7_LAUNDRY_CLAIM_BEFORE_SOURCE`, `_AP_NOT_AVAILABLE`) dan detektor `cp7_guard.findings()` (INDEPENDENT_SOURCE_REVIEW); `CP17_FIN02_*` 3 PASS (run 38784255332). Probe Fable R3-03 tidak sampai ke penulis klaim (fixture tanpa BS, run 38786164960), jadi bukti runtime berasal dari kasus penulis yang saya jalankan ulang |
| FABLE-009 (dugaan) pickup POSTED tidak bisa dikoreksi | **DITUTUP** | `pickup.sql`: batal Bagi Potongan sebelum ada pemakaian lanjutan; lebih dari 15 jenis penghalang (jahit, laundry, FG, BS, payroll, pool absensi, dll.) disebut di layar; pascasyarat menolak bila ada pemakaian lanjutan (INDEPENDENT_SOURCE_REVIEW). `CP17_SG01_*` 2 PASS + browser desktop PASS (run 38784255332) |
| FABLE-010 (dugaan) sisa kain tidak bisa masuk stok lagi | **DITUTUP** | `return.sql` memakai `erp.post_cutting_material_returns` (stok, jurnal Dr bahan/Cr WIP, recost); batal/koreksi D14-10 dalam satu transaksi, riwayat asli tetap. `CP17_SG02_*` 8 PASS + browser HP dan desktop PASS (run 38784255332) |
| FABLE-011 (dugaan) tanpa lantai tanggal cutover global | **MASIH TERBUKA** | Tidak ada perubahan produk; penulis menunggu keputusan owner. Tetap dugaan, bukan cacat terbukti |
| FABLE-012 (dugaan S2) `authenticated` punya EXECUTE ke 108 fungsi penulis `erp` | **MASIH TERBUKA (ditunda D14-9)** | Pencabutan ditunda ke CP7C. Yang sudah ada dan saya lihat lulus: gerbang `exposure_gate` (`CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST` PASS) dan `CP17_HTTP_ERP_WRITERS_NOT_REACHABLE` PASS (run 38784255332). Skenario RBAC saya ulang: 0 tabel `erp` tanpa RLS, fasad definer dengan search_path terkunci (run 38786182325, 38786198297, FABLE). Setelan Data API hosted **belum saya baca ulang**: konektor Supabase menolak (`You do not have permission`) pada 15 Okt |

## Perbaikan r1 lain yang saya periksa (bukan temuan saya)

| Bagian | Hasil |
|---|---|
| D14-3 penjaga kas tanggal mana pun | Kasus penulis `CP17_CASH_*` 6 PASS + race + HTTP. **Tetapi** lihat FABLE-013: dasar tanggal penjaga ≠ dasar tanggal laporan kas |
| D14-6 kasbon | Sumber: tanggal tidak di masa depan/periode tertutup, penjaga kas berlaku, potongan hanya di payroll draf, batal ditolak bila sudah dipotong, payroll tidak boleh dibayar sebelum tanggal kasbon. `CP17_KASBON_*` 3 PASS + HTTP + browser |
| STK01 kartu stok | Pembaca menghitung pasangan dibalik/pembalik sebagai tidak aktif (`materials/read.sql`, `procurement/correction.sql`). `CP17_STK01_*` PASS |
| G1 jahit selesai | Upah borongan dan "siap laundry" lewat penulis Native; batal ditolak bila sudah di laundry, di payroll aktif, atau di pool absensi. Upah yang dicatat mundur tetap terambil payroll berikutnya (pemilihan `eligible_at <= period_end` tanpa batas bawah). `CP17_G1_*` + race + HTTP + browser desktop/HP PASS |
| G2 selesaikan PO | Lihat FABLE-014 (tidak bisa dibatalkan dari aplikasi). `CP17_G2_*` + race + HTTP + browser PASS |
| D14-17 arsip CI kedaluwarsa | Jalur pengganti tidak melonggarkan langkah X. Jumlah 208/207/1 dan sidik nama `eb7f121d…` sama di semua rantai yang saya baca. Batasnya: kesamaan dengan daftar 15 Sep tidak bisa dibuktikan lagi (diakui penulis). 37 workflow CP6 lama tidak bisa jalan (T2 run 38784274269 berhenti di HTTP 410). T2 dikunci ke commit CP6 beku, jadi tidak menguji kandidat |

## Pernyataan paparan
Lihat `MANIFEST.md` §Paparan dan koreksinya (2 baris `HANDOFF_ASTRA.md` r1 tulisan penulis tercetak oleh grep; isinya
sama dengan handoff Fable). Tidak ada laporan, run, artifact, atau cabang auditor lain yang dibuka.
