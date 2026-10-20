# Paket uji ulang r6 CP1–CP7 (atas audit r5 `17fa2507`, WhatsApp D17-3..D17-7, stok minimum D17-8..D17-12)

**Status: BELUM SIAP DIKIRIM — kandidat `55c885d1` sudah dikualifikasi (bagian Kandidat), tetapi pemeriksaan D17-13
(`../../D17_13_PENUNDAAN_PENULIS_20261020.md`) menemukan tiga hal yang tidak sesuai keputusan owner; menunggu keputusan owner
apakah dibetulkan dulu.** Dua kandidat sebelumnya
tidak dikirim: `b1649535` (owner meminta rumus titik pesan ulang disambungkan dulu, D17-9) dan `3b7bb381` (sebelum dikirim
owner memutuskan aksesori memakai batas minimum manual dan kain memakai satu judul pengingat, D17-10, lalu isian hitung
batas minimum aksesori di aplikasi, D17-12).

Fable, Astra dan Sol menguji ulang kandidat r5 `17fa2507`; ketiganya tidak menemukan cacat produk baru. Sol mengusulkan lima
penguatan uji untuk kasus R5 penulis (R6-01). Sesudah itu owner meminta pengingat diteruskan ke WhatsApp owner sendiri lewat
CallMeBot (D17-3..D17-6, R6-02), analisis otomatis bawaan tiap 4 jam (D17-7), dan titik pesan ulang barang jadi, kain dan
aksesori dihitung dari data ERP lalu diteruskan ke WhatsApp (D17-8, D17-9, R6-03). Sesudah itu owner memutuskan aksesori
tanpa rumus: batas minimum diketik atau dihitung aplikasi dari isian owner (MOQ, lama kirim dari Cina, perkiraan pemakaian
per bulan, cadangan), dan kain berumus masuk ke pengingat "Stok kain di bawah minimum" (D17-10..D17-12). Penulis menyatukan ketiga
laporan r5 di `CROSS_AUDIT.md`. Paket ini satu kandidat untuk ketiga auditor, dan menjadi pemeriksaan terakhir sebelum CP7C
(CP7C tetap ditahan, D13-9a). Owner yang mengirim: salin kotak di `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan
`HANDOFF_SOL.md` ke sesi masing-masing auditor. Penulis tidak mengirim apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perubahan per butir, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan r5 dan rencana r6 |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat `55c885d1` |
| `RED_RUNS_VS_R6.json` | Setiap run merah pada `55c885d1` dibandingkan dengan run merah workflow yang sama pada kandidat sebelumnya `3b7bb381`: job dan langkah gagal |
| `RED_RUNS_VS_R5.json` | Perbandingan yang sama untuk kandidat pertama `b1649535` terhadap r5 (riwayat) |
| `../../WA_CALLMEBOT_DESIGN_20261019.md` | Desain penerusan WhatsApp (bahasa owner) |
| `../../wa/STOCK_FORMULA_FG_DESIGN.md` | Desain titik pesan ulang dengan rumus: barang jadi, kain, aksesori; beda dari usulan |
| `../../wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md` | Usulan yang disetujui owner (D17-9) |
| `../../wa/WA_FORWARD.json` | 58 kasus WhatsApp dan stok minimum yang dideklarasikan sebelum dijalankan |
| `../../evidence/stock-formula-rounding-20261020/` | Log lokal: kasus batas pembulatan gagal di kode lama dan lulus sesudah perbaikan (E25v; bukan bukti CI) |
| `../../wa/CP7C_INSTALL_FINDINGS_20261019.md` | Temuan pemasangan F1–F3 untuk CP7C (dari uji tumpukan WhatsApp) |
| `../../wa/WA_WRITER_HANDOFF.md` | Serah-terima penulis WhatsApp, termasuk log titik simpan (bukan untuk auditor) |

## Kandidat

- **Commit `55c885d1a12336905e433e05852b99be4d933f74`**, tree `80622a93bbbd2fb6295546aa00f1dc5eb919d827`, di cabang
  `claude/new-session-deapao`. Commit sesudahnya di cabang itu hanya mengubah `docs/`:
  `git diff --name-only 55c885d1 origin/claude/new-session-deapao`. Basis r5: `17fa2507` (tree
  `65f778479093d869a3354c0b9f19b4d9a541d98a`). Kandidat r6 sebelumnya: `b1649535` (tree
  `954d3ef3c9cbf544cfd66d6f8ddb49d8fd243329`) dan `3b7bb381` (tree `b9487027918f53e18b1aa9e2baf8ccb911055b2e`); beda dari
  `3b7bb381`: `git diff --stat 3b7bb381 55c885d1 -- src supabase scripts tests .github` (16 berkas: modul stok minimum bahan,
  gabungan judul kain di modul pengingat, isian aksesori, panel bahan dan Pengingat sistem, kasus dan uji layar).
  `supabase/` tidak berubah sejak r5. `src/` berubah hanya untuk layar Reminder (tab Pengingat sistem dan Sambungan
  WhatsApp) dan panel Titik pesan ulang / Batas minimum aksesori (Ringkasan Barang Jadi, Bahan & Roll, Aksesori, Kain &
  Benchmark, Aksesori & Harga Mandor).
- **`CI_RECEIPT.json`:** dibuat dengan `scripts/cp7_ci_receipt.py`: 117 run (116 workflow kualifikasi + satu run skenario
  CP6), 96 lulus; 182 job, 160 lulus; tidak ada percobaan kedua karena pergantian hari.
- **Run merah:** 21 run merah, semuanya workflow CP6 lama, dan ke-21 punya job dan langkah gagal yang sama dengan run
  merah workflow yang sama pada `3b7bb381` (`RED_RUNS_VS_R6.json`). P19 lulus pada percobaan pertama.
- **Skenario penulis CP6 lengkap — salah berkas, diulang:** run 39385942007 lulus, tetapi penulis menjalankannya dengan
  berkas skenario `scripts/cp6_be_modes.py` / `scripts/cp6_be_browser.mjs` (17 kasus), bukan berkas skenario lengkap yang
  dipakai `b1649535` dan `3b7bb381` (`scripts/cp6_bf_combined_modes.py` / `scripts/cp6_bf_vendor_browser.mjs`: 104 kasus,
  26 race, 9 HTTP, 31 browser). Run itu **tidak** dihitung sebagai skenario lengkap. Skenario lengkap dijalankan ulang
  dengan berkas yang benar: run 39396888098 di `c512a178` (sesudah `55c885d1` hanya `docs/` yang berubah:
  `git diff --name-only 55c885d1 c512a178`). Hasil (job 118541720668): INCOMPLETE, sama dengan `b1649535` dan `3b7bb381`:
  104 kasus, 26 race, 9 HTTP PASS; browser 27 PASS dan 4 INCOMPLETE yang sama dengan alasan yang sama (`READINESS_BROWSER`
  desktop/HP: fungsi `erp_cp7_get_recost_queue_v1` dan `erp_cp7_get_hpp_pools_v1` tidak ada di tumpukan CP6 skenario ini;
  `BF_BROWSER:SALES_MANUAL_13` desktop/HP: isian ukuran tidak tampil). Berkas skenario dan hash-nya sama persis dengan run
  kandidat sebelumnya. Best practice E25w.
- **Kasus CP17:** run 39385547471, job 118504391137: 345 kasus yang dideklarasikan PASS (Native 165, race 39, HTTP 27,
  browser 57, browser build Enteng 57). Di grup build Enteng 1.377 permintaan ke alamat proyek Enteng dijawab API lokal
  runner; 1 jawaban tidak sampai karena halamannya sudah ditutup saat kasus selesai ("Request context disposed"; r4: 2, r5: 0,
  `b1649535`: 1, `3b7bb381`: 5): satu bacaan `erp_cp7_get_material_transfers_v1`. Ke-57 kasus tetap PASS. Suite CP17 tidak
  memasang modul stok minimum; modul dipasang bersama seluruh lapisan CP7 saat CP7C.
- **Kasus WA dan stok minimum:** run 39385547480, job 118504823367 (wa-forward-58): 58 kasus yang dideklarasikan PASS
  (Native 41, termasuk 22 kasus `SS1_*`/`SS2_*`/`SS3_*`; race 6; HTTP 4; browser 7); uji tumpukan wa3a (job 118504823185)
  lulus; `cp6_restored` dan gerbang advisor benar. Kasus batas pembulatan PASS di CI: 350,00 dan 100,00 (aksesori), 2 pcs
  (barang jadi, cadangan hari). Penerusan kain: satu judul "Stok kain di bawah minimum" berisi "sisa 30 YD, dipesan 0 YD,
  minimum rumus 39,32 YD" dan "sisa 100 YD, minimum 500 YD". 2.000 barang tiap menit: 539–572 ms (batas 3.000 ms).
- **P19 pada `3b7bb381` (riwayat):** run 39368267401 percobaan pertama: job p19-scale5 INCOMPLETE pada
  `P19S_BROWSER_DESKTOP_300` di langkah login (`.top-title strong` tidak tampil dalam 5 detik sesudah Masuk), sebelum klik
  yang diukur; 100, 1.000 dan 5.000 target PASS. Dijalankan ulang sekali pada commit yang sama: percobaan kedua lulus. Penyebab
  tidak bisa dibuktikan: alat uji tidak menyimpan tangkapan layar saat login gagal (usulan alat: simpan tangkapan layar dan
  log konsol bila login gagal). Layar login dan kerangka aplikasi tidak berubah sejak `b1649535`.

## Perubahan per butir

| Butir | Asal | Yang berubah | Uji |
|---|---|---|---|
| R6-01 penguatan kasus R5 | Sol r5, lima butir "Penguatan uji permanen" (bukan cacat produk) | Hanya `scripts/cp7_r5_cases.py`: (1) baseline wajib tepat 167 identitas detektor dan semuanya nol; (2) ke-11 pembaca lama dipasang bersama di `erp` dalam savepoint yang dibatalkan, jadi panggilan bersarang juga memakai grafik lama; (3) nilai buku persis di kedua grafik: PO 120/0/0 → 96/24/0 → 108/12/0, siklus +24/−12, NULL untuk jurnal yang tidak ada, jawaban banyak baris dan kosong; (4) satu PREPARE manual lintas ganti pemetaan FG_INVENTORY dengan auto-prepare mati: 120 → 0 → 120; (5) ke-167 keluaran detektor disimpan per fase di kontrol | CP17 pada kandidat (run 39368249559): `CP7_CP17_FIXES` PASS, 345 kasus |
| R6-02 Pengingat sistem dan penerusan WhatsApp | Owner D17-3..D17-6; bawaan analisis otomatis 240 menit (D17-7) | Modul CP7 baru `cp7_alert_native` di `scripts/cp7-src/alerts/alerts.sql` (pemasang `scripts/cp7_alert_bundle.py`): pengingat sistem dari sumber yang sudah diterima (stok kain di bawah minimum lewat Ringkasan Gudang, piutang dan tagihan jatuh tempo, pengingat pribadi owner yang waktunya tiba, kekurangan produksi dan kain dari analisis owner sendiri yang dicek ulang), antrean, pesan langsung, ringkasan, jeda dan jam tenang, kunci CallMeBot hanya di Vault, pengiriman lewat pg_net, tiga tick pg_cron (dibuat, tidak dipasang). Analisis otomatis bawaan tiap 240 menit (sebelumnya 60). Layar: Reminder tab **Pengingat sistem** (semua akun yang boleh membuka Reminder, per hak baca sumbernya) dan **Sambungan WhatsApp** (hanya Owner): `src/waContract.ts`, `src/SystemRemindersPanel.tsx`, `src/WaConnectionPanel.tsx` | Workflow "CP7 WA Forward": uji tumpukan (pasang dan copot sebagai `postgres`), kasus yang dideklarasikan di `docs/cp7/wa/WA_FORWARD.json`, hanya server CallMeBot palsu, nomor `+620000000000`, kunci `FAKEKEY-*`. Hasil pada kandidat: bagian Kandidat |
| R6-03 Titik pesan ulang dan batas minimum | Owner D17-8, D17-9 (usulan `PROPOSAL_SAFETY_STOCK_R6_20261020.md`), D17-10, D17-12 | Modul CP7 baru `cp7_stock_formula`: `scripts/cp7-src/stock-formula/formula.sql` (barang jadi) dan `materials.sql` (kain, aksesori), dipasang oleh pemasang WA sebelum `alerts.sql`. **Barang jadi dan kain:** titik = ceil(D × L + cadangan); cadangan z × σ × √L (tingkat layanan bawaan 95%) atau D × hari penyangga profil perencanaan, tidak pernah keduanya; jendela 30 hari WIB penuh; hari kehabisan stok tanpa pemakaian tidak dihitung permintaan nol; perlu ≥ 14 hari terhitung; dihitung sebagai satu pembilang dibagi satu penyebut (E25v). Barang jadi: penjualan POSTED, lama produksi terukur dari potong sampai QC, barang dalam produksi ikut posisi; pengingat `FG_AT_REORDER_POINT` "Stok barang jadi menipis". Kain: pemakaian potong, pabrik dan mandor; stok semua lokasi + sisa PO terbuka; lama kirim per kain diisi Owner/Admin, kosong = belum cukup data. **Satu pengingat kain (D17-10):** `FABRIC_BELOW_MINIMUM` "Stok kain di bawah minimum" untuk kain yang punya minimum di Kain & Benchmark (aturan Ringkasan Gudang, stok < minimum, sumber lama tidak diubah) dan kain berumus (stok + dipesan ≤ titik); gabungannya `cp7_alert_native.fabric_kind_source()`; jenis `FABRIC_AT_REORDER_POINT` dihapus. **Aksesori tanpa rumus (D17-10, D17-12):** batas minimum diketik, atau dihitung dari isian owner per aksesori (MOQ, lama kirim dari Cina, perkiraan pemakaian per bulan, cadangan hari): ke atas 0,01 dari pemakaian per bulan × (lama kirim + cadangan) ÷ 30; yang diketik menang; isian kurang dan tanpa minimum: tidak diingatkan; MOQ hanya info ("MOQ cukup untuk sekitar N hari"); pemakaian nyata diukur dan hanya ditampilkan; stok hanya yang "ada di gudang" (bukan pos servis, area periksa, area rusak); pengingat `ACCESSORY_AT_REORDER_POINT` "Stok aksesori menipis" bila stok ≤ minimum. Dihitung tiap menit, sekali per perintah; setiap pengingat dicek ulang sebelum dikirim. Layar: `src/FgReorderPanel.tsx`, `src/MaterialReorderPanel.tsx` (kain "Titik pesan ulang", aksesori "Batas minimum aksesori" dengan baris hitungan langsung). Desain: `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md` | Suite "CP7 WA Forward" yang sama: 22 kasus stok Native dengan pembanding dihitung ulang di Python dari angka fixture memakai pecahan eksak (bukan dari tabel modul), termasuk kasus batas yang hasil tepatnya bulat (350,00; 100,00; 2 pcs) dan 2.000 barang tiap menit; kasus penerusan WA kain (dua jenis kain di bawah satu judul) dan aksesori (dari isian hitungan); 2 race "kunci terpegang, cek ulang stok saat itu"; 2 HTTP Auth nyata; browser desktop dan HP (isian aksesori 20 / 300 / 5 / 5000 → 250,00). Hasil: bagian Kandidat |

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
- Pemantau CI penulis memakai SHA pendek dan tidak menemukan run; kini SHA penuh. Best practice E25o.
- Rumus stok (R6-03): hitungan tiap menit butuh 3,7 detik untuk 2.000 barang karena kompilasi JIT; kini 0,6 detik lokal
  (E25p). Hari kehabisan stok bukan permintaan nol, dan pembanding kasus dihitung ulang dari angka fixture (E25q). Tanda
  "sudah dihitung" pertama berkunci transaksi sehingga bacaan kedua di transaksi yang sama basi; kini berkunci waktu mulai
  perintah (E25r). Stok aksesori mengikuti aturan "ada di gudang" Bahan & Roll, bukan semua lokasi gudang bahan (E25s).
  Run 39360612119 menolak deklarasi WA sebelum kasus berjalan (RPC di deklarasi tidak sama dengan modul kasus); deklarasi
  kini dicek lokal dengan aturan probe (E25t). Run 39364244415: kasus HTTP bahan mengharapkan tingkat layanan 95%, padahal
  kasus HTTP barang jadi di depannya sudah menyimpan 99%; kasus kini membaca pengaturan yang berlaku (b9b11e1c), dan tiga
  kasus browser gagal karena layar belum mengenal jenis pengingat baru (layar digabung, c4c119f5).
- D17-10: dua sumber pengingat kain digabung tanpa mengubah sumber lama yang sudah punya pembanding
  (`WAF_FABRIC_EQUALS_WAREHOUSE_SUMMARY`); satu kain tidak boleh muncul di dua himpunan (E25u).
- D17-12, pembulatan: pemeriksaan layar yang menghitung ulang batas minimum secara eksak menemukan server memberi 350,01
  untuk 500 per bulan dengan 14 + 7 hari (tepatnya 350), karena 500/30 dibulatkan dulu baru dikali. Kelas yang sama ada di
  barang jadi mode cadangan hari (20 terjual dalam 30 hari, 2 + 1 hari: 3 pcs, tepatnya 2) dan rumus kain. Pembanding
  Python lama ikut salah karena membulatkan dengan cara yang sama. Diperbaiki di `2c43e713` (kali dulu baru bagi, pembanding
  pecahan eksak, kasus batas di `SS1_DAYS_BUFFER_NOT_STACKED` dan `SS3_ACCESSORY_MINIMUM_FROM_OWNER_ESTIMATE`); log lokal
  gagal di kode lama dan lulus sesudahnya di `../../evidence/stock-formula-rounding-20261020/`. Best practice E25v.

## Yang sudah diketahui penulis

- Lapisan CP7, termasuk WhatsApp dan rumus stok, belum terpasang di Enteng (CP7C ditahan, D13-9a). Tidak ada pesan WhatsApp
  sungguhan dan tidak ada kunci nyata; nomor dan kunci diisi owner sendiri di layar saat pemasangan (D17-6).
- Beda dari usulan (rincian di `../../wa/STOCK_FORMULA_FG_DESIGN.md`): (1) judul kain sudah diputuskan owner (D17-10): kain
  berumus masuk ke "Stok kain di bawah minimum", tidak ada judul terpisah; (2) kebutuhan aksesori dari rencana produksi tetap
  tidak diteruskan ke WhatsApp, karena analisis selalu menyatakannya "belum diketahui" (pemakaian aksesori per potong tidak
  tercatat); gantinya "Stok aksesori menipis" dari batas minimum; belum ada keputusan owner lain soal ini; (3) isian lama
  kirim kain dipasang di Master Data dan juga di Gudang, datanya satu. Angka manual barang jadi disimpan di tabel CP7
  `manual_points`, bukan di `erp.stock_policy_versions` (alasan di desain).
- Ringkasan Gudang tetap hanya mendaftar kain yang punya minimum di Kain & Benchmark; kain berumus terlihat di Pengingat
  sistem, WhatsApp dan panel Titik pesan ulang.
- Tingkat layanan 95% belum diuji ke data penjualan owner (tidak ada di lingkungan uji); diuji sesudah CP7C. Lama produksi
  terukur dimulai dari potong, karena waktu dari keputusan produksi sampai potong tidak tercatat.
- Lama kirim kain tidak tercatat di ERP; selama isiannya kosong, kain itu tidak punya titik rumus dan tidak diingatkan
  (kecuali kain dengan minimum di Kain & Benchmark). Aksesori tidak diingatkan sampai batas minimumnya diketik atau isian
  hitungannya lengkap di aplikasi. ERP lama tidak menyimpan pemakaian aksesori (D17-11), jadi perkiraan per bulan datang dari
  owner dan bisa dibandingkan dengan pemakaian nyata yang diukur ERP sesudah dipakai.
- BOM aksesori per warna/ukuran (kancing per warna, sleting per ukuran) dan laporan aksesori mandor (diambil lawan
  seharusnya terpakai): pertanyaan penulis ke owner belum dijawab; tidak dikerjakan di r6.
- `STOCK_AT_REORDER_POINT` dari README r6 pertama kini dibuat sebagai `FG_AT_REORDER_POINT` dan
  `ACCESSORY_AT_REORDER_POINT`; kain memakai `FABRIC_BELOW_MINIMUM` yang sudah ada.
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- KNOWN-P19-DIRECT-LATENCY tetap terbuka (S2, tidak diubah di r6): 100 target dengan angka keuangan sekitar 2,8–3,5 detik di
  browser pada run ketiga auditor dan kualifikasi r5; 300 target di atas 3 detik. 3 detik tidak ditandai tercapai.

`production_go: false`.
