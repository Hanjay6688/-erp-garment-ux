# Paket uji ulang r5 CP1–CP7 (perbaikan atas audit r4 `663f6fae`)

**Status: SIAP DIKIRIM — kandidat `17fa2507`, kualifikasi selesai (bagian Kandidat).**

Fable, Astra dan Sol menguji ulang kandidat r4 `663f6fae`. Fable dan Astra tidak menemukan cacat produk baru; Sol
menemukan satu (SOL-R4-001, S1). Penulis menyatukan ketiga laporan per akar masalah di `CROSS_AUDIT.md`, memperbaiki
SOL-R4-001 (R5-01) dan mengerjakan kecepatan analisis langsung dengan angka keuangan atas keputusan owner D17-2 (R5-02),
semuanya di cabang `claude/r5-fixes-20261019`. Paket ini satu kandidat untuk ketiga auditor. Owner yang mengirim: salin
kotak di `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` ke sesi masing-masing auditor. Penulis tidak mengirim
apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perbaikan per akar, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan r4 dan rencana r5 |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat `17fa2507` |
| `RED_RUNS_VS_R4.json` | Setiap run merah dibandingkan dengan run merah workflow yang sama di r4: job dan langkah gagal |
| `../../p19/P19_R5_02_REPORT_READERS.md` | Diagnosis, perubahan dan hasil kecepatan analisis langsung dengan angka keuangan (R5-02) |
| `../../cp17/R5_WRITER_HANDOFF.md` | Serah-terima untuk penulis cadangan, termasuk log titik simpan (bukan untuk auditor) |

## Kandidat

- **Commit `17fa25075ba77f0853c3c16f504288ace03eec35`**, tree `65f778479093d869a3354c0b9f19b4d9a541d98a`, di cabang
  `claude/new-session-deapao` (di-fast-forward dari `claude/r5-fixes-20261019`). Commit sesudahnya di cabang itu hanya
  mengubah `docs/`: `git diff --name-only 17fa2507 origin/claude/new-session-deapao`. Basis r4: `663f6fae` (tree
  `023f3554432f80f994439f5d0b8cc164846a2041`). `src/` dan `supabase/` tidak berubah sejak `663f6fae`.
- **`CI_RECEIPT.json`:** 116 run dari 115 workflow pada commit itu (115 workflow yang sama dengan receipt r3 dan r4; CP6
  Auditor Scenario dua kali: contoh bawaan dan skenario penulis lengkap); 94 run lulus; 179 job, 157 lulus; semua percobaan
  pertama. Receipt dibuat dengan `scripts/cp7_ci_receipt.py` di repo.
- **22 run merah, semuanya sudah merah di r3 dan r4 dengan job dan langkah gagal yang sama** (dibandingkan per run dengan
  r4, 22 dari 22, `RED_RUNS_VS_R4.json`; tidak ada pemeriksaan yang dilonggarkan):
  - 21 workflow CP6 lama: 20 pemeriksaan cakupan historis (skrip cakupan memastikan checkout masih usulan lamanya) dan
    CP6 AF Posted Child Family (artifact 10418502157 kedaluwarsa).
  - Skenario penulis CP6 lengkap (`scripts/cp6_bf_combined_modes.py` + `scripts/cp6_bf_vendor_browser.mjs`, run
    39216963720): native 104/104, race 26/26, HTTP 9/9, browser 27 PASS dan 4 INCOMPLETE yang sama dengan r3 dan r4:
    `READINESS_BROWSER:{DESKTOP,MOBILE}_NATIVE_POLICY_STATES_FINANCE_NOTE` (layar keuangan memanggil
    `erp_cp7_get_recost_queue_v1`, yang tidak ada di tumpukan CP6 skenario ini) dan `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}`
    (dipensiunkan, `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md`). Contoh bawaan (run 39216743258) lulus.
  - CP6 AC Independent Audit tidak punya pemicu manual (tidak dijalankan), sama dengan r3 dan r4.
- **Kasus CP17:** run 39216595138, job 117941786263: 345 kasus yang dideklarasikan PASS, 0 gagal (Native 165, race 39,
  HTTP 27, browser 57, browser build Enteng 57), ditambah `CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER` PASS. Di grup build
  Enteng 1.361 permintaan ke alamat proyek Enteng dijawab API lokal runner, 0 galat rute (r4: 2 jawaban tidak sampai karena
  halamannya sudah ditutup; kali ini 0).
- **P19 skala:** run 39216681775, job p19-scale5 (job 117942069254): semua kasus PASS. 100 target dengan angka keuangan:
  2,89 / 3,00 / 3,33 detik di browser (r4 di runner kualifikasi: 4,57–5,92 detik); rincian di
  `../../p19/P19_R5_02_REPORT_READERS.md` bagian "Qualification run".

## Perbaikan per akar

Kasus CP17 dideklarasikan sebelum dijalankan di `docs/cp7/cp17/CP17_FIXES.json` (bagian `findings`, bahasa Inggris) dan
dijalankan workflow "CP7 CP17 Fixes". Jumlah kasus: 345 (Native 165, race 39, HTTP Auth nyata 27, browser 57, dan 57 kasus
browser yang sama di build mode Enteng); r4 punya 341. Kasus gagal auditor dipakai apa adanya; penjaga lama tidak
dilonggarkan. `src/` dan `supabase/` tidak berubah sejak `663f6fae`.

| Akar | Temuan | Yang berubah | Uji |
|---|---|---|---|
| R5-01 pemeriksa upah ke borongan yang salah | SOL-R4-001 (S1) | `erp.run_v263a_payroll_integrity_checks()` mencari borongan baris Nota FG_REPAIR di `erp.fg_unsourced_repair_wages_v1` (`coalesce` produksi, rework, upah perbaikan barang jadi); cek lain di fungsi itu dan syarat Nota bukan REVERSED tetap. Delta Native yang dideklarasikan: teks asli disimpan di `originals` F03, pemasangan menolak bila teks Native yang ditemukan berbeda, pencopotan memulihkan teks asli. `scripts/cp7_payroll_checks_bundle.py`. Sapuan keluarga: cabang jenis sumber upah lain khusus sumbernya sendiri atau sudah mengenal FG_REPAIR (`CROSS_AUDIT.md`) | Kasus Sol apa adanya `CP17_R5_01_VALID_FG_REPAIR_NOTA_ZERO_ALARM_SOL`: 167 identitas detektor semua nol sebelum dan sesudah Nota yang sah; pemeriksa lama di salinan sekali pakai naik 0 → 2. Kontrol `CP17_R5_01_PAYROLL_CHECK_STILL_FINDS_WRONG_OR_MISSING_REPAIR`: upah milik borongan lain +1, upah yang hilang +1 |
| R5-02 kecepatan analisis langsung dengan angka keuangan | Sol/Fable/Astra KNOWN-P19-DIRECT-LATENCY, owner D17-2 | Diagnosis hitungan per fungsi (run kualifikasi r4 39173212515): pada 100 target dengan angka keuangan `erp.account_id` dipanggil 30.974 kali (2,48 dari 4,56 detik bersama penjaganya), karena sebelas pembaca cek keuangan menulis `erp.account_id('<KUNCI>')` langsung di saringan per baris jurnal. Kini `(select erp.account_id('<KUNCI>'))`: dihitung sekali per query. Pemetaan, penjaga dan angka sama. Pemasangan menolak kecuali ke-17 kunci adalah pemetaan inti yang terisi dan jumlah panggilan per pembaca persis seperti dideklarasikan. `scripts/cp7_report_accounts_bundle.py` | `CP17_R5_02_REPORT_READERS_SAME_ANSWER` (setiap pembaca terpasang dan pembaca tanpa perubahan berdampingan di buku CP17: setiap produk, PO, periode pocket, pelunasan saldo awal, pasangan jurnal penjualan/PO, tiga jendela laporan; ditambah, di savepoint yang dibatalkan, impor saldo awal dengan tiga potongan dan kredit pelanggan yang dipakai, impor produksi dengan periode pocket diposting, serta penjualan barang jadi saldo awal dan returnya; baris sama atau penolakan sama, dan gagal bila ada pembaca yang tidak pernah menjawab), `..._REVIEWED` (lima penolakan). 100 target dengan angka keuangan: server 4,56 → 2,25 detik, browser 4,57–5,92 → 2,89–3,33 detik (kualifikasi r4 lawan kualifikasi r5, runner sebanding); `P19_R5_02_REPORT_READERS.md` |

## Ditemukan penulis selama r5

- Saat menguji lokal (PG16 penulis, pembaca sintetis): PostgreSQL juga menghitung panggilan STABLE berargumen tetap saat
  memperkirakan rencana query, sehingga teks lama menolak kunci yang tidak dipetakan walaupun tidak ada baris; teks baru
  hanya menolak bila ada baris yang memerlukannya. Ditutup dengan syarat pemasangan: semua 17 kunci adalah pemetaan inti
  yang terisi, dan penjaga Native menolak hapus/ganti nama pemetaan inti. Best practice E25h.
- Pemeriksa teks laporan pemilik di F03 (`cp7_note_correction_verify.py`) mewajibkan teks terpasang sama persis dengan
  delta nota saja; sesudah R5-02 ia mewajibkan delta nota ditambah perubahan R5-02 yang dideklarasikan (tetap persis).
- Alat uji CP17 penulis tiga kali INCOMPLETE sebelum lulus (salinan pembanding di skema yang tidak bisa dipakai peran
  pemilik, lalu pembaca internal yang tidak diberikan ke peran browser); perbaikan di alat uji saja, log gagal disimpan
  penulis.
- Uji pembanding R5-02 sempat lulus walau tiga dari sebelas pembaca dibandingkan pada nol masukan (buku uji CP17 tidak punya
  kredit saldo awal, periode pocket atau jurnal penjualan; CI 39209921715). Uji kini membangun baris itu sendiri di
  savepoint yang dibatalkan dan gagal bila ada pembaca yang tidak pernah menjawab; lulus dengan semua pembaca menjawab
  (CI 39213380701 dan kualifikasi). Best practice E25i.

## Yang sudah diketahui penulis

- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a); build Enteng diuji terhadap salinan sekali pakai.
- FABLE-012 (hak langsung `authenticated` ke `erp`) tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C,
  tidak dipasang.
- Analisis langsung: 100 target dengan angka keuangan 2,89–3,33 detik di browser pada runner kualifikasi, dekat tetapi
  belum stabil di bawah 3 detik; 300 target tetap di atas 3 detik (dengan angka keuangan 1 dan 30 hari selesai sekitar 10
  detik, 100 hari berhenti di batas 8 detik dengan pesan). `P19_R5_02_REPORT_READERS.md` bagian "Still open". 3 detik tidak
  ditandai tercapai.

`production_go: false`.
