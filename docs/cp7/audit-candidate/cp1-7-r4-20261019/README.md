# Paket uji ulang r4 CP1–CP7 (perbaikan atas audit r3 `b53b5acd`)

**Status: SIAP DIKIRIM — kandidat `663f6fae`, kualifikasi selesai (bagian Kandidat).**

Fable, Astra dan Sol menguji ulang kandidat r3 `b53b5acd`. Penulis menyatukan ketiga laporan per akar masalah di
`CROSS_AUDIT.md`, memperbaiki temuan Astra (R4-01 sampai R4-04), memeriksa keabsahan tiga butir Sol, dan mengerjakan
kecepatan analisis langsung atas keputusan owner D17-1 (R4-05), semuanya di cabang `claude/r4-fixes-20261018`. Paket ini
satu kandidat untuk ketiga auditor. Owner yang mengirim: salin kotak di `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan
`HANDOFF_SOL.md` ke sesi masing-masing auditor. Penulis tidak mengirim apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perbaikan per akar, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan r3 dan rencana r4 |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat `663f6fae` |
| `CI_RECEIPT_FIRST_769f2cc3.json` | Kualifikasi pertama pada `769f2cc3` (ditarik, R4-Q1) |
| `../../cp17/r4-sol/` | Pemeriksaan keabsahan butir Sol dan patch backup yang disiapkan untuk CP7C (tidak dipasang) |
| `../../p19/P19_R4_05_DIRECT_LATENCY.md` | Diagnosis, perubahan dan hasil kecepatan analisis langsung (R4-05) |
| `../../cp17/R4_WRITER_HANDOFF.md` | Serah-terima untuk penulis cadangan, termasuk log titik simpan (bukan untuk auditor) |

## Kandidat

- **Commit `663f6faefcbb9c70f0f99bbc7e78164e03521329`**, tree `023f3554432f80f994439f5d0b8cc164846a2041`, di cabang
  `claude/new-session-deapao` (di-fast-forward dari `claude/r4-fixes-20261018`). Commit sesudahnya di cabang itu hanya
  mengubah `docs/`: `git diff --name-only 663f6fae origin/claude/new-session-deapao`. Basis r3: `b53b5acd` (tree
  `32f54240a60e01ab8b1ffad7267d285a669be520`). `supabase/` tidak berubah sejak `b53b5acd`.
- **`CI_RECEIPT.json`:** 116 run dari 115 workflow pada commit itu (115 workflow yang sama dengan receipt r3; CP6 Auditor
  Scenario dua kali: contoh bawaan dan skenario penulis lengkap); 94 run lulus; 179 job, 157 lulus; semua percobaan
  pertama. Receipt dibuat dengan `scripts/cp7_ci_receipt.py` di repo.
- **22 run merah, semuanya sudah merah di r3 dengan sebab yang sama** (tidak ada pemeriksaan yang dilonggarkan):
  - 21 workflow CP6 lama: 20 pemeriksaan cakupan historis (skrip cakupan memastikan checkout masih usulan lamanya) dan
    CP6 AF Posted Child Family (artifact 10418502157 kedaluwarsa). Job dan langkah yang gagal sama persis dengan run r3
    masing-masing (dibandingkan per run, 21 dari 21).
  - Skenario penulis CP6 lengkap (`scripts/cp6_bf_combined_modes.py` + `scripts/cp6_bf_vendor_browser.mjs`, run
    39180053859): native 104/104, race 26/26, HTTP 9/9, browser 27 PASS dan 4 INCOMPLETE yang sama dengan r3:
    `READINESS_BROWSER:{DESKTOP,MOBILE}_NATIVE_POLICY_STATES_FINANCE_NOTE` (layar keuangan memanggil
    `erp_cp7_get_recost_queue_v1`, yang tidak ada di tumpukan CP6 skenario ini) dan `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}`
    (dipensiunkan, `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md`). Contoh bawaan (run 39173288385) lulus.
  - CP6 AC Independent Audit tidak punya pemicu manual (tidak dijalankan), sama dengan r3.
- **Kasus CP17:** run 39173236062, job 117810508835: 341 kasus yang dideklarasikan PASS, 0 gagal (Native 161, race 39,
  HTTP 27, browser 57, browser build Enteng 57), ditambah `CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER`. Di grup build Enteng
  1.361 permintaan ke alamat proyek Enteng dijawab API lokal runner; 2 jawaban tidak sampai karena halamannya sudah
  ditutup (`route.fetch: Request context disposed`, bacaan daftar bahan dan transfer bahan), dicatat oleh alat uji
  (best practice E25d); r3: 0.
- **P19 skala:** run 39173212515, job p19-scale5: semua kasus PASS. Runner kualifikasi ini lebih lambat; angkanya
  (100 target dengan angka keuangan 4,57–5,92 detik) ada di `../../p19/P19_R4_05_DIRECT_LATENCY.md` bagian
  "Qualification run".
- **Kualifikasi pertama pada `769f2cc3`** (`CI_RECEIPT_FIRST_769f2cc3.json`, 115 run, 93 lulus): dibanding r3 hanya CP7
  P19 Analysis Job Transport yang baru merah (R4-Q1, di bawah). Karena alat uji berubah, kandidat baru `663f6fae`
  dikualifikasi ulang penuh. Sesudah `769f2cc3` hanya alat uji, alat jadwal (fungsi baca baru, tidak dipakai
  pemasangan) dan dokumen yang berubah. Uji pembuktian perbaikan di cabang r4 sebelum kualifikasi: run 39168052459,
  12/12 job lulus.

## Perbaikan per akar

Kasus CP17 dideklarasikan sebelum dijalankan di `docs/cp7/cp17/CP17_FIXES.json` (bagian `findings`, bahasa Inggris) dan
dijalankan workflow "CP7 CP17 Fixes". Jumlah kasus: 341 (Native 161, race 39, HTTP Auth nyata 27, browser 57, dan 57 kasus
browser yang sama di build mode Enteng); r3 punya 321. Kasus gagal auditor dipakai apa adanya; penjaga lama tidak
dilonggarkan.

| Akar | Temuan | Yang berubah | Uji |
|---|---|---|---|
| R4-01 jalur publik lama | ASTRA-R3-01, Sol KNOWN-POOL-PUBLIC-ENTRYPOINTS | 25 fungsi publik lama yang tidak dipakai aplikasi (termasuk empat pembungkus pool HPP CP4) menolak sesi Data API (`session_user` `authenticator`) sebagai pernyataan pertama: 42501 `CP7_PUBLIC_ROUTE_CLOSED`, detail nama rute. Definisi, hak dan pemanggilan Native tetap; sesi database (operator, migrasi, fixture) tidak berubah; batas SQL langsung tetap batch pencabutan CP7C (FABLE-012, D14-9). Sensus: fungsi publik baru yang bisa dijalankan peran browser, termasuk `anon`, gagal sampai ditinjau. `scripts/cp7_public_routes_bundle.py` | Dua kasus HTTP Astra apa adanya (`CP17_HTTP_R4_01_POOL_PUBLIC_CLOSED_PERIOD_ASTRA`, `..._REVOKED_MANAGE_ASTRA`), 25 rute ditolak lewat Auth nyata tanpa tulis dan rute aplikasi tetap menjawab, sesi database vs Data API, sensus gagal untuk rute baru/anon/rute tertutup tanpa penolakan |
| R4-02 buka ulang PO | ASTRA-R2-01 sisa | Gerakan negatif yang membalik pemasukan positif bukan pemakaian. `scripts/cp7-src/cutting-correction/po-reopen.sql` | Kasus Astra apa adanya (`CP17_R4_02_REOPEN_POSITIVE_ADJUSTMENT_INVERSE_ASTRA`), pemakaian aktif tidak tersembunyi, buka ulang lalu selesai lagi sama, dua tab |
| R4-03 Audit Trail | ASTRA-R3-02 | Setiap daftar membawa tanda isinya (juga di kursor); halaman berikut dengan tanda berbeda mengatakannya (`changed`, `newer`), layar berhenti dan meminta Muat ulang. `scripts/cp7-src/audit/audit.sql`, `src/ConnectedAuditTrailPage.tsx` | Jadwal tiga sesi Astra apa adanya (`CP17_RACE_R4_03_AUDIT_LOWER_ID_LATE_COMMIT_ASTRA`), tiga race kontrol, penolakan tanda/kursor |
| R4-04 teks terbaca | ASTRA-R3-03 | Kartu terang memberi warna teks gelapnya sendiri (WIP, Pola, panel pool HPP, tombol RecordTools BS, layar Master Data tersambung). Sensus keterbacaan: setiap teks terlihat diukur terhadap warnanya (WCAG); di bawah 2:1 ditolak di semua menu, desktop dan HP; angka WIP minimal 4,5:1 | `CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_{DESKTOP,MOBILE}` (+ build Enteng), sensus lebar HP build demo |
| R4-05 kecepatan analisis langsung | Sol KNOWN-P19-DIRECT-LATENCY, owner D17-1 | Diagnosis hitungan waktu per fungsi: penjaga `erp.require_internal()` dipanggil sekitar 32.000 kali per analisis dengan angka keuangan (3,9 dari 6,3 detik). Penjaga kini menjawab kasus tanpa baris konteks perintah dengan satu pemeriksaan (tanpa id transaksi: tidak ada baris; dengan id: satu pencarian di sepuluh tabel yang sama); dengan baris apa pun, urutan lama berjalan utuh. Layar analisis menulis "Sedang dihitung sejak jam …" seketika. `scripts/cp7_internal_guard_bundle.py`, `src/NativeAnalysisPanel.tsx` | `CP17_R4_05_INTERNAL_GUARD_SAME_ANSWER` (penjaga lama dan baru berdampingan, delapan pemanggil), `..._DISPATCH_REVIEWED`; sensus skala P19. 100 target dengan angka keuangan: 2,30–2,60 detik di browser pada run 39159625311 (sebelumnya 5,58–7,53 detik), tetapi 4,57–5,92 detik pada runner kualifikasi yang lebih lambat (r3: 4,16–4,62 detik pada runner yang lebih cepat); 300 target tetap di atas 3 detik (lihat `P19_R4_05_DIRECT_LATENCY.md`) |
| Sol: tulis pengganti saat cek pemulihan | KNOWN-BACKUP-REPLACEMENT-WRITE | Tidak dipasang (D13-9a). Patch `docs/cp7/cp17/r4-sol/CP7C_BACKUP_DISPOSABLE_SCRATCH.patch`: cek pemulihan hanya di server sekali pakai miliknya sendiri | Lokal penulis: 12/12 kasus off-site lulus dengan patch, kasus baru gagal tanpa patch; dijalankan di CI saat CP7C |

## Ditemukan penulis selama r4

- Sensus keterbacaan menemukan keluarga yang sama dengan ASTRA-R3-03 di layar tersambung dengan data (panel pool HPP,
  tombol RecordTools BS, Master Data); diperbaiki tanpa menurunkan ambang (log gagal disimpan penulis).
- F03 full di `27f04d72`: alat kesetaraan dispatch penjualan (`cp7_p19_sales_dispatch_equivalence.py`) membangun ulang
  penjaga pendahulu dari teks terpasang dan menemukan pemeriksaan R4-05. Pemeriksaan itu kini dicek terhadap dispatch yang
  diwakilinya lalu dikeluarkan dari pendahulu; keputusan dan oracle tidak berubah. Rerun lulus 8/8.
- R4-Q1, kualifikasi `769f2cc3` (run 39161868253, job k6-proof-runner-10): `K6P_RACE_PG_CRON_FINISHES_PASS` INCOMPLETE.
  Run pg_cron yang menyelesaikan putaran bukti menyimpan pekerjaannya lebih dulu, lalu pg_cron menulis statusnya; kasus
  membaca catatan run begitu putaran terlihat dan mendapati satu-satunya run masih "running". Celah yang sama ada di r3
  (lulus dengan satu run karena pembacaannya kebetulan lebih lambat). Kasus pg_cron K6 dan K4 dan fixture browser K4 kini
  membaca catatan sesudah jadwal dicabut, sesi pg_cron pergi, dan setiap run punya akhir tertulis (paling lama 60 detik;
  `scripts/cp7_schedule.py` `wait_recorded`). Syarat lulus tetap: minimal satu run selesai dan semua run selesai berhasil
  (browser: semua run berhasil). Log gagal disimpan penulis. Best practice E25g.

## Yang sudah diketahui penulis

- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a); build Enteng diuji terhadap salinan sekali pakai.
- FABLE-012 (hak langsung `authenticated` ke `erp`) tetap ditunda ke CP7C (D14-9); R4-01 menutup jalur publik lama untuk
  Data API, bukan batas SQL langsung.
- Analisis langsung: 300 target belum 3 detik; 100 target dengan angka keuangan belum stabil di bawah 3 detik (2,30–2,60
  detik pada satu runner, 4,57–5,92 detik pada runner kualifikasi). Dengan angka keuangan biaya laporan pemilik (Native)
  tumbuh dengan buku besar dan dibaca dua kali per analisis langsung; pemeriksaan ulang saat kirim sengaja dipertahankan.
- Workflow CP6 lama yang merah karena pemeriksaan cakupan historis dan artifact kedaluwarsa tetap merah dengan langkah
  yang sama seperti r3 (bagian Kandidat).

`production_go: false`.
