# Serah-terima penulis ke Astra: pekerjaan D17-14 (20 Okt 2026)

Owner (D17-14, persis): "ini jawabannya karna limit lu mepet siapin handover buat astra". Penulis sebelumnya (Claude)
menyerahkan pekerjaan D17-14 ke Astra. Astra sebelumnya auditor independen r1–r5; bila Astra menulis kode ini, audit atas
perubahan Astra harus dilakukan auditor lain (Fable atau Sol), bukan Astra sendiri (Pro Max §2.2).

## Kotak untuk owner (salin seluruh isi kotak ke sesi Astra)

````text
Kamu Astra. Kali ini kamu MENULIS (bukan mengaudit) lanjutan ERP Garment, repo Hanjay6688/-erp-garment-ux. Baca dulu
docs/cp7/handoff/HANDOFF_ASTRA_WRITER_D17_14_20261020.md di cabang claude/new-session-deapao, lalu
docs/cp7/OPEN_WORK_D17_14_20261020.md dan keputusan owner D17-14 di docs/cp7/OWNER_DECISIONS_20261008.md (kutipan persis).
Kerjakan OW-01..OW-15 sesuai urutan di sana, di cabang baru terpisah (usul astra/d17-14-<tanggal>); kandidat audit
55c885d1 tetap beku. Mulai dari jalur uang, stok, HPP dan koreksi transaksi; tiga butir Kelompok 1 (OW-01..OW-03) wajib
beres sebelum paket dikirim ke auditor. Untuk setiap butir catat perubahan, bukti uji (run/job/kasus) dan batas yang
tersisa. "Selesai" hanya bila kebutuhan owner terpenuhi dan alurnya terbukti berjalan. Jangan melonggarkan pemeriksaan
lama, jangan mengarang nilai kebijakan, tanyakan owner hanya untuk nilai kebijakan atau pilihan bisnis yang belum
ditetapkan. Batas wajib ada di bagian 3 serah-terima (jangan ubah main, Cloudflare, Supabase Enteng, ERP lama,
production; WA hanya server palsu; tanpa biaya; repo publik). Laporan ke owner dalam bahasa sehari-hari sesuai CLAUDE.md.
Perubahanmu diaudit auditor lain, bukan kamu sendiri.
````

## 1. Posisi saat serah-terima

- Cabang penulis: `claude/new-session-deapao`. **Kandidat beku untuk audit r6: `55c885d1a12336905e433e05852b99be4d933f74`**
  (tree `80622a93bbbd2fb6295546aa00f1dc5eb919d827`). Commit sesudahnya di cabang itu hanya `docs/` dan dua alat uji
  (`scripts/cp7_qualify_dispatch.py`, `scripts/cp7_red_compare.py`); jangan menambah kode produk ke cabang ini.
- **Kerjakan D17-14 di cabang terpisah** (arahan owner), usul: `astra/d17-14-<tanggal>`, dibuat dari ujung
  `claude/new-session-deapao`.
- Kualifikasi `55c885d1` selesai: paket `docs/cp7/audit-candidate/cp1-7-r6-20261019/` (README bagian Kandidat,
  `CI_RECEIPT.json`, `RED_RUNS_VS_R6.json`). Paket r6 **belum dikirim**: owner menahannya sampai tiga butir Kelompok 1
  (OW-01..OW-03) dibetulkan; paket berikutnya dibuat pada satu versi baru (OW-15).
- Daftar kerja dan syarat selesai: `docs/cp7/OPEN_WORK_D17_14_20261020.md` (OW-01..OW-15, urutan dari owner). Latar
  temuan dengan rujukan berkas/baris: `docs/cp7/D17_13_PENUNDAAN_PENULIS_20261020.md`.

## 2. Wajib dibaca dulu

1. `CLAUDE.md` (laporan ke owner: bahasa sehari-hari, kalimat pertama apa yang beres dan belum, keputusan dalam bentuk
   ya/tidak) dan `docs/ERP_BEST_PRACTICES.md` (jalankan daftar periksa di akhir sebelum menyerahkan kandidat; pelajaran
   terbaru E25o–E25w).
2. `docs/cp7/OWNER_DECISIONS_20261008.md` D13-1..D17-14 (kutipan persis). Keputusan yang sudah disahkan tidak dibuka ulang.
3. `docs/AUDIT_PANDUAN_PRO_MAX.md`.
4. Untuk OW-01/OW-02: `docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md`, `docs/cp7/wa/WA_WRITER_HANDOFF.md`,
   `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md`, `docs/cp7/k4/K4_RUNNER.json`.

## 3. Batas yang tidak boleh dilanggar (owner, persis bila dikutip)

- "Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
  (`vlxdhpkjeevubjxexnfo`, read-only), production." ERP lama hanya SELECT (D17-11).
- "Jangan mengirim pesan/notifikasi ke orang lain. Jangan meminta password, token, atau kunci di chat; pakai autentikasi
  lokal." Uji WA hanya server CallMeBot palsu, nomor `+620000000000`, kunci `FAKEKEY-*`.
- "Jangan melonggarkan oracle/guard lama agar hasil hijau. Simpan log gagal dan fixture salah."
- "Dump produksi jangan masuk repo, artifact publik, atau log." Repo ini publik.
- "gamau keluarin duit 1000 pun"; "Enteng belum boleh diubah sebelum backup awal berhasil dan terverifikasi"; CP7C tetap
  ditahan (D13-9a); `production_go: false`.
- Tanpa PR kecuali owner minta. Commit per bagian.

## 4. Titik masuk kode per butir

| ID | Mulai dari |
|---|---|
| OW-01 | `scripts/cp7-src/alerts/alerts.sql` (`collect_kinds`, `ar_source` hanya `receivable_source`, `ap_source` hanya `payable_source`, baris 348-367 dan 484-485); Pengingat membaca semua domain lewat `scripts/cp7-src/reminders/staged-reminders.sql:478-500` dan `reminders/other-obligation-source.sql` (OPENING_AR/AP, PAYROLL_AP, ACCESSORY_AP, LAUNDRY_AP, LAUNDRY_RECEIPT, LAUNDRY_OPENING_UNINVOICED). Hak baca per domain: `reminders/rule-condition-source.sql`. Status kirim dan pengaman duplikasi yang sudah ada: outbox/dispatch di `alerts.sql`. Kasus: `scripts/cp7_wa_forward_cases.py`, deklarasi `docs/cp7/wa/WA_FORWARD.json` (ubah sebelum dijalankan; probe menolak jumlah/ID/RPC yang tidak cocok, E25t) |
| OW-02 | `docs/cp7/k4/K4_RUNNER.json` (`not_runner_driven`); penjalan `scripts/cp7-src/ops/` (staged-runner); laporan `report-staged.sql`, pengingat `reminders/staged-reminders.sql`, analisis latar. Uji browser harus menutup browser saat proses berjalan lalu membuka lagi |
| OW-03 | `scripts/cp7-src/planning/analysis.sql:288`, `planning/analysis-stages.sql:1267` (`rounding_multiple` selalu null); mesin `scripts/cp7-src/baseline/feasibility.sql` belum dipanggil; tidak ada isian di `src/`. Klaim salah di `docs/cp7/P20_P21_PAKET_CABANG_CLAUDE.md:100` harus dibetulkan |
| OW-04 | Penolakan retur invoice lunas: `docs/cp7/F03_WRITER_HANDOFF_20261001.md:25`, `docs/cp7/F03_REMAINING_CONTRACT.md:32`; layar dan fasad retur penjualan `docs/cp7/SALES_RETURN_CORRECTION_HANDOFF.md` |
| OW-05 | `docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/SG01_PICKUP_REVERSAL.md` dan `SG01_PICKUP_CORRECTION_DESIGN.md` (tingkat (b) ditolak); upah/nota/payroll/HPP: `scripts/cp7-src/payroll/`, `scripts/cp7-src/hpp-pool/pool.sql` |
| OW-06 | `scripts/cp7-src/invoices/payment-create.sql` (satu `purchase_id`), `docs/cp7/SUPPLIER_PAYMENT_CREATE_HANDOFF.md:94-95`; pembetulan bayar `docs/cp7/SUPPLIER_PAYMENT_CORRECTION_HANDOFF.md`; penjaga kas per tanggal (D14-3, D15-1) tidak boleh dilonggarkan |
| OW-07 | Native `erp.rebuild_po_hpp`, `_build_attendance_hpp_manifest_v1` (`supabase/migrations/20260901023200_*_14c_*`), kain kantong `supabase/release/cp6-t3/20260926050000_*_20be_*` (`sync_pocket_period_v1`, `period_blockers_v1`); fasad CP7 `scripts/cp7-src/hpp-pool/pool.sql` |
| OW-09 | `src/RecordTools.tsx:31`; 8 layar dengan `filterScope="PAGE"` (`grep -rn 'filterScope="PAGE"' src`) |
| OW-10..OW-13 | `scripts/cp7-src/planning/baseline-source.sql:71-100`, `planning/analysis-stages.sql:397-399, 2094`, mesin `baseline/target.sql` (mode `STATISTICAL`), `demand/estimate.sql:23-29` (analog), `model-native/evaluation.sql`, `src/NativeModelEvaluationPanel.tsx`, `src/NativeStagedAnalysisView.tsx:61-62`, `plan-native/history-yield.sql:237,282`, `docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md:136-137` |

Catatan dari pemeriksaan: komentar basi tanpa akibat di `cutting-yield/model-producer.sql:1` dan
`reminders/other-obligation-source.sql:2` (keduanya sebenarnya terpasang).

## 5. Cara uji dan kualifikasi

- Setiap suite CI dideklarasikan sebelum dijalankan (`docs/cp7/cp17/CP17_FIXES.json`, `docs/cp7/wa/WA_FORWARD.json`, dst.);
  ubah deklarasi bersama kasus dan cek lokal dengan aturan probe (E25t).
- Pembanding kasus dihitung dari angka fixture, rumus dengan pembagian memakai pecahan eksak dan punya kasus batas (E25q,
  E25v). Bukti gagal di kode lama disimpan.
- Kualifikasi satu versi: `python3 scripts/cp7_qualify_dispatch.py SHA BRANCH` (116 workflow,
  `QUALIFICATION_WORKFLOWS.json`), lalu skenario penulis CP6 lengkap secara terpisah dengan masukan yang sama seperti run
  pembanding (`scenario_path=scripts/cp6_bf_combined_modes.py`, `browser_path=scripts/cp6_bf_vendor_browser.mjs`,
  `phase=after`; cocokkan jumlah kasus 104/26/9/31, E25w). Sesudah selesai: `python3 scripts/cp7_red_compare.py SHA
  docs/cp7/audit-candidate/cp1-7-r6-20261019/RED_RUNS_VS_R6.json OUT.json` dan
  `python3 scripts/cp7_ci_receipt.py SHA CI_RECEIPT.json`.
- Kondisi pembanding di `55c885d1`: 117 run, 96 lulus; 21 run merah CP6 lama (job dan langkah sama dengan `3b7bb381`);
  skenario CP6 lengkap INCOMPLETE dengan 4 kasus layar yang sama (`READINESS_BROWSER` desktop/HP: fungsi
  `erp_cp7_get_recost_queue_v1`/`erp_cp7_get_hpp_pools_v1` tidak ada di tumpukan skenario; `BF_BROWSER:SALES_MANUAL_13`
  desktop/HP). Owner (D17-14): tetap ditampilkan sebagai gagal dengan pembanding, ditambah pemetaan uji pengganti (OW-15).
- `[skip ci]` di commit teratas mematikan workflow yang dipicu push; jangan dipakai pada commit yang harus diuji.
- Log GitHub Actions: `gh api .../jobs` jalan, tetapi unduhan log lewat URL blob ditolak proxy; pakai alat log MCP
  GitHub dengan `return_content`.

## 6. Hal yang menunggu owner

Lihat `OPEN_WORK_D17_14_20261020.md` bagian akhir: pilihan bisnis yang mungkin perlu ditanyakan (tanya hanya bila memang
dibutuhkan) dan pertanyaan yang sudah diajukan tetapi belum dijawab (kebutuhan aksesori dari rencana, BOM per warna/ukuran,
laporan aksesori mandor).
