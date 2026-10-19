# Paket uji ulang r6 CP1–CP7 (atas audit r5 `17fa2507` dan pekerjaan WhatsApp D17-3..D17-6)

**Status: SIAP DIKIRIM — kandidat `b1649535`, kualifikasi selesai (bagian Kandidat).**

Fable, Astra dan Sol menguji ulang kandidat r5 `17fa2507`; ketiganya tidak menemukan cacat produk baru. Sol mengusulkan lima
penguatan uji untuk kasus R5 penulis (R6-01). Sesudah itu owner meminta pengingat diteruskan ke WhatsApp owner sendiri lewat
CallMeBot (D17-3..D17-6, R6-02). Penulis menyatukan ketiga laporan di `CROSS_AUDIT.md`. Paket ini satu kandidat untuk ketiga
auditor, dan menjadi pemeriksaan terakhir sebelum CP7C (CP7C tetap ditahan, D13-9a). Owner yang mengirim: salin kotak di
`HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` ke sesi masing-masing auditor. Penulis tidak mengirim apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perubahan per butir, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan r5 dan rencana r6 |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat |
| `RED_RUNS_VS_R5.json` | Setiap run merah dibandingkan dengan run merah workflow yang sama di r5: job dan langkah gagal |
| `../../WA_CALLMEBOT_DESIGN_20261019.md` | Desain penerusan WhatsApp (bahasa owner) |
| `../../wa/WA_FORWARD.json` | 24 kasus WhatsApp yang dideklarasikan sebelum dijalankan |
| `../../wa/CP7C_INSTALL_FINDINGS_20261019.md` | Temuan pemasangan F1–F3 untuk CP7C (dari uji tumpukan WhatsApp) |
| `../../wa/WA_WRITER_HANDOFF.md` | Serah-terima penulis WhatsApp, termasuk log titik simpan (bukan untuk auditor) |

## Kandidat

- **Commit `b1649535c42e9d8641a1128b02e60c23093a0685`**, tree `954d3ef3c9cbf544cfd66d6f8ddb49d8fd243329`, di cabang
  `claude/new-session-deapao`. Commit sesudahnya di cabang itu hanya mengubah `docs/`:
  `git diff --name-only b1649535 origin/claude/new-session-deapao`. Basis r5: `17fa2507` (tree
  `65f778479093d869a3354c0b9f19b4d9a541d98a`). `supabase/` tidak berubah sejak r5; `src/` berubah hanya untuk layar
  Reminder (tab Pengingat sistem dan Sambungan WhatsApp).
- **`CI_RECEIPT.json`:** 117 run dari 116 workflow pada commit itu (115 workflow r5 ditambah "CP7 WA Forward"; CP6 Auditor
  Scenario dua kali: contoh bawaan dan skenario penulis lengkap); 95 run lulus; 182 job, 160 lulus. Dibuat dengan
  `scripts/cp7_ci_receipt.py`.
- **Dua run lulus di percobaan kedua** (semua lainnya percobaan pertama; log percobaan pertama disimpan penulis):
  - CP6 AV Rev2 Qualification (run 39299915092): job "AR 174 original cases, AV package cycles and post-use refusal"
    berhenti di uji tolak-sesudah-dipakai, sebelum pemeriksaannya berjalan: pencopotan paket mensyaratkan database
    tanpa koneksi lain (`PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE`) dan masih ada sesi lain sesudah sekitar 20 detik
    menunggu. Alat AV tidak berubah sejak r5 (lulus di r5, run 39216748508). Percobaan kedua lulus. Alat ini mencoba
    ulang hanya penolakan itu (sejak run 38670698254); sesi mana yang bertahan belum tercatat di log, dicatat sebagai
    butir alat untuk penulis.
  - CP7 F03 Full Retained Components (run 39300027996): job `supplier_credit` mati sebelum kasus apa pun berjalan
    (unduhan repo terputus, lalu HTTP 403 saat memasang Supabase CLI). Percobaan kedua lulus.
- **22 run merah, semuanya sudah merah di r5 dengan job dan langkah gagal yang sama** (22 dari 22,
  `RED_RUNS_VS_R5.json`; tidak ada pemeriksaan yang dilonggarkan): 21 workflow CP6 lama (20 pemeriksaan cakupan historis
  dan CP6 AF Posted Child Family, artifact kedaluwarsa) dan skenario penulis CP6 lengkap (run 39300221708): native
  104/104, race 26/26, HTTP 9/9, browser 27 PASS dan 4 INCOMPLETE yang sama dengan r3–r5
  (`READINESS_BROWSER:{DESKTOP,MOBILE}_NATIVE_POLICY_STATES_FINANCE_NOTE`, `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}`,
  penjelasan di README r5). Contoh bawaan (run 39299908534) lulus. CP6 AC Independent Audit tidak punya pemicu manual.
- **Kasus CP17:** run 39299784250, job 118221634251: 345 kasus yang dideklarasikan PASS (Native 165, race 39, HTTP 27,
  browser 57, browser build Enteng 57). Di grup build Enteng 1.359 permintaan ke alamat proyek Enteng dijawab API lokal
  runner, 1 jawaban tidak sampai karena halamannya sudah ditutup ("Request context disposed"; r4: 2, r5: 0); ke-57 kasus
  tetap PASS.
- **Kasus WA:** run 39299833580, job 118221807839 (wa-forward-24): 24 kasus yang dideklarasikan PASS (Native 15, race 4,
  HTTP 2, browser 3); uji tumpukan wa3a lulus.
- **P19:** run 39299813990 (job p19-scale5 dan lima job P19 lain) lulus; latensi tidak diubah di r6.

## Perubahan per butir

| Butir | Asal | Yang berubah | Uji |
|---|---|---|---|
| R6-01 penguatan kasus R5 | Sol r5, lima butir "Penguatan uji permanen" (bukan cacat produk) | Hanya `scripts/cp7_r5_cases.py`: (1) baseline wajib tepat 167 identitas detektor dan semuanya nol; (2) ke-11 pembaca lama dipasang bersama di `erp` dalam savepoint yang dibatalkan, jadi panggilan bersarang juga memakai grafik lama; (3) nilai buku persis di kedua grafik: PO 120/0/0 → 96/24/0 → 108/12/0, siklus +24/−12, NULL untuk jurnal yang tidak ada, jawaban banyak baris dan kosong; (4) satu PREPARE manual lintas ganti pemetaan FG_INVENTORY dengan auto-prepare mati: 120 → 0 → 120; (5) ke-167 keluaran detektor disimpan per fase di kontrol | CP17 pada kandidat (run 39299784250): `CP7_CP17_FIXES` PASS, 345 kasus; sebelumnya juga run 39280347023 pada `97e42575` |
| R6-02 Pengingat sistem dan penerusan WhatsApp | Owner D17-3..D17-6 | Modul CP7 baru `cp7_alert_native` di `scripts/cp7-src/alerts/alerts.sql` (pemasang `scripts/cp7_alert_bundle.py`): pengingat sistem dari sumber yang sudah diterima (stok kain di bawah minimum lewat Ringkasan Gudang, piutang dan tagihan jatuh tempo, pengingat pribadi owner yang waktunya tiba, kekurangan produksi dan kain dari analisis owner sendiri yang dicek ulang), antrean, pesan langsung, ringkasan, jeda dan jam tenang, kunci CallMeBot hanya di Vault, pengiriman lewat pg_net, tiga tick pg_cron (dibuat, tidak dipasang). Layar: Reminder tab **Pengingat sistem** (semua akun yang boleh membuka Reminder, per hak baca sumbernya) dan **Sambungan WhatsApp** (hanya Owner): `src/waContract.ts`, `src/SystemRemindersPanel.tsx`, `src/WaConnectionPanel.tsx` | Workflow "CP7 WA Forward": uji tumpukan (pasang dan copot sebagai `postgres`), 24 kasus yang dideklarasikan (`docs/cp7/wa/WA_FORWARD.json`: Native 15, race 4, HTTP Auth nyata 2, browser 3), hanya server CallMeBot palsu, nomor `+620000000000`, kunci `FAKEKEY-*`. Hasil pada kandidat: 24/24 PASS (bagian Kandidat). |

## Ditemukan penulis selama r6

- Uji tumpukan WhatsApp memasang sebagai `postgres` (bukan superuser di Supabase): dua temuan pemasangan untuk semua bundle CP7
  (F1 serah objek ke peran baru butuh SET ROLE; F2 `postgres` tidak bisa meneruskan USAGE skema `auth`). Opsi perbaikan dan
  bukti di `../../wa/CP7C_INSTALL_FINDINGS_20261019.md`. Modul WhatsApp sudah memakai jalan aman untuk keduanya; bundle lain
  dibuktikan saat CP7C. Best practice E25j.
- CodeQL menolak server CallMeBot palsu karena mencetak kunci uji; kini hanya mencetak `key_ok`. Best practice E25k.
- Alat uji Native memasang sebagai `supabase_admin`, sehingga tabel `transport` sempat ikut pemiliknya; kini `alter ... owner
  to postgres` eksplisit, dan pemasangan diuji dengan dua pemasang. Best practice E25l.
- Run 39279865016 (22.41 WIB): tick analisis menjawab "di luar jam analisis" sebelum "Bos belum pernah menjalankan
  analisis"; urutan diperbaiki (keadaan analisis owner dulu, lalu sakelar, lalu jam), kasus kini memakai jam yang tidak
  memuat waktu sekarang. Data uji "pengingat orang lain" memakai peran Gudang yang memang ditolak modul pengingat; kini
  ADMIN. Best practice E25m dan E25n.

## Yang sudah diketahui penulis

- Lapisan CP7, termasuk WhatsApp, belum terpasang di Enteng (CP7C ditahan, D13-9a). Tidak ada pesan WhatsApp sungguhan dan
  tidak ada kunci nyata; nomor dan kunci diisi owner sendiri di layar saat pemasangan (D17-6).
- Kebutuhan aksesori tidak diteruskan ke WhatsApp: modul pengingat lama tidak pernah menjawab "masih terbuka" untuknya.
- `STOCK_AT_REORDER_POINT` belum dibuat (lihat desain).
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- KNOWN-P19-DIRECT-LATENCY tetap terbuka (S2, tidak diubah di r6): 100 target dengan angka keuangan sekitar 2,8–3,5 detik di
  browser pada run ketiga auditor dan kualifikasi r5; 300 target di atas 3 detik. 3 detik tidak ditandai tercapai.

`production_go: false`.
