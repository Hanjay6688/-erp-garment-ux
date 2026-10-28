# Sambungan CP7.5 → CP7C → CP8 — persiapan 28 Oktober 2026

Basis A3efecab / backend3194. Desain dan pemeriksaan sumber saja;
formal5/16, independent_acceptance=false, production_go=false.
Rancangan September tetap arsip kontrak; implementasi Oktober di bawah dipakai ulang.

## Backbone yang tersedia

| Sambungan nyata | Input → output / izin / kegagalan | Bukti dan gap |
|---|---|---|
| src/nativeStagedJob.ts: persistStagedRequest, parseStagedJob, driveStagedJob | UUID+payload+versi+sumber → status/unit/hasil; akses terkini; respons hilang dibaca dengan UUID sama | Backend3194 qualified; driver dan browser baru milik B. unit_count sebelum plan_final sementara |
| scripts/cp7_frozen_analysis_units_v2/cache.sql: binding/pack/unpack/unit_reference | Referensi frozen job → unit terikat sumber; metadata privat | Cache bukan ledger kedua; pergantian sumber/izin wajib menolak hasil current |
| scripts/current-factory-initial-stage/composition.py: sources/install/verify/rollback_preuse | Deklarasi sumber+cursor admin → rantai delta terverifikasi | All22, data/sequence/roles dan restore3194 PASS; dipakai sebagai sumber upgrade, bukan installer bersih baru |
| scripts/current-factory-initial-stage/worker.py: definitions | Unit0 frozen-v2 >=1000 target → worker privat16s; biasa8s; akses diperiksa dahulu | Cron aktual PASS. Pesan CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED ditangani tepat oleh B |
| scripts/cp7-src/ops/schedule.sql: schedules/analysis_tick/cleanup_tick/retention_tick/proof_tick; scripts/cp7_schedule.py: install/matches/uninstall | Definisi → jadwal target eksplisit; admin; konflik jadwal asing ditolak | Empat jadwal lama + satu initial dari delta; jangan membuat scheduler kedua |
| scripts/cp7-src/planning/report-staged.sql: report_request/report_status/report_document/report_section | Job/periode/request → laporan/arsip sesuai hak; financial readiness terpisah | Gunakan reader resmi dalam cp7_current_frozen_finance_installation dan successor consistency. DONE produksi tidak berarti finance READY |
| src/NativeAnalysisFinancePanel.tsx; src/nativeAnalysisFinanceSidecar.ts: parseAnalysisFinance | Respons server → progres/status/angka; akses dicabut menyembunyikan nilai | A279 95 tes lokal; backend3194 24 metrik; browser gabungan masih B |
| scripts/cp7-src/alerts/alerts.sql: collect_tick/send_tick/reconcile/wa_post/schedules | Reminder authorized → outbox → request provider → hasil transport | WA99 sink palsu; ACCEPTED/hasil HTTP bukan DELIVERED. Jangan menghitung uang/stok ulang di adapter |
| scripts/cp7_current_installation.py + cp7_install_legacy_inventory | Referensi minimum lama → receipt aturan aktif; admin; sumber/receipt berubah ditolak | Native4/inventory dan restore historis tersedia; default final harus mengikat seluruh delta terbaru |
| scripts/cp7_access_inventory.py: inventory/exposure_gate | ACL+declared schemas/search path+role overrides → gate | Inventaris 82 historis tidak diasumsikan tetap82; baca kondisi aktual sebelum aktivasi |
| scripts/cp7_offsite_backup.py: read_source/backup/Remote/prune; cp7_supabase_restore_drill.py: fetch_night/drill | Snapshot → encrypted dump → fetch → scratch restore → comparison | Folder/S3-local dan local Supabase terbukti historis; Drive nyata dan comparator mandiri dari backup belum terbukti |

## CP7.5 — satu jalur pemasangan dengan pembanding dua asal

Urutan: bekukan CP7 diterima → arsipkan sumber/manifest/installer/inverse dan Original
beserta kegagalan → dua database disposable dari baseline sah yang sama → jalur
upgrade existing versus pemasangan bersih yang baru disederhanakan → fixture bisnis
identik → bandingkan → restore kedua sisi. Belum membuat pemasang kedua sekarang.

Pembanding memakai katalog22 existing, semua baris dan sequence relevan, owner/ACL/RLS,
definisi fungsi, source registry/types serta official metrics dan pembaca bisnis.
UUID/waktu yang memang baru dipetakan eksplisit; jangan menghapus kolom agar diff hijau.
State job lama, arsip, posted/reversal, saldo dan stock/HPP harus tetap terbaca.
Unknown/zero serta aturan minimum aktif harus setara. DDL identik bukan satu-satunya
syarat; perbedaan struktur yang disengaja perlu daftar tepat dan bukti perilaku.

Lulus bila bisnis/data/hak/sequence setara dan kedua restore lengkap. Tolak bila
referensi sumber hilang, histori rusak, sumber tak dapat direproduksi atau privilege
melebar. Pensiunkan jalur lama hanya setelah archive→materialize→source verification
berhasil. Hindari kerja ulang dengan memakai sources()/verify()/catalog existing;
gap nyata: baseline bersih final, adapter equivalence dan eksekusi dua asal belum ada.

## CP7C — operasi mandiri memakai penjalan dan outbox existing

Urutan: CP7.5 diterima → inventaris paparan/ACL aktual → audit/revoke FABLE-012 sebelum
jalur menjadi reachable → konfigurasi disabled dan rencana egress → gladi disposable
→ backup Drive proof ketika tahapnya diotorisasi → backup awal terverifikasi → izin
pemasangan terpisah → aktivasi bertahap. Saat ini tidak ada aktivasi atau permintaan secret.

| Gangguan | Kontrak penerimaan dan pemulihan yang harus diuji |
|---|---|
| Browser ditutup/dibuka | Worker tetap berjalan; UUID/run yang sama; progres server; tidak submit/simpan ganda |
| Worker putus sebelum/sesudah commit | Unit committed sekali; unit belum committed dapat dilanjutkan; attempt/lock terbatas; bukan job baru otomatis |
| Respons hilang | UNKNOWN/VERIFYING sampai lookup; request/body sama; pesan yang mungkin terkirim tidak diulang buta |
| Jadwal terlewat/berulang | Catat occurrence dan kebijakan catch-up; tidak menganggap “seharusnya jalan” sebagai DONE; uji overlap lima jadwal ops dan tiga WA |
| Akses/sumber berubah | Recheck setelah wait, sebelum hasil/pesan/apply; sumber berubah memerlukan hasil baru, akses dicabut menahan payload |
| Provider timeout/reject/accepted | Pisahkan job selesai, hasil layak tampil, provider menerima, dan delivery terkonfirmasi; unsupported receipt diberi label |
| Restore | Egress/jadwal tetap nonaktif; rekonsiliasi send watermark/outbox sebelum hidup; jangan mengirim ulang pesan dari snapshot lama |

Konfigurasi sumber aktual: alerts.defaults() sudah240 menit (D17-7), collect/send tiap
menit, reminder baru lewat trigger; digest defaults08:00/15:00 dan quiet21:00–06:00
adalah default aplikasi yang harus ditinjau, bukan jam bisnis baru yang disahkan.
Cleanup */5, retention02:30WIB, runner tiap menit, proof */10; initial tambahan16s
hanya unit0 besar. Backup01:00WIB/14 malam terverifikasi tetap konfigurasi terdokumentasi.
Jadwal tick tiap menit berbeda dari interval analisis240 menit; jangan mengganti salah satunya.

Backup pakai alat existing dan workflow ops/backup-repo/workflows/nightly-backup.yml
pada repo privat Rp0 sesuai D13-8. Gap: Drive upload→fetch→hash→restore nyata;
restore dari snapshot yang diambil kembali dengan comparator yang ikut backup,
tanpa database sumber masih hidup; target hosted-like, Auth/config non-dump, kuota,
retensi dan pengujian kegagalan. Alat sekarang membandingkan ke sumber hidup;
menambah comparator terenkripsi pada alat yang sama memerlukan audit terarah.
Lulus lokal bukan Drive/hosted PASS. D14-9: declared Dashboard schemas juga perlu
bukti konfigurasi aktual; SQL tidak dapat membaca Dashboard dengan sendirinya.

## CP8 — rehearsal, GO, dan pemulihan sesudah transaksi

Urutan: kandidat diterima + sumber terkunci → tujuan Enteng postgres dikonfirmasi
sesuai D13-7 → konfigurasi/Auth/RLS/facade/roles dan versi/extension dibandingkan →
backup awal Drive verified → rencana pembersihan UAT yang terpisah dan direview →
saldo awal/material/lot/utang/piutang/kas serta opening provenance direkonsiliasi →
rehearsal pembelian sampai jual/retur/payroll/HPP/tutup buku → owner GO → transaksi
live kecil yang diotorisasi dan pemeriksaan hasil. Ledger/rumus existing dipakai.

Boleh lanjut hanya bila bukti final mencakup sumber terpasang, hak terkini, saldo dan
alur bisnis penting, backup/restore serta operator runbook. Berhenti pada source
mismatch, angka/readiness tidak terbukti, paparan akses, restore gagal, konfigurasi
minimum hilang, atau GO belum ada. Tidak menetapkan RPO/RTO bisnis tanpa keputusan.

Sebelum transaksi live pertama: inverse hanya jika preuse guard mengizinkan dan
katalog/data tepat, atau pulih ke target baru dari backup verified. Sesudah transaksi
sah baru masuk: jangan menimpa dengan backup lama; hentikan writer/egress, amankan
backup keadaan terbaru, inventaris transaksi pascabackup dan request ambigu, lakukan
perbaikan maju/koreksi tertaut atau recovery ke target baru dengan rekonsiliasi semua
transaksi sah. Owner menilai hasil dan memberi izin melanjutkan. Post-use inverse
refusal existing tetap dihormati. Ini rencana; belum ada cutover/UAT cleanup/hosted write.

Sumber dasar: framework-v2/01,02,06; automation-seam.md; OFFSITE_BACKUP.md;
OWNER_DECISIONS_20261008.md D13-7/8/9a, D14-9, D17-7/14/16/18.
