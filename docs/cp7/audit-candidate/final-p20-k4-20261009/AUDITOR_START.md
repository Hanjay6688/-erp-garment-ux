# Audit gabungan — uji ulang P20 + K4 (sesi auditor terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Owner 9 Okt: "kerjain dl aja nnti audit nya sekalian
semua" — uji ulang temuan P20 dan audit K4 dijadikan satu putaran. Perbaikan dan fitur writer adalah kandidat baru; hasil
writer di paket ini bukan penerimaan.

## Paste block untuk membuka sesi auditor

> Kamu auditor independen CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`).
> Kandidat yang diaudit adalah commit sumber `8cc1b0818fdba54f3ebeb64e132f7f3e20309e24` (tree `2ea854abca572afa923297b0c304e92703ede136`), tercatat di
> `docs/cp7/audit-candidate/final-p20-k4-20261009/CI_RECEIPT.json`. Audit commit itu, bukan HEAD lain; commit sesudahnya
> hanya dokumen — buktikan sendiri dengan `git diff --name-only 8cc1b081 HEAD` (semua harus di bawah `docs/`). Baca
> `docs/AUDIT_PANDUAN_PRO_MAX.md`, laporan dan handoff audit P20 di cabang `audit/astra-p20-2e605bb7-20261009`
> (`audit/astra_p20/REPORT.md`, `WRITER_HANDOFF.md`), lalu `README.md` dan `AUDITOR_START.md` di folder paket itu.
> Kerjakan dua bagian dengan oracle-mu sendiri: (1) uji ulang F01–F05 dengan kriteria retest di handoff P20 dan regresi
> yang terdampak; (2) audit K4 (penjalan server analisis bertahap) terhadap keputusan owner 8 Okt butir 6 dan kontrak
> `docs/cp7/k4/K4_RUNNER.json`. Selisih sumber ada di `SOURCE_DELTA.json` (dari `2e605bb7`) dan
> `SOURCE_DELTA_FROM_REVISION.json` (dari `870d4f79`). Batas: jangan mengubah `main`, deployment Cloudflare, Supabase
> hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan
> push ke `claude/new-session-deapao`, `cp7/integration` atau cabang audit P20 lama (pakai cabang audit baru); jangan
> memasang jadwal pg_cron atau backup malam di database mana pun selain salinan sekali pakai; jangan mengirim pesan ke
> orang lain; jangan meminta password/token/kunci; jangan melonggarkan oracle/guard; simpan log gagal pertama. Keputusan
> owner yang sudah disahkan tidak dibuka ulang. Area optimasi timeline PR44 tidak boleh diterima oleh auditor yang
> menulisnya. `production_go:false` tetap.

## Bagian 1 — uji ulang F01–F05

Ikuti `../revision-p20-20261009/AUDITOR_RETEST.md` (tabel temuan, kriteria retest, regresi). Sumber perbaikan F01–F05
tidak berubah sejak `870d4f79`; yang berubah di berkas jadwal hanyalah entri ketiga `cp7-staged-runner` (bagian 2).

## Bagian 2 — K4

| Pertanyaan audit minimal | Di mana |
|---|---|
| Job yang diminta halaman selesai tanpa halaman, dan hasilnya sama persis dengan halaman/jalur tunggal pada acuan yang sama? | `cp7_analysis_stage.run_next`, `cp7_ops.analysis_tick`, jadwal `cp7_ops.schedules()` |
| Halaman dan server (atau dua giliran server) tidak pernah menjalankan atau menyimpan unit yang sama; buka ulang = UUID, job dan run yang sama; tidak ada job baru atau hitung ulang? | kunci baris job (`for update skip locked`), `outputs` primary key, `request()` |
| Batas 8 dtk per unit tidak bisa dilewati: giliran tanpa `statement_timeout` ≤ 8 dtk ditolak sebelum apa pun dibaca/ditulis; batas diterapkan per pernyataan pada perintah pg_cron; unit yang dihentikan = percobaan, tiga kali = gagal; mode background-worker pg_cron tidak menjalankan giliran? | `run_next`, perintah jadwal, PostgreSQL `statement_timeout` |
| Hak aktor diperiksa ulang tiap unit tanpa sesi login: identitas permintaan = aktor tersimpan hanya selama unit, lalu dikembalikan; hak berubah/dicabut = gagal; berubah di tengah unit = unit dibuang; tidak ada jalan menjalankan unit sebagai aktor lain? | `run_next`, `cp7_schedule_native.access_now`, `cp7_private.access_now` |
| Job yang ditolak tidak menahan job lain (tidak ada antrean macet); job FAILED/DONE tidak disentuh? | `run_next` (urutan kemajuan paling lama) |
| Tidak ada jalur HTTP/`authenticated`/`service_role` ke penjalan; tabel `runner` privat dan tidak bisa dihapus? | grant, RLS, trigger |
| Layar tidak pernah menyebut "boleh ditutup" bila penjalan tidak aktif; teks lama tetap bila tidak aktif? | `src/nativeStagedJob.ts`, `src/NativeAnalysisPanel.tsx` |
| Penjalan tidak mengganggu pembersihan K3 (pembersihan menunda selama ada analisis bergerak) dan retensi K2? | `clean_pending`, `purge_expired` |
| Integritas uji: suite `k4-runner-16` tidak melemahkan oracle lama; perubahan deklarasi K3 hanya menambah entri jadwal? | `scripts/cp7_k4_runner_*`, `docs/cp7/k3/K3_CLEANUP.json` |

## Hasil yang diminta

1. F01–F05: DITUTUP / MASIH TERBUKA, dengan run, kasus dan oracle auditor.
2. K4: LULUS / GAGAL / BELUM DIPERIKSA per baris tabel di atas, dengan alasan.
3. Regresi area yang disentuh: LULUS / GAGAL / BELUM DIULANG.
4. Temuan baru bila ada (ID, keparahan, reproduksi, bukti, dampak).
5. Vonis kandidat dan syarat sebelum owner memberi izin memasang jadwal (pembersihan, hapus 7 hari, penjalan) dan
   backup malam. Penerimaan area PR44 tetap memerlukan auditor lain.
