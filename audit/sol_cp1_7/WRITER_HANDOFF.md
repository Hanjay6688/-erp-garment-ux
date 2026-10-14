# Audit independen Sol CP1–CP7 — handoff writer

**Putusan: HOLD pada `0b7049d9`.** Audit putaran ini selesai; kandidat belum memenuhi penerimaan penuh. `audit_complete=false`, `production_go=false`. Satu akar masalah bisnis dan dua cacat bukti terkonfirmasi; kegagalan pertama pemasangan AZ tetap belum terjelaskan.

| ID | Prioritas | Temuan dan dampak | Pekerjaan writer |
|---|---|---|---|
| SOL-001 | P1 / S1 | Bank saldo 0 membayar supplier 1.00 dan menjadi −1.00. Kontrol funded 34.50 → 33.50 lulus. | Penjagaan kas bersama per akun/tanggal, concurrency, dan kebijakan overdraft eksplisit bila diizinkan. Tutup seluruh keluarga pengeluaran, bukan hanya form supplier. |
| SOL-002 | P2 / S2 | Artefak BE hanya 4/16; log Native sendiri memuat 16/16 PASS. Import AV memindahkan global output path. | Output sink tetap per run; unggahan harus exact ID set, terminal result dan cleanup. |
| SOL-003 | P2 / S2 | Pemasang kehilangan diagnostik PostgreSQL saat AZ gagal; hanya P0001/MAINTENANCE_RUNTIME_FAILED tersisa. | Simpan diagnosis privat yang aman, file/hash dan state; telusuri first AZ failure. |
| OPEN-AZ-FIRST | Sebelum penerimaan install | First run berhenti 51/58. Qualification berinstrumen 58/58 tidak menjelaskan first failure. | Root cause tetap OPEN. Admission first failure tertutup; data produksi tidak dipakai. |

Rincian expected/actual, root cause, bukti dan acceptance berada di `FINDINGS.json`; daftar tugas siap olah di `WRITER_TASKS.json`. Jangan menyebut SOL-002 sebagai bug hitung BE: keenam belas kasusnya terbukti berjalan melalui log asli.

**Bukti kuat yang selesai:** delapan bucket F03 447/447; prefreeze UI 31/31; F01/F02 fullstack 86/86; AT 16+4 balapan dan AU 15+6 balapan; AR 146 original + 28 balapan dengan satu original zero-price tetap INCOMPLETE dan replacement BC lulus; C0 25/25 dengan cleanup qualification terpisah dan 0 kredit pengulangan; lima kasus kontrak Sol 5/5; PR44 235/235 + dua mutant tertangkap. K4 real pg_cron menyelesaikan 5.000 target dalam 127 unit dan 26 halaman, tanpa manual tick/page step, lalu dibuka dengan UUID/run yang sama.

**Regresi 326 bukan 326 PASS:** 275 PASS, 39 CONTROL_PASS, 12 DATE_POLICY_REVIEW_REQUIRED. AS34 raw = 25 PASS, 8 COUNTEREXAMPLE, 1 INCOMPLETE; AO12 raw = 8 PASS, 4 INCOMPLETE. Pembanding C0/owner D01 berjalan terpisah; status original tidak ditimpa.

**Kebutuhan lama yang tetap terbuka:** auto-bagi satu lusin ke range ukuran dalam form connected. Kandidat masih menyebut bagi rata 4/4/4 hanya simulasi; `SalesDraftPanel` menyimpan quantity per baris dan helper lusin mengubah satu baris. A6 browser per-line lengkap sesuai D13, tetapi itu bukan bukti fitur range-wide. Ini known gap writer, tidak dihitung temuan baru.

**Batas pemeriksaan:** CP2 original utuh (149 ZIP members, 148 hashes, 142 tables, 104 configuration rows, Auth 0), tetapi original functional restore belum dijalankan. Poison control belum lengkap untuk semua detektor. API alternatif/GraphQL belum diuji, sedangkan harness HTTP saat ini mengekspos public saja. Hardware fisik/Safari, data cutover nyata, hosted clone/shadow dan backup offsite mengikuti tahap/izin owner berikutnya. Matrix lengkap: `INVARIANT_MATRIX.csv` dan `SCENARIO_MATRIX.json`.

**Urutan revisi:** tutup SOL-001 dan tetapkan kebijakan bila saldo negatif memang dibutuhkan; benahi kedua cacat bukti; diagnosis AZ; tutup known requirement/coverage gap yang berlaku; bekukan kandidat baru dan jalankan affected gate dengan oracle yang tetap. Migrasi historis jangan diubah in-place. Paket ini tidak mengubah produk/writer branch/main/hosted/deployment. A2 supplier lama tetap known OPEN sesuai D13-10 dan tidak menjadi temuan baru Sol.
