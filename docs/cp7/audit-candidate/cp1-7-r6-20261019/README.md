# Paket uji ulang r6 CP1–CP7 (atas audit r5 `17fa2507`, WhatsApp D17-3..D17-7, rumus stok D17-8/D17-9)

**Status: BELUM SIAP DIKIRIM — kandidat `3b7bb381`, kualifikasi masih berjalan (bagian Kandidat).** Kandidat pertama paket ini,
`b1649535`, tidak dikirim: sebelum dikirim owner meminta rumus titik pesan ulang disambungkan dulu (D17-9).

Fable, Astra dan Sol menguji ulang kandidat r5 `17fa2507`; ketiganya tidak menemukan cacat produk baru. Sol mengusulkan lima
penguatan uji untuk kasus R5 penulis (R6-01). Sesudah itu owner meminta pengingat diteruskan ke WhatsApp owner sendiri lewat
CallMeBot (D17-3..D17-6, R6-02), analisis otomatis bawaan tiap 4 jam (D17-7), dan titik pesan ulang barang jadi, kain dan
aksesori dihitung dengan rumus dari data ERP lalu diteruskan ke WhatsApp (D17-8, D17-9, R6-03). Penulis menyatukan ketiga
laporan r5 di `CROSS_AUDIT.md`. Paket ini satu kandidat untuk ketiga auditor, dan menjadi pemeriksaan terakhir sebelum CP7C
(CP7C tetap ditahan, D13-9a). Owner yang mengirim: salin kotak di `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan
`HANDOFF_SOL.md` ke sesi masing-masing auditor. Penulis tidak mengirim apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perubahan per butir, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan r5 dan rencana r6 |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat `3b7bb381` |
| `RED_RUNS_VS_R6.json` | Setiap run merah pada `3b7bb381` dibandingkan dengan run merah workflow yang sama pada kandidat pertama `b1649535`: job dan langkah gagal |
| `RED_RUNS_VS_R5.json` | Perbandingan yang sama untuk kandidat pertama `b1649535` terhadap r5 (riwayat) |
| `../../WA_CALLMEBOT_DESIGN_20261019.md` | Desain penerusan WhatsApp (bahasa owner) |
| `../../wa/STOCK_FORMULA_FG_DESIGN.md` | Desain titik pesan ulang dengan rumus: barang jadi, kain, aksesori; beda dari usulan |
| `../../wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md` | Usulan yang disetujui owner (D17-9) |
| `../../wa/WA_FORWARD.json` | 57 kasus WhatsApp dan rumus stok yang dideklarasikan sebelum dijalankan |
| `../../wa/CP7C_INSTALL_FINDINGS_20261019.md` | Temuan pemasangan F1–F3 untuk CP7C (dari uji tumpukan WhatsApp) |
| `../../wa/WA_WRITER_HANDOFF.md` | Serah-terima penulis WhatsApp, termasuk log titik simpan (bukan untuk auditor) |

## Kandidat

- **Commit `3b7bb38178b54a86f07a849e5b59703b31778fc4`**, tree `b9487027918f53e18b1aa9e2baf8ccb911055b2e`, di cabang
  `claude/new-session-deapao`. Commit sesudahnya di cabang itu hanya mengubah `docs/`:
  `git diff --name-only 3b7bb381 origin/claude/new-session-deapao`. Basis r5: `17fa2507` (tree
  `65f778479093d869a3354c0b9f19b4d9a541d98a`). Kandidat pertama r6: `b1649535` (tree
  `954d3ef3c9cbf544cfd66d6f8ddb49d8fd243329`); bedanya: `git diff --stat b1649535 3b7bb381 -- src supabase scripts tests .github`.
  `supabase/` tidak berubah sejak r5. `src/` berubah hanya untuk layar Reminder (tab Pengingat sistem dan Sambungan
  WhatsApp) dan panel Titik pesan ulang (Ringkasan Barang Jadi, Bahan & Roll, Aksesori, Kain & Benchmark, Aksesori & Harga
  Mandor).
- **`CI_RECEIPT.json`:** dibuat sesudah dua run terakhir selesai (P19 percobaan kedua, skenario penulis CP6 lengkap). Dibuat dengan `scripts/cp7_ci_receipt.py`.
- **Run merah sejauh ini:** 116 run pertama selesai, 22 merah; 21 sama dengan kandidat pertama (job dan langkah gagal sama), satu baru (P19, di bawah). `RED_RUNS_VS_R6.json` dibuat sesudah dua run terakhir selesai.
- **Kasus CP17:** run 39368249559, job 118449927288: 345 kasus yang dideklarasikan PASS (Native 165, race 39, HTTP 27,
  browser 57, browser build Enteng 57). Di grup build Enteng 1.377 permintaan ke alamat proyek Enteng dijawab API lokal
  runner; 5 jawaban tidak sampai karena halamannya sudah ditutup saat kasus selesai ("Request context disposed"; r4: 2,
  r5: 0, `b1649535`: 1): dua bacaan panel Titik pesan ulang dan tiga bacaan Bahan & Roll. Ke-57 kasus tetap PASS. Suite
  CP17 tidak memasang modul rumus, jadi panel itu di sana menjawab galat server; modul dipasang bersama seluruh lapisan CP7
  saat CP7C.
- **Kasus WA dan rumus stok:** run 39368278547, job 118450018361 (wa-forward-57): 57 kasus yang dideklarasikan PASS
  (Native 40, termasuk 21 kasus rumus `SS1_*`/`SS2_*`/`SS3_*`; race 6; HTTP 4; browser 7); uji tumpukan wa3a lulus.
- **P19:** run 39368267401 percobaan pertama: job p19-scale5 INCOMPLETE pada `P19S_BROWSER_DESKTOP_300` di langkah login (`.top-title strong` tidak tampil dalam 5 detik sesudah Masuk), sebelum klik yang diukur; 100, 1.000 dan 5.000 target PASS. Layar login dan kerangka aplikasi tidak berubah sejak `b1649535`, dan job ini tidak memasang modul WA atau rumus. Job dijalankan ulang sekali pada commit yang sama; hasilnya dicatat di sini.

## Perubahan per butir

| Butir | Asal | Yang berubah | Uji |
|---|---|---|---|
| R6-01 penguatan kasus R5 | Sol r5, lima butir "Penguatan uji permanen" (bukan cacat produk) | Hanya `scripts/cp7_r5_cases.py`: (1) baseline wajib tepat 167 identitas detektor dan semuanya nol; (2) ke-11 pembaca lama dipasang bersama di `erp` dalam savepoint yang dibatalkan, jadi panggilan bersarang juga memakai grafik lama; (3) nilai buku persis di kedua grafik: PO 120/0/0 → 96/24/0 → 108/12/0, siklus +24/−12, NULL untuk jurnal yang tidak ada, jawaban banyak baris dan kosong; (4) satu PREPARE manual lintas ganti pemetaan FG_INVENTORY dengan auto-prepare mati: 120 → 0 → 120; (5) ke-167 keluaran detektor disimpan per fase di kontrol | CP17 pada kandidat (run 39368249559): `CP7_CP17_FIXES` PASS, 345 kasus |
| R6-02 Pengingat sistem dan penerusan WhatsApp | Owner D17-3..D17-6; bawaan analisis otomatis 240 menit (D17-7) | Modul CP7 baru `cp7_alert_native` di `scripts/cp7-src/alerts/alerts.sql` (pemasang `scripts/cp7_alert_bundle.py`): pengingat sistem dari sumber yang sudah diterima (stok kain di bawah minimum lewat Ringkasan Gudang, piutang dan tagihan jatuh tempo, pengingat pribadi owner yang waktunya tiba, kekurangan produksi dan kain dari analisis owner sendiri yang dicek ulang), antrean, pesan langsung, ringkasan, jeda dan jam tenang, kunci CallMeBot hanya di Vault, pengiriman lewat pg_net, tiga tick pg_cron (dibuat, tidak dipasang). Analisis otomatis bawaan tiap 240 menit (sebelumnya 60). Layar: Reminder tab **Pengingat sistem** (semua akun yang boleh membuka Reminder, per hak baca sumbernya) dan **Sambungan WhatsApp** (hanya Owner): `src/waContract.ts`, `src/SystemRemindersPanel.tsx`, `src/WaConnectionPanel.tsx` | Workflow "CP7 WA Forward": uji tumpukan (pasang dan copot sebagai `postgres`), kasus yang dideklarasikan di `docs/cp7/wa/WA_FORWARD.json`, hanya server CallMeBot palsu, nomor `+620000000000`, kunci `FAKEKEY-*`. Hasil pada kandidat: 57/57 PASS (bagian Kandidat) |
| R6-03 Titik pesan ulang dengan rumus | Owner D17-8, D17-9 (usulan `PROPOSAL_SAFETY_STOCK_R6_20261020.md`) | Modul CP7 baru `cp7_stock_formula`: `scripts/cp7-src/stock-formula/formula.sql` (barang jadi) dan `materials.sql` (kain, aksesori), dipasang oleh pemasang WA sebelum `alerts.sql`. Titik = ceil(D × L + cadangan); cadangan z × σ × √L (tingkat layanan bawaan 95%) atau D × hari penyangga profil perencanaan, tidak pernah keduanya; jendela 30 hari WIB penuh; hari kehabisan stok tanpa pemakaian tidak dihitung permintaan nol; perlu ≥ 14 hari terhitung. Barang jadi: penjualan POSTED, lama produksi terukur dari potong sampai QC, barang dalam produksi ikut posisi. Kain: pemakaian potong, pabrik dan mandor; stok semua lokasi + sisa PO terbuka. Aksesori: nota mandor dan pemakaian pabrik dikurangi retur nota layak pakai; stok "ada di gudang" (bukan pos servis, area periksa, area rusak). Lama kirim per bahan diisi Owner/Admin; kosong = belum cukup data, tidak ditebak. Dihitung tiap menit, sekali per perintah. Tiga jenis pengingat baru, dicek ulang sebelum dikirim: `FG_AT_REORDER_POINT`, `FABRIC_AT_REORDER_POINT`, `ACCESSORY_AT_REORDER_POINT`. Layar: panel Titik pesan ulang (`src/FgReorderPanel.tsx`, `src/MaterialReorderPanel.tsx`). Desain: `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md` | Suite "CP7 WA Forward" yang sama: 21 kasus rumus Native dengan pembanding dihitung ulang di Python dari angka fixture (bukan dari tabel modul), termasuk 2.000 barang tiap menit (CI 0,34 detik, batas 3 detik); 4 kasus penerusan WA; 2 race "kunci terpegang, cek ulang stok saat itu"; 2 HTTP Auth nyata; 4 browser desktop dan HP. 57/57 PASS |

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

## Yang sudah diketahui penulis

- Lapisan CP7, termasuk WhatsApp dan rumus stok, belum terpasang di Enteng (CP7C ditahan, D13-9a). Tidak ada pesan WhatsApp
  sungguhan dan tidak ada kunci nyata; nomor dan kunci diisi owner sendiri di layar saat pemasangan (D17-6).
- Tiga beda dari usulan, dua menunggu keputusan owner (rincian di `../../wa/STOCK_FORMULA_FG_DESIGN.md`, bagian "Beda dari
  usulan"): (1) kain yang memakai rumus diingatkan dengan judul sendiri "Stok kain menipis", judul lama "Stok kain di bawah
  minimum" tetap untuk kain yang punya minimum manual; (2) kebutuhan aksesori dari rencana produksi tetap tidak diteruskan ke
  WhatsApp, karena analisis selalu menyatakannya "belum diketahui" (pemakaian aksesori per potong tidak tercatat); gantinya
  "Stok aksesori menipis" dari rumus stok; (3) isian lama kirim dipasang di Master Data dan juga di Gudang, datanya satu.
  Angka manual barang jadi disimpan di tabel CP7 `manual_points`, bukan di `erp.stock_policy_versions` (alasan di desain).
- Tingkat layanan 95% belum diuji ke data penjualan owner (tidak ada di lingkungan uji); diuji sesudah CP7C. Lama produksi
  terukur dimulai dari potong, karena waktu dari keputusan produksi sampai potong tidak tercatat.
- Lama kirim kain dan aksesori tidak tercatat di ERP; selama isiannya kosong, bahan itu tidak punya titik pesan ulang dan
  tidak diingatkan (kecuali kain dengan minimum manual lewat pengingat lama).
- `STOCK_AT_REORDER_POINT` dari README r6 pertama kini dibuat sebagai tiga jenis di atas.
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- KNOWN-P19-DIRECT-LATENCY tetap terbuka (S2, tidak diubah di r6): 100 target dengan angka keuangan sekitar 2,8–3,5 detik di
  browser pada run ketiga auditor dan kualifikasi r5; 300 target di atas 3 detik. 3 detik tidak ditandai tercapai.

`production_go: false`.
