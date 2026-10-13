# Uji ulang temuan Fable — kandidat `7a0b4a90` (sesi auditor terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Audit penuh CP7 Fable atas `d0b9e9c2` memberi HOLD
(F-OPS-01, F-OPS-02, F-UI-01 major). Handoff Fable: "Writer boleh diminta perbaiki tiga temuan major, lalu kandidat baru
diuji ulang dengan kasus Fable yang sama." Kandidat ini juga memuat perbaikan ASF-F01 dari audit Astra
(`../asf-f01-retest-20261012/`).

## Paste block untuk membuka sesi auditor

> Kamu auditor independen CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`).
> Kandidat revisi adalah commit sumber `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2`, tercatat di
> `docs/cp7/audit-candidate/fable-retest-20261012/CI_RECEIPT.json`. Uji commit itu, bukan HEAD lain. Sesudahnya kode
> produk tidak berubah — buktikan sendiri dengan `git diff --name-only 7a0b4a90 HEAD -- supabase src scripts/cp7-src`
> (harus kosong); alat uji yang berubah sesudahnya terdaftar di bagian "Perubahan sesudah kandidat". Selisih
> dari `d0b9e9c2` yang diaudit ada di `SOURCE_DELTA.json` paket itu. Baca `docs/AUDIT_PANDUAN_PRO_MAX.md`, laporan audit
> Fable di cabang `audit/fable-cp7-full-d0b9e9c2-20261011` (`audit/fable_cp7/AUDIT_FABLE_d0b9e9c2.md`, skenario
> `audit/fable_cp7/scenarios/`), lalu `README.md` dan `AUDITOR_RETEST.md` di folder paket ini. Jalankan ulang kasus Fable
> yang sama tanpa mengubah oracle-nya (`FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB`, `FABLE_CORE:CLEANUP_LOCK_VS_RUNNING_STEP`,
> `FABLE_CORE:BACKUP_VERIFY_UNDER_LIVE_WRITES`, `FABLE_UI:LANDING_NO_FABRICATED_FIGURES_DESKTOP` dan `_MOBILE`) pada SHA
> revisi, ditambah kontrol auditor sendiri, lalu periksa temuan minor sesuai tabel `README.md`. Keputusan owner 12 Okt
> (dashboard disembunyikan; PL-5 owner saja) dan 2 Okt (kredit kelebihan bayar boleh ke nota berikutnya mana pun) sudah
> disahkan dan tidak dibuka ulang. Batas: jangan mengubah `main`, deployment Cloudflare, Supabase hosted Enteng
> (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke
> `claude/new-session-deapao`, `cp7/integration` atau cabang audit lama (pakai cabang audit baru); jangan memasang jadwal
> pg_cron atau backup malam di database mana pun selain salinan sekali pakai; jangan mengirim pesan ke orang lain; jangan
> meminta password/token/kunci; jangan melonggarkan oracle/guard; simpan log gagal pertama. Area optimasi timeline PR44
> tidak boleh diterima oleh auditor yang menulisnya (Astra). `production_go:false` tetap.

## Paste block untuk Astra (uji ulang ASF-F01 pada kandidat yang sama)

Paket lama `../asf-f01-retest-20261012/` menguji `5f1506f4`; sesudah commit itu ada perubahan kode (perbaikan Fable), jadi
pemeriksaan "commit sesudahnya hanya dokumen" di paket lama tidak berlaku lagi. Astra memakai blok di bawah.

> Kamu auditor independen CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`), yang
> sebelumnya mengaudit `d0b9e9c2` (cabang `audit/astra-cp7-full-d0b9e9c2-20261012`, putusan HOLD karena ASF-F01).
> Kandidat revisi adalah commit sumber `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2`, tercatat di
> `docs/cp7/audit-candidate/fable-retest-20261012/CI_RECEIPT.json`; sesudahnya kode produk tidak berubah — buktikan dengan
> `git diff --name-only 7a0b4a90 HEAD -- supabase src scripts/cp7-src` (harus kosong). Perbaikan ASF-F01 ada sejak `5f1506f4` (`docs/cp7/audit-candidate/asf-f01-retest-20261012/`);
> sesudahnya alat tanggal hanya menambah anotasi peringatan GitHub (`scripts/cp6_auditor_business_day.py` `annotate`), dan
> kandidat ini juga memuat perbaikan temuan audit Fable (`README.md` paket `fable-retest-20261012`). Baca
> `docs/AUDIT_PANDUAN_PRO_MAX.md`, laporan dan handoff auditmu sendiri, lalu `README.md` dan `AUDITOR_RETEST.md` kedua
> paket. Tugas: (1) uji ulang ASF-F01 dengan kontrolmu sendiri (`audit/astra_full/probe_business_day_new.py` dan kontrol
> tambahan) di semua mode yang memakai helper (savepoint, balapan, HTTP, browser), termasuk anotasi baru; (2) ulangi
> regresi yang terdampak perubahan sejak `d0b9e9c2` (`SOURCE_DELTA.json`), boleh menulis BELUM DIULANG untuk area yang tidak
> tersentuh; (3) bila mau, uji silang perbaikan temuan Fable sebagai auditor kedua. Kamu menulis area optimasi timeline
> PR44, jadi kamu **tidak** menerima area itu; kamu boleh memberi catatan apakah perubahan writer pada probe-mu
> (`scripts/cp7_astra_timeline_reuse_probe.mjs`, F-TOOL-02) masih sesuai maksud aslinya. Keputusan owner yang sudah
> disahkan (12 Okt: dashboard disembunyikan, PL-5 owner saja; 2 Okt: kredit kelebihan bayar ke nota berikutnya mana pun)
> tidak dibuka ulang. Batas: jangan mengubah `main`, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`),
> legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke `claude/new-session-deapao`,
> `cp7/integration` atau cabang audit lama (pakai cabang audit baru); jangan memasang jadwal pg_cron atau backup malam di
> database mana pun selain salinan sekali pakai; jangan mengirim pesan ke orang lain; jangan meminta password/token/kunci;
> jangan melonggarkan oracle/guard; simpan log gagal pertama. `production_go:false` tetap.

## Yang diuji ulang

| Temuan | Kriteria penutupan (laporan Fable §2) | Yang berubah di `7a0b4a90` | Titik awal (bukan bukti lulus) |
|---|---|---|---|
| F-OPS-01 major | `FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB` PASS (database lain tetap ada); nama scratch dicatat di receipt | `scripts/cp7_nightly_backup.py` (`scratch_state`, `mark_scratch`, `Tools.create` tanpa hapus dulu, `backup`) | kasus Fable tanpa diubah PASS di mesin writer; `K3C_RACE_BACKUP_SCRATCH_NEVER_DROPS_ANOTHER_DATABASE` di suite `k3-cleanup-22` |
| F-OPS-02 major | `FABLE_CORE:CLEANUP_LOCK_VS_RUNNING_STEP` PASS (step tidak menunggu/dibatalkan); suite `k3-cleanup` dan `k4-runner-17` lulus | `scripts/cp7-src/planning/analysis-stages.sql` (`work_immutable`, `clean_done`, `purge_expired`, `purge_intermediates`); `scripts/cp7_analysis_stages_bundle.py` | kasus Fable PASS di mesin writer (step 0,02 dtk, `unit_attempts` 0); `K3C_RACE_CLEANUP_BESIDE_RUNNING_STEP` |
| F-UI-01 major | Dashboard mode terhubung tanpa angka karangan (owner 12 Okt: sembunyikan) | `src/OwnerDashboard.tsx`, `src/App.tsx` | `src/OwnerDashboard.dom.test.tsx`; kasus browser Fable dijalankan auditor |
| F-OPS-03 | verifikasi dengan isi dump, atau receipt "belum terverifikasi" diterima owner | `cp7_nightly_backup.py` (snapshot ekspor) | `FABLE_CORE:BACKUP_VERIFY_UNDER_LIVE_WRITES` PASS di mesin writer; `K3C_RACE_BACKUP_VERIFIED_UNDER_WRITES` |
| F-OPS-04 | `--database` dicek sama dengan `current_database()` | `scripts/cp7_schedule.py` | kasus K3 jadwal |
| F-AN-01 | >5.000 target ditolak saat request dengan kode yang dideklarasikan | `analysis-stages.sql` `request()` | `cp7_p19_staged_cases.py`, `f05-staged-api.test.ts` |
| F-PAY-01, F-AP-01, F-TOOL-01..03, F-UI-02, F-DOC-01, OBS-01..03 | sesuai disposisi `README.md` | lihat `README.md` | lihat `README.md` |

## Regresi yang mungkin terdampak

- Semua suite yang memakai tabel kerja analisis bertahap (K2, K3, K4, P19 staged, plan v2, report v2, AI v2, reminder
  v2): trigger tabel kerja berubah. Ke-15 workflow kualifikasi dijalankan pada `7a0b4a90`.
- PL-5 B: admin tidak lagi bisa menyimpan versi kebijakan (keputusan owner).
- Alat uji tanggal WIB: hanya menambah anotasi; logika ASF-F01 tidak berubah sejak `5f1506f4`.
- `CP7 Supplier Payment Create` gagal dua kali (`7a0b4a90` run 38288829388, `5656f072` run 38330557862) di pemeriksaan
  batas akhir kelompok native dengan semua kasus PASS. Sesudah diagnosis dipasang (13 Okt): 9 run kualifikasi dan 60
  grup ulang: kegagalan tidak terulang pada pengujian berikutnya; penyebab dua kegagalan **belum ditemukan** (OPEN).
  Rincian dan yang sudah diperiksa:
  `../../evidence/fable-retest-20261012/GROUP_END_DIAGNOSIS.md`. Auditor dipersilakan mengulang dan menilai sendiri.
- Area yang tidak disentuh `SOURCE_DELTA.json` boleh tidak diulang; tulis BELUM DIULANG, bukan LULUS.

## Perubahan sesudah kandidat (13 Okt 2026, atas permintaan owner)

Kode produk (`supabase/`, `src/`, `scripts/cp7-src/`) tidak berubah sejak `7a0b4a90`. Yang berubah hanya alat uji:

| Berkas | Isi | Bukti |
|---|---|---|
| `scripts/cp6_auditor_runner.py`, `scripts/cp6_auditor_difference.py`, `scripts/cp6_auditor_runner_difference_test.py`, `.github/workflows/claude-p08-shell.yml` | Diagnosis: bagian yang berbeda dicatat bila pembanding batas gagal. Pembanding sendiri tidak diubah. | `../../evidence/fable-retest-20261012/GROUP_END_DIAGNOSIS.md` |
| `scripts/cp7_group_end_repeat_diagnosis.py`, `.github/workflows/cp7-group-end-diagnosis.yml` | Uji ulang grup native bayar supplier (hanya diagnosis, dispatch saja) | idem, bagian 3 |
| `scripts/cp7_k3_cleanup_cases.py`, `docs/cp7/k3/K3_CLEANUP.json`, `scripts/cp7_f05_analysis_probe.py`, `.github/workflows/claude-p19-transport.yml`, `.github/workflows/cp7-nightly-backup.yml` (komentar) | Kasus ke-23 K3: gladi pemasang jadwal di salinan CI | `../../evidence/fable-retest-20261012/SCHEDULE_REHEARSAL.md` |

## Hasil yang diminta

1. F-OPS-01, F-OPS-02, F-UI-01: DITUTUP / MASIH TERBUKA, dengan run, kasus dan oracle auditor.
2. Minor dan observasi: disposisi diterima / tidak, dengan alasan.
3. Regresi: LULUS / GAGAL / BELUM DIULANG.
4. Temuan baru bila ada (ID, keparahan, reproduksi, bukti, dampak).
5. Vonis audit penuh CP7 sesudah perbaikan ini dan syarat pemasangan jadwal/backup yang tersisa (Fable §2.2 dan §2.5).
6. Bila auditor bukan Astra dan bersedia: penerimaan area optimasi timeline PR44 dengan probe
   `scripts/cp7_astra_timeline_reuse_probe.mjs` yang sudah diperbaiki (workflow `CP7 Astra Timeline Reuse`) dan kontrol
   sendiri.
