# Uji ulang Fable — kandidat revisi `7a0b4a90` (perbaikan temuan audit penuh CP7 `d0b9e9c2`)

**Status:** DRAFT (13 Okt 2026, ~01:15 UTC) — review sumber selesai; run independen sedang berjalan (bagian ⏳ diisi sesudah dibaca per kasus).

| | |
|---|---|
| Kandidat revisi | commit `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2`, tree `05d4ccd84ed7faedede1d9161cd08952591659b2`; head cabang `5656f072` (selisih dari 7a0b4a90 hanya `docs/`, diperiksa sendiri) |
| Selisih produk dari d0b9e9c2 | 27 berkas non-dokumen: `analysis-stages.sql`, `plan-native/{history-yield,commands,staged}.sql`, `cp7_nightly_backup.py`, `cp7_schedule.py`, `cp6_auditor_business_day.py` (+test), `cp7_astra_timeline_reuse_probe.mjs`, `cp7_ci_receipt.py`, kasus K3/PL5/staged/settlement/receipt, `src/App.tsx`, `src/OwnerDashboard.tsx` (+test), panel PL-5. Tree `supabase/*` tidak berubah (paket CP6 identik). |
| Metode | kasus Fable yang sama **tanpa diubah oracle** (smoke 8, core native 5 + balapan 5, UI browser 3) + 1 kasus baru (PL-5 owner-only HTTP) pada `product_ref=7a0b4a90`; 17 workflow penulis didispatch ulang pada head `5656f072`; review sumber setiap perbaikan. Panduan PR #42. |

## 1. Review sumber perbaikan (INDEPENDENT_SOURCE_REVIEW, dibaca baris per baris dari `git diff d0b9e9c2 7a0b4a90`)

| Temuan | Perbaikan yang terbaca | Penilaian statis |
|---|---|---|
| F-OPS-01 | `cp7_nightly_backup.py`: `scratch_state()` membaca komentar database; `FOREIGN` → `BACKUP_SCRATCH_EXISTS_NOT_OURS` sebelum apa pun; `Tools.create` memakai `createdb` tanpa `dropdb` dulu (nama yang muncul di tengah membuat `createdb` gagal, bukan dihapus); hanya database bertanda milik alat yang di-drop; receipt mencatat `scratch_before/after`. | Benar. Tidak ada jalur `dropdb` tanpa cek tanda. |
| F-OPS-02 | `analysis-stages.sql`: trigger baru `work_immutable()` pada `outputs/target_rows/pair_rows/pair_lists/fragments/pages` meloloskan DELETE hanya untuk job yang disebut di setelan transaksi `cp7.analysis_work_delete` (dan `_run` untuk pages); `clean_done/purge_expired/purge_intermediates` tidak lagi `alter table … disable trigger`; `purge_expired` kini `lock_timeout` 2 s. | Benar: DELETE biasa tidak mengambil kunci tabel yang ditunggu INSERT unit. Catatan: setelan GUC bisa dipasang sesi mana pun, tetapi DELETE tetap memerlukan hak tabel (hanya pemilik; RLS) → tidak membuka jalur hapus baru. Penundaan 10 menit `clean_pending` tetap; `purge_expired` tetap tanpa penundaan (sekarang tidak perlu karena tidak mengunci). |
| F-OPS-03 | sumber dibaca dalam satu snapshot (`pg_export_snapshot`), `pg_dump --snapshot`, hash tabel sumber di transaksi yang sama → pembandingan dengan isi dump. | Benar; menutup observasi. |
| F-OPS-04 | `cp7_schedule.py`: `same_database()` membandingkan `--database` dengan `current_database()`; `uninstall` butuh `--removal-approved`. | Benar. |
| F-UI-01 | `OwnerDashboard.tsx`: `connected` (= `runtime.mode !== 'DEMO_SIMULATION'`) → hanya judul + panel `role="status"` "Ringkasan angka belum tersambung ke data ERP"; angka contoh hanya di demo. | Benar sesuai keputusan owner 12 Okt (sembunyikan). ⏳ dibuktikan browser. |
| OBS-01 → keputusan owner 12 Okt | `history-yield.sql`: `actor_role` check `='OWNER'`; akses tulis `CP7_YIELD_POLICY_OWNER_REQUIRED` (42501) untuk selain OWNER; `manage_allowed` hanya OWNER; `commands.sql`/`staged.sql` menyimpan `new_start_yield` (termasuk revisi kebijakan) pada rencana yang disahkan. | Benar. ⏳ kasus Fable HTTP owner-only. |
| F-AN-01 | `request()` menolak `CP7_ANALYSIS_STAGED_TARGET_LIMIT` (detail `refused_at=REQUEST`) sebelum `create_job`. Uji penulis menurunkan `bounds()` di savepoint dan memastikan 0 job/acuan. | Benar. |
| F-PAY-01 | Penulis benar: fungsi Native `erp.post_payroll_payment` yang **terpasang** (v2.6.20ac `20260915031500:4709`, juga `ap` `20260922135615:4695`, keduanya di paket T3) memakai `(statement_timestamp() at time zone 'Asia/Jakarta')::date`. Temuan saya mengutip definisi lama `20260901023200` yang sudah diganti. **Temuan F-PAY-01 saya tarik (salah kutip versi).** Uji baru `P12_SETTLEMENT_WIB_PAYMENT_DATE` memaksa zona sesi berbeda hari dari WIB. | Koreksi auditor; bukan cacat produk. |
| F-AP-01 | Tidak diubah: keputusan owner 2 Okt (kredit boleh ke nota berikutnya mana pun). | Diterima sebagai ACCEPTED_BY_DECISION; dicatat di dokumen koreksi penerimaan. |
| F-TOOL-01 | ASF-F01 (Astra) `5f1506f4`: `explained()` kini mensyaratkan `status_before_rollover=PASS` dan error `AUDITOR_BUSINESS_DAY_ROLLOVER` → FAIL/COUNTEREXAMPLE/INCOMPLETE kasus tidak pernah diulang; `KEPT_FIRST_RESULT` + anotasi GitHub; `cp7_ci_receipt.py` membaca anotasi. | Benar; menutup kekhawatiran saya. |
| F-TOOL-02 | Probe PR44 diperbarui: setiap blok fungsi `cp7_netting_native` harus = pendahulu `aa638356` kecuali dua turunan `_within` dengan **tepat** suntingan yang disebut; bagian luar blok hanya boleh beda komentar/owner. | Benar dan ketat. ⏳ run. |
| F-TOOL-03 | CP6 beku, dicatat. | Diterima. |
| F-UI-02, F-DOC-01 | dicatat / panduan +138 baris (PR #42) | Diterima (F-DOC-01 belum saya diff ulang baris per baris; ⏳ cek cepat). |
| OBS-02, OBS-03 | tidak diubah | Diterima (observasi). |

## 2. Hasil run independen ⏳

(diisi: kasus Fable per kasus; 17 workflow penulis per kasus; kegagalan satu kali `CP7 Supplier Payment Create` pada 7a0b4a90.)

## 3. Vonis ⏳
