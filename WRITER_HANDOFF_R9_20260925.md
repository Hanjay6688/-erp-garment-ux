> **DIGANTIKAN (25 Sep 2026 13:00):** versi gabungan dua auditor yang berlaku = `AUDIT_WRITER_HANDOFF_CP6.md`. Berkas ini dipertahankan sebagai riwayat.

# Handoff auditor → writer — CP6 putaran 9 (25 September 2026, ~07:35 UTC)

Dari: auditor Fable (audit silang dengan auditor GPT selesai; semua run GPT diverifikasi Fable dari log Actions).
Kandidat yang dinilai: produk **a095a9d804d29643721e18635c2c3e26adcd56ea**, alat **9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7**.
Branch audit: `audit/cp6-final-20260924-gpt-a0bcadf` (rincian: `out/fable_r8_results.md`, `out/fable_crossreview_gpt_r8.md`, `AUDIT_WRITER_HANDOFF_CP6.md` banner + tabel aktif, `audit/CP6_COMBINED_INDEX.json`).

**Verdict: CP6 HOLD · audit_complete=false · production_go=false.** Tidak ada lagi cacat produk P1 yang terbuka. Penahan sekarang adalah tugas di bawah.

## 1. Yang sudah tertutup pada a095a9d (jangan dikerjakan ulang, jangan diregresi)
| ID | Bukti auditor |
|---|---|
| A1 / CP6-09 impor ganda | open_1 13/13, open_2 4/4, xaudit_7 A1 ×2, R1 dua sesi PASS (36096552454) |
| A2 / CP6-01 waktu WIB | review sumber + browser nyata 12/12 (Potongan, Pickup, BS × 4 zona; run 36099496005, 36100064157) |
| A3 / CP6-02 WIP bertanggal | U02 PASS, xaudit_7 A3 ×2, SI-02 ditolak dengan kode yang disahkan |
| A4 / CP6-03 kasus satu penerimaan | U03 ×2, invoice ×2, MONEY ×4 PASS (rev2 oracle half-up) |
| A5 / CP6-04 selector | selector-101 PASS (102 sumber), selector-51 PASS |
| A6 / CP6-24 close ganda | R2 dua sesi satu filing; close tanggal berikutnya tetap jalan |
| A9 / CP6-07 (D02) | ORDERED ×3 PASS, DATED ×3 ditolak `BA_ADVANCE_DATED_CAPACITY`, batas hari koreksi PASS |
| A10 / CP6-18 (D03) | SI-01 ditolak `BA_WIP_OUTPUT_PRODUCT_BOUND`, xaudit_7 A10 ×4 termasuk provenance unknown |
| C0 25 kasus uang/tanggal | 25/25 PASS (GPT 36098555186 + 36099496005), oracle Fable konvergen |
| HTTP Auth nyata | matriks 18 cek PASS, revocation PASS; helper prepare tidak terjangkau HTTP publik |
| T3 / rollback | package gate semua true, browser 10/10, rollback AC..BA 127/127 (T3_PREP, bukan bukti rilis) |
| B1 mode cases | ID ganda menolak grup; bocor → INCOMPLETE |

## 2. Tugas writer (urut prioritas)
| ID | Prioritas | Masalah (bukti) | Yang harus dikerjakan | Bukti penutup auditor |
|---|---|---|---|---|
| **W8 / CP6-03 residu multi-penerimaan** | P2 produk | Dua penerimaan @10,00 → koreksi/invoice ke 10,005 (dan turun): persediaan 0,01 (atau −0,01) pada qty 0, WIP 20,01 vs expected 20,02 / 20,00 (GPT run 36097284096 MULTI_CENT ×4). M:835/3818/3820/6625/6632: jumlah sen per dokumen, qty 0 ⇒ nilai 0 | Alokasikan sen per dokumen ke pemakaian yang benar sehingga persediaan 0 saat qty 0; atau owner menulis pengecualian eksplisit (bukan default) | rerun `G8:MULTI_CENT_*` (`audit/scenarios/round8/gpt_round8.py`) + kasus satu penerimaan tetap PASS |
| **W7 / R8-B1-01** | P2 alat | Mode race dan HTTP tidak memakai grup ketat: status di luar kosakata diterima (`NOT_A_VALID_STATUS`), ID ganda menimpa hasil, job tetap RUN_COMPLETE (GPT job 107952095197; sumber `scripts/cp6_auditor_modes.py run_races/run_http/finish`) | Terapkan `runner.strict_group` (kosakata, ID unik, planned/final, cek bocor) di kedua mode | `audit/scenarios/round8/gpt_tool_modes.py` → penolakan grup/INCOMPLETE, bukan RUN_COMPLETE |
| **W13 / CP6-06 KPI 0 saat unknown** | P2 produk | Read awal gagal → empat KPI merender **0** dengan banner error dan tulis terkunci; refetch memulihkan 20/10 (GPT run 36106291785 Laundry, 36106777202 QC). M:3825: data tidak diketahui tidak boleh tampil sebagai 0 | `src/ConnectedLaundryPage.tsx:412-416` (`?? 0`, `: 0`) dan `src/ConnectedQcFinalPage.tsx:314-335`: render status "belum diketahui"/"—" saat `workspace` null atau error; pertahankan banner dan kunci tulis | rerun `G8UI:UNKNOWN:*` → KPI awal bukan angka; healthy/refetch tetap PASS |
| **W10 / CP6-05 identitas request** | P2 (GPT) / P3 (Fable) | `src/PatternPage.tsx:97,112` dan `src/AccessControlPage.tsx:202,220,238,253` membuat `p_client_request_id` baru (`randomUUID()`) tiap klik Simpan; setelah balasan hilang, klik ulang = request baru (browser nyata GPT run 36102303107: 409 unik, DB tetap satu baris). M:1679/M:3819: identitas request dipertahankan, replay exact. Halaman CONNECTED transaksi sudah benar (`envelope.id`) | Pakai pola envelope yang dipertahankan (seperti halaman CONNECTED) di Pola dan Role | rerun `G8UI:RECOVERY:*` → replay UUID sama, satu efek |
| **W1 / lampiran C6** | P2 dokumen | ACC-04 dan LAU-05 dilabeli CR-TUNDA menyeluruh padahal M:1668/1691–1699 "tetap dibutuhkan"; LAU-07 terlalu luas; 7 sub-keputusan M:4448–4479 tanpa baris; tidak ada crosswalk ke 75 ID asli; inventaris CR-MASUK belum ada (Fable `out/fable_c6_annex_review.md`, GPT `out/gpt_c6_scope_amendment.md`, `out/gpt_c6_75_case_crosswalk.md`) | Pisahkan ACC-04 → 04a (perilaku lama, BASELINE) / 04b (perluasan baru, CR menurut inventaris); LAU-05 → mekanisme lama BASELINE / komponen-paket-alokasi invoice baru CR; ganti LAU-07 dengan LAU-DEC01–06; tambah ACC-DEC01/04/06/07, ERP-DEC02; lampirkan entrypoint publik + storage + status implementasi tiap CR; tautkan 75 ID asli | auditor cocokkan ulang → owner sahkan D06 → GATE-16 dinilai |
| **W2 / oracle C0 di harness T2** | P2 alat | 25 kasus beku tetap HOLD by design (M:1769); oracle pasca-addendum sudah ada (`out/fable_t2_oracles_post_addendum.md`, `audit/scenarios/c0_round8/gpt_c0_oracles.py`) dan terbukti 25/25 native | Tambahkan grup oracle C0 baru di harness T2 tanpa menghapus assertion beku; perbaiki fixture ADJUSTMENT_DATE per D01 §3.3 (max(E, tanggal penyesuaian)) | run T2 berikutnya memuat grup baru; auditor baca per kasus |
| **W9 / marker laporan** | P3 pertanyaan | C0 §3.4 "laporan menandai `changed_since_filing`" vs implementasi `cp6_aw_t1_family.sql:836` = `filed && readiness<>READY` (dua kasus AO tertutup memberi false meski ada koreksi). Uang/tanggal benar | Jelaskan makna yang dimaksud atau ubah flag menjadi digest perubahan isi; kalau teks diubah, owner sahkan perubahan konkret itu saja | auditor baca kasus AO tertutup ulang |
| **W11 / pesan error klien** | P3 UX | `src/lib/clientError.ts:71`: semua exception tak dikenal (termasuk penolakan parser, mis. "Model produk bukan UUID valid.") ditampilkan sebagai "Layanan UAT belum dapat dihubungi" (terbukti rev2/rev3 GPT) | Tampilkan pesan asli atau kode terpisah (jaringan vs data) | pengamatan browser: pesan parser muncul apa adanya |
| **W12 / kualitas UUID data** | P3 pertanyaan | Validator UUID frontend (`src/laundryQcModel.ts:123`, versi 1–8) menolak UUID non-standar; seed uji `cp3_r3_full_schema_seed.sql` memakai `a1000000-…`/`a2000000-…` (nibble versi 0) dan membuat halaman Laundry/QC gagal memuat | (a) perbaiki UUID seed uji ke v4 (perubahan alat, catat head baru); (b) masukkan cek "tidak ada UUID non-standar pada tabel yang dibaca facade CP6" ke drill T3 untuk data hosted/legacy | hasil cek drill T3 |
| **W3 / A8** | P3 opsional | Grant EXECUTE `authenticated` pada `erp.prepare_migration_opening_balance`; tidak terjangkau HTTP publik, hanya koneksi DB langsung | Cabut grant `authenticated` (hanya FINALIZE yang memanggil) | — |
| **W4 / alat** | P3 | SAMPLE_BROWSER sesekali INCOMPLETE `users_created 0` (run 36096186788); COMMIT pada koneksi kasus membuat grup crash `savepoint "auditor_case" does not exist` (rt_probe_2) | Tandai rapi sebagai INCOMPLETE terstruktur | — |
| **W5 / A7** | P3 opsional | Race COMPLETE ditolak `POCKET_PERIOD_BUSY`, bukan `STALE_VERSION` (aman) | Pesan saja; jangan ubah produk hanya untuk ini selama beku | — |
| **W6 / identitas kas** | P3 pertanyaan | Identitas CASH_BANK per `cash_account_id`, bukan COA; legacy-vs-legacy tidak dicek | Konfirmasi apakah alias nyata ada | — |

## 3. Untuk owner
- D01–D05 dan D03 §5.3: sudah disahkan (addendum C0 hash d39762da…, konfirmasi langsung ke auditor). Tidak perlu diputuskan ulang.
- **O2**: sahkan D06 hanya setelah lampiran C6 direvisi (W1) dan dicocokkan ulang auditor.
- W8: kalau ingin menerima sisa ≤0,01 per penerimaan, harus ditulis eksplisit sebagai pengecualian; tanpa itu W8 wajib diperbaiki.

## 4. Cara auditor memverifikasi ulang
Push head baru H (produk boleh berubah). Auditor mencatat H dan diff, lalu menjalankan ulang lewat `cp6-auditor-scenario.yml` (`phase=after`): skenario Fable di `audit/scenarios/` (hash di `audit/scenarios/FABLE_SHA256SUMS`) dan skenario GPT di `audit/scenarios/round8|c0_round8|browser_round8|pickup_round8|recovery_round8|unknown_round8` (manifest per folder). Setiap penutupan hanya lewat run auditor dengan status PASS per kasus. Hasil beku lama tidak dilabel ulang.

## 5. Yang belum diperiksa auditor (batas)
Cakupan ALL 22 state / 6 keluarga end-to-end (`out/gpt_all_round8_binding.md` memberi rencana kasus); crosswalk 75 ID C6 belum menjadi bukti; matriks izin/lokasi penuh; jalur payroll/BS/settlement lengkap; A4 multi-penerimaan hanya kasus GPT; kompatibilitas legacy hosted (di luar audit).
