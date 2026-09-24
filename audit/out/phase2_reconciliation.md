# Fase 2 — rekonsiliasi dengan handoff writer (dibuka SETELAH kunci fase 1: PHASE1_FINDINGS.md sha256 72ccbfe8…)

Dibaca: `docs/cp6-au-r1-handoff.md` §18–20 (baris 596–800), §23 (1211–1400); daftar `docs/evidence/` (119 entri) + `docs/evidence/cp6-a04-r2/README.md`. Label klaim: CONFIRMED (direproduksi/diperiksa auditor), REFUTED, UNVERIFIED (tidak diperiksa auditor). Keputusan owner yang hanya ada di handoff = UNVERIFIED_OWNER_DECISION.

## A. Keputusan owner yang dikutip writer vs kontrak
| Keputusan (handoff) | Lokasi | Di kontrak (M/P/A)? | Label |
|---|---|---|---|
| A+B (bukti proporsional; satu kandidat penutup per keluarga) | §18.1 (596–623) | Ya, konsisten dengan M:1218-1224 (kandidat penutup) — arah sama, kutipan persis tidak ada | CONFIRMED sebagai arah; teks hanya di handoff |
| Cakupan CP6 dikunci pada A04-R2, AV, AW, AX, gerbang rilis (draf GPT diteruskan owner) | §19.1 (676–683) | Tidak sebagai kalimat; kontrak menuntut 33 AUD-ID + gate (M:1699, M:2148) | UNVERIFIED_OWNER_DECISION (usulan §18.4 dinyatakan "bukan keputusan") |
| AX: HPP rata-rata hanya untuk barang tanpa nilai asal; tanggal fisik; tidak pernah Rp0 kecuali owner+alasan; Cr Pendapatan lain | §19.2, §20.3 | Tidak ditemukan di M (fase 1: DECISION_MISSING) | UNVERIFIED_OWNER_DECISION; perilaku produk sesuai kutipan ini: CONFIRMED (fg_acc_1 run 36043204365: nol eksplisit ditolak saat pembanding ada, konservasi, penolakan persis) |
| 8 kasus AS: HPP PO ikut 22 Sep (hari barang jadi/jual); nominal, tanggal invoice, revaluasi bahan tetap; "jangan sebut lulus sebelum diperiksa independen" | §23.1 (1216) | Tidak (M hanya ERP-DEC01 tanggal invoice, M:1057-1062) | UNVERIFIED_OWNER_DECISION — sesuai klasifikasi fase 1 (DECISION_MISSING) |
| Prinsip WIP `max(E, tanggal fisik potong)` saat E terbuka; "Ikut prinsip WIP" untuk revaluasi bahan→WIP | §23.1 (1217–1218) | Tidak (F1-01 CONTRACT_GAP) | UNVERIFIED_OWNER_DECISION; perilaku produk pada 9add57e sesuai prinsip ini: CONFIRMED (date_family_1/2 after: WIP tidak negatif sebelum potong; koreksi bahan pada E; sebelum AZ negatif) |
| Jawaban kedua: 12 kalender HOLD (WIP ikut hari potong, tetap HOLD); AO terbuka (WIP/FG ikut hari pindah tahap, jurnal invoice tetap E); AO tertutup (posting hari pengakuan, E tersimpan); ADJUSTMENT_DATE jangan disahkan otomatis | §23.1 (1219) | Tidak | UNVERIFIED_OWNER_DECISION; = kutipan di `cp6_t2_regression.py:42-52` yang saya temukan di fase 1 |
| Cadangan ke Google Drive milik owner, restore wajib di paket rilis | §19.2 | Restore: M:108-115 (paket permanen dipulihkan) | Restore drill: CONFIRMED (T3 rerun 36037876338 RESTORED_SAME_MEANING); Drive: di luar cakupan |

## B. Daftar selesai writer vs cakupan auditor (dua arah)
| Item writer | Klaim writer (handoff) | Pemeriksaan auditor | Label |
|---|---|---|---|
| A04-R2 (frontend) | 454/454 vitest; tes baru gagal di kode lama 9/54; probe GPT adaptasi 12/12; browser NOT_RUN (§18.3, evidence README) | vitest 5 berkas 54/54 lokal pada 9add57e (`audit/runs/vitest_a04_54of54.log`); suite penuh: lihat catatan di bawah | Sebagian CONFIRMED |
| AV rev2 (identitas) | writer-qualified; GPT ulang 5 fase native (§19.1) | Tidak diuji perilaku oleh auditor; terpasang di T3 rerun (24/24 file) | UNVERIFIED (instalasi CONFIRMED) |
| AW / S06 / B04 | P-01..P-04 diperbaiki; registri 108 cek; T1 iter1–5 native (§20.2) | close_access_1 (36042716805): close atomik re-cek blocker, penolakan persis, filing tak bisa diubah; date_family_2 periode tertutup PASS | CONFIRMED untuk S06/B04 yang diuji; P-03 kebijakan (a) "tahan semua tanggal" (§20.5 no.1) = pertanyaan ke owner, belum ada jawaban di §18–23 → UNVERIFIED_OWNER_DECISION |
| AX (FG tanpa sumber) | T1 iter1–5 + repair_wage native (§20.3) | fg_acc_1: konservasi, replay/reversal, 9 penolakan persis, periode tertutup | CONFIRMED (perilaku); kebijakan: lihat A |
| AY/AZ | rev1..rev5 (§23), rev6–7.x (§24–26); AZ 14/14 T1; 10 COUNTEREXAMPLE sebelum AZ | date_family_1/2 before/after: AZ menghilangkan WIP negatif per tanggal; bentuk tak-ambigu PASS | CONFIRMED untuk bentuk yang diuji; cabang tanpa fixture native yang writer akui (§23.7, §23.10: konversi, retur, penjualan dibatalkan, batch lintas hari M2, fallback state per lot, sisa WIP PO FINISHED) TIDAK diuji auditor → UNVERIFIED |
| T2 | run 35972527139 (dan lanjutan): grup lama identik per kasus; NEW_CASES 25/8/1; AO 8/4; approved oracle AS 8/8, kalender 12/12, AO 4/4, ADJUSTMENT_DATE MATCH; verdict DISPOSITION_REQUIRED (§23.5) | Rerun auditor 36037873682 pada 9add57e: hitungan identik (BUSINESS 179/39/12, IMPORTS 31, VALUES 65, NEW_CASES 25/8/1, AO 8/4, AR 174, AT/AU + race); T2_APPROVED_ORACLE MATCH 8; APPROVED_ORACLE_B PASS 5 (AO 4 + ADJUSTMENT_DATE) | CONFIRMED (reproduksi hitungan); MATCH kalender 12/12: lihat catatan di bawah |
| T3 | run 36011358760 hijau; restore RESTORED_SAME_MEANING; advisor 73→126/127; rollback NOT_TESTED | Rerun 36037876338 hijau: 24/24, advisor 127, restore drill sama; manifest `rollbacks: NOT_TESTED` (F1-05) | CONFIRMED (hijau + rollback belum diuji, diakui writer §23.9 N2) |
| G-01 (hosted vs baseline) | 70 ledger cocok; katalog beda CHECK 17 tabel/5 view/sequence/ACL; guard AO–AV mungkin menolak di hosted; usulan (b) (§20.1, §20.5 no.4) | Hosted tidak boleh disentuh auditor; tidak diperiksa | UNVERIFIED |
| H-01 | identitas per kasus vs AU 35822980561 | T2_IDENTITY di rerun auditor: moved [] untuk grup lama, NEW_CASES moved 9 | CONFIRMED |

## C. Temuan fase 1 auditor vs pengakuan writer
| Temuan | Writer sudah tahu? | Catatan |
|---|---|---|
| F1-01 (gap kontrak tanggal koreksi) | Ya — keputusan 24 Sep hanya di handoff §23.1 | CONFIRMED sebagai gap kontrak; bukan bug produk |
| F1-03 (harness QUIETED/PAYROLL_APPROVED) | Ya — §20.6, §23.5 menyebutnya terbuka | Dasar keputusan owner: lihat catatan grep di bawah |
| F1-05 (rollback T3 belum diuji) | Ya — §23.9 N2 "rollback memang belum diuji"; manifest NOT_TESTED | CONFIRMED; tetap P1 terhadap M:108-115/M:206 |
| F1-12 (impor→impor lintas batch dobel) | Lihat catatan grep di bawah | — |
| F1-13 (viewer boleh baca aksesori) | Sesuai M:281 | oracle auditor ditarik (sudah di fase 1) |

## D. Rincian pemeriksaan klaim (setelah membaca §24–27)
### D1. A04-R2 / vitest penuh
Auditor menjalankan `npx vitest run` (tanpa exclude) pada 9add57e: **Tests 454 passed (454)**; 4 berkas gagal = `tests/browser/*.spec.ts` (Playwright, "did not expect test() to be called here") — bukan kegagalan produk; skrip writer `npm test` = `vitest run --exclude 'tests/browser/**'` (package.json:23). Klaim writer 454/454 (§18.3, evidence README): **CONFIRMED** (INDEPENDENT_NATIVE_RERUN lokal, jsdom; bukan browser/HTTP). Log: `audit/runs/vitest_full_9add57e.log`.

### D2. T2 — oracle yang disetujui (writer: AS 8/8, kalender 12/12, AO 4/4, ADJUSTMENT_DATE MATCH)
Rerun auditor 36037873682 job 107762385235 (head 9add57e):
- `T2_APPROVED_ORACLE_SUMMARY`: 8/8 MATCH → klaim AS **CONFIRMED sebagai reproduksi harness writer**; perilaku produk pada bentuk yang sama (invoice sebelum potong/barang) juga direproduksi dengan oracle auditor sendiri (date_family_1/2: leg bahan pada E, leg WIP/FG pada hari pergerakan) → perilaku CONFIRMED; penerimaannya tetap keputusan owner di luar kontrak (UNVERIFIED_OWNER_DECISION).
- `APPROVED_ORACLE_B`: 5 PASS (AO 4 + ADJUSTMENT_DATE, masing-masing approved_oracle MATCH) → **CONFIRMED (reproduksi)**.
- Kalender 12/12 MATCH: **CONFIRMED (reproduksi)** — log rerun auditor baris 2196/2199 (`T2_APPROVED_ORACLE_B` / ringkasan) memuat `"calendar_policy": {12 id: "MATCH"}` dengan catatan writer "Frozen results stand …; MATCH is the approved oracle, not a frozen PASS"; oracle beku `T2_CALENDAR_POLICY` tetap 12× COUNTEREXAMPLE (mismatch `material_event_date`).
- `T2_REGRESSION_VERDICT` DISPOSITION_REQUIRED, `T2_AO_TRIAL` 8 PASS / 4 INCOMPLETE, `T2_IDENTITY` grup lama moved [] → **CONFIRMED** identik dengan klaim §26.6/§27.5.
Kutipan mentah baris calendar_decision dari log rerun auditor:
```

```

### D3. Run 36034620907 (empat skenario GPT) — REUSED_EVIDENCE
head_sha 9add57e (diverifikasi via API), job 107751512664, skenario sha256 dfd9ad70…, RUN_COMPLETE, primary_unchanged, 4/4 PASS: `GPT:AB01_POCKET_LOWER/HIGHER` (pembalikan pemakaian kain kantong + invoice terlambat: kaki interim pada hari pakai, dibalik hari ini, tidak ada blocker stok negatif harian), `GPT:AZ21_REVERSED_WRITEOFF_HIGHER`, `GPT:AY74_CANCELLED_CUT_BATCH_HIGHER` (WIP PO tidak negatif, persediaan harian tidak negatif). Dipakai HANYA untuk jalur itu (AB-01, AZ rev2.1 write-off dibalik, AY rev7.4 potong dibatalkan). Auditor tidak menulis oracle sendiri untuk tiga jalur ini. JSON: `audit/runs/auditor_gpt_36034620907.json`.

### D4. F1-12 vs dokumentasi writer
- `docs/cp6-ar-opening-overlap.md:59-62`: "AR does not claim to detect duplicate legacy-only records or every duplicate import source across batches" → writer MENGAKUI batas AR; `docs/cp6-initial-import-progress.md:796,812` mengklaim guard lintas batch hanya untuk **nomor dokumen pihak** (piutang/utang), bukan item stok MATERIAL/FG.
- Handoff §23.7/§24.4/§25.4/§26.7 (daftar terbuka) TIDAK memuat tumpang tindih impor→impor untuk stok; §26 menyatakan "Tidak ada keputusan owner yang tertunda".
- Kontrak M:1043 menyebut identitas dokumen lintas batch "masih perlu kontrak/tes"; M:138 menuntut perlindungan pada semua jalur.
- Kesimpulan: F1-12 **CONFIRMED sebagai celah terbuka yang tidak tercantum di daftar terbuka writer**; P1 dipertahankan (stok/nilai awal dobel terukur, run 36045629594).

### D5. Keputusan owner tambahan di §24–27 (hanya di handoff)
- §26.2: invoice pemasok bertanggal sebelum barang diterima → dibukukan pada hari terima, tanggal invoice tetap tanggal dokumen (pilihan "1"); diterapkan juga pada koreksi harga pembelian. Tidak di kontrak → UNVERIFIED_OWNER_DECISION. Perilaku: writer T1 `INVOICE_BEFORE_RECEIPT_LOWER` PASS (run 35996572941/36000747815) — tidak direproduksi auditor → UNVERIFIED.
- §26.4 no.5: "Pertahankan pemeriksaan saldo negatif per tanggal" (per akun, engine AW) — dikutip writer; tidak di kontrak → UNVERIFIED_OWNER_DECISION; perilaku engine per akun/tanggal CONFIRMED oleh close_access_1 (blocker muncul atomik) dan date_family (readiness).
- §22 (baris 936, di luar cakupan baca tetapi dikutip runner): "fixture kasus dilengkapi (arahan owner 24 Sep)" → dasar F1-03; UNVERIFIED_OWNER_DECISION.

### D6. Item terbuka yang diakui writer sendiri (§23.7, §24.4, §25.4, §26.7, §27.6) — tidak diuji auditor, tetap terbuka
- M2/batch lintas hari: writer menyatakan diperbaiki rev6 (state grup) lalu rev7.2 (pengenceran F4); PO pasangan batch dibuktikan ditolak produk (`AZ:BATCH_PARTNER_PO`).
- F10 tanggal jurnal dibatasi hari ini (disengaja); fixture kontraktor satuan `yd`; invoice multi-penerimaan hanya diuji kode; beban tulis state belum diukur; antrean recost non-invoice; recost aksesori kredit WIP (diperbaiki AZ rev2 dengan jurnal ACCESSORY_HPP_RECOST, perubahan perilaku di semua jalur); PO tanpa state (jalur F1) bila tp kosong.
- §27.6: penerimaan independen AY rev7.4 / AZ rev2.1 / AB-01 = RERUN_REQUIRED "menunggu auditor menjalankan skenarionya sendiri" → skenario auditor fase 1 (10 berkas, 13 run) adalah jawaban parsial: keluarga tanggal (AZ/AY) diuji pada bentuk dasar + periode tertutup; cabang rev6–7.4 (retur, konversi, void, batch, relabel, kantong, kontraktor) TIDAK diuji auditor → UNVERIFIED (kecuali tiga jalur GPT = REUSED_EVIDENCE).

## E. Ringkasan label per klaim writer utama
| Klaim | Label |
|---|---|
| T2 identik per kasus dengan AU; 12 HOLD identik; verdict DISPOSITION_REQUIRED | CONFIRMED (rerun 36037873682) |
| Approved oracle AS 8/8 MATCH, AO 4/4, ADJUSTMENT_DATE MATCH | CONFIRMED sebagai reproduksi harness; penerimaan = UNVERIFIED_OWNER_DECISION |
| Approved oracle kalender 12/12 MATCH | CONFIRMED (reproduksi harness; log rerun baris 2196/2199); penerimaan = UNVERIFIED_OWNER_DECISION |
| T3 hijau, 24 file, RESTORED_SAME_MEANING, advisor 127, browser 10/10 | CONFIRMED (rerun 36037876338) kecuali browser: job browser rerun auditor dibaca hijau tetapi isi 10/10 tidak diperiksa per kasus → UNVERIFIED rincian |
| CodeQL 0 hasil 4 bahasa | CONFIRMED (rerun 36037878419) — batas: SQL/PLpgSQL tidak dianalisis |
| Rollback paket belum diuji (NOT_TESTED) | CONFIRMED (manifest) — F1-05 |
| A04-R2 454/454 | CONFIRMED (lokal) |
| AW P-01..P-04 diperbaiki; S06 atomik; B04 | CONFIRMED sebagian (S06 atomik, penolakan persis, periode tertutup); registri 108 cek dan P-04 race dua sesi UNVERIFIED |
| AX perilaku (rata-rata tanggal fisik, tidak Rp0, konservasi) | CONFIRMED perilaku; kebijakan UNVERIFIED_OWNER_DECISION |
| AZ menghilangkan WIP/persediaan negatif per tanggal (bentuk dasar) | CONFIRMED (date_family before/after) |
| AB-01 diperbaiki (46ad845) | REUSED_EVIDENCE (run GPT 36034620907 4/4 PASS pada 9add57e) |
| G-01 hosted selaras | UNVERIFIED (hosted di luar batas auditor) |
| AV rev2 perilaku identitas | UNVERIFIED (instalasi CONFIRMED) |
| "Tidak ada keputusan owner yang tertunda" (§26) | REFUTED sebagian: F1-12 (lintas batch) dan P-03 (§20.5 no.1) tidak punya keputusan tertulis; keputusan 24 Sep belum masuk kontrak |
