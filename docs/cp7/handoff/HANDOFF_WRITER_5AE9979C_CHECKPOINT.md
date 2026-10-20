# Handoff writer — checkpoint Native, waktu retur dan skala

**INTERNAL_WRITER_CHECKPOINT, bukan audit independen atau izin produksi.**
Cabang `astra/d17-14-20261020`. Scope16 butir tetap mengikuti
`OPEN_WORK_D17_14_20261020.md`, D17-14 dan tambahan Claude D17-15/OW-16.
Writer utama satu-satunya integrator; putaran ini memakai empat pembantu
GPT-6.1 Sol Max untuk menelusuri sumber, menguji dan menantang, tanpa edit
produk atau anak agen.

## Kandidat dan ruang perubahan

| Identitas | Nilai |
|---|---|
| Produk terbaru yang dikualifikasi P11 | `4e3c98b3ce04427c65c7bc7c1b21ec3bdacfea71` |
| Tree4e | `29db6ac1b6fd80de2e1480930eeaae36713be621` |
| Alat E01 dan checkpoint bukti | `5ae9979cb60f18b6db47524441f6ac6f7787d8e6` |
| Tree5ae | `4050507bfadf0cdd6d57dd4747ab1ef71d92be1d` |
| Produk sebelumnya OW-02/03 | `2ad56e147a180c3fb2c433aed53cadb6a421f434` |
| Penguatan perjalanan input profil | `878e0a9cad779db42826d7cb1fb97d978d498b73` |
| Kandidat auditor yang tetap beku | `55c885d1a12336905e433e05852b99be4d933f74` |

Produk5ae byte-identik4e (`git diff --name-only 4e3c98b3 5ae9979c -- src supabase` kosong).
Produk4e menambah perbaikan UI waktu retur baru menjadi kosong, bukan waktu
buka halaman. Native SQL/rumus uang tidak berubah dari2ad; DOM pendamping
ada di src.5ae menambah langkah waktu eksplisit pada alat browser E01 dan
cabang trigger workflow saja, lalu menyimpan bukti/keterbatasan.
Dokumen sesudah5ae dan reproducer Decimal bukan perubahan produk.

Commit lokal62e9c0d9 dan GitHub5ae mempunyai tree yang sama4050507b;
publikasi memakai perbandingan tree dan ref ber-lease, tanpa force.

## Pekerjaan dan syarat selesai yang terbukti

| Cakupan | Bukti dan batas |
|---|---|
| OW-02 pada aplikasi | K4 32/32 pada2ad. Desktop/HP menutup tiga tab, server melanjutkan, buka ulang hasil sama tanpa duplikasi. Hosted/operasional CP7C tetap HOLD. |
| OW-03 isian→analisis | Profil38, staged15, F05154 pada2ad; penguatan F05154 pada878 membuktikan ketik12→profil yang sama→gap93/saran96/tambahan3, bahan186 tetap, clearUNKNOWN dan arsip utuh. Bukan kelulusan SLA/skala seluruh ERP. |
| OW-01 sebagian | WA65 pada2ad dengan server palsu. Kebutuhan aksesori rencana belum tersambung; otorisasi D17-14 sudah ada. |
| OW-04 pendahuluan waktu | P11 64/64 pada4e dan E01 4/4 pada alat5ae/produk4e. Input retur kosong, wajib waktu eksplisit, perubahan waktu membatalkan review, readback instant tepat. Settlement CREDIT/REFUND belum tersedia. |

Seluruh receipt per kasus, kegagalan awal dan hasil perbandingan tersimpan
di `docs/cp7/d17-14/`; indeks mesin `CHECKPOINT_2AD56E14.json` tetap memberi
label kandidat asli, bukan mengganti bukti lama menjadi bukti produk baru.

## Runtime baru yang ditutup pada checkpoint ini

| Suite | Pin/run/job | Hasil |
|---|---|---|
| P11 |4e /39430283909 /118653236629 attempt1 |64/64, restore/advisor PASS; SQLhash722aca08… |
| E01 produksi→kas→retur→laporan |5ae /39433112026 /118663009654 attempt1 |4/4 sekali jalan: Native1/HTTP1/browser2, restore/advisor PASS; SQLhasha7305cfc… |
| K6 ulang tunggal |2ad /39420750772 /118654098080 attempt2 |10/10, restore/advisor PASS; hashb4adfb3a… |
| Skala |2ad /39420750772 /118620792724 attempt1 |5/5 kontrak pengukuran, restore/advisor PASS; hash3c0364ce…; bukan SLA |

E01 tetap menghasilkan FG45/nilai675, kas200, AR175, pendapatan375,
COGS225, laba kotor150 pada desktop/HP. Replay balasan hilang dengan UUID/
payload sama, pagar tab kedua, nol penulis di tab kedua dan laporan baca-saja
tetap diperiksa. Ini belum retur lunas: sebelum retur masih AR300.

Reproduksi Native menggunakan persis workflow `.github/workflows/`
`cp7-p11-sales.yml` pada4e dan `cp7-f03-e01.yml` pada5ae, termasuk pin
writer/candidate/AB/harness/Supabase/Postgres. UI dibangun dari checkout
auditor pada commit workflow; pin candidate Native bukan sumber build UI.
Jangan mengarahkannya ke hosted/Enteng. Hash bundle lokal yang dihitung
ulang cocok SQL terpasang pada kedua suite; perintah/proof identity ada di
receipt `ow04/CI_39430283909_PHYSICAL_TIME.json` dan `CI_39433112026_E01.json`.

## Kegagalan pertama dan perubahan alat

- UI waktu baru pada produk lama:1/10 gagal karena prefill jam halaman;
  sesudah perbaikan32/32 tiga formulir DOM lulus. Log awal tetap ow04.
- E01 pemakai kedua: diagnosis sumber menemukan ketergantungan default;
  tidak diklaim ada kegagalan Native E01 sebelumnya. Delapan assertion/
  langkah baru mengisi waktu, angka expected dan semua assertion lama tetap.
- K6 awal gagal **sebelum kasus**: port database bentrok dan registry menolak
  unduhan. Receipt lingkungan tetap ada. Ulang hanya job itu pada kode sama,
  sesudah workflow skala selesai; sukses job lain attempt2 adalah reuse.
- K4 lama28PASS/4INCOMPLETE tetap disimpan: clock baca dibanding salah dan
  fixture mencoba mencabut OWNER terakhir. Perbaikan alat mempertahankan
  seluruh fakta/hash/izin; ulang2ad32/32 sudah terikat receipt.
- Model tanggal: penjelasan awal menyamakan dua varian buka ulang900+100
  dan1000. Counter-review memisahkannya; expected model tidak diubah.

## Hasil counter-review dan pekerjaan berikutnya

Rancangan retur lunas satu jumlah/satu tanggal ditolak berdasarkan jurnal
sumber: pembayaran setelah retur membuat kredit muncul terlalu awal.
Pembukaan ulang periode juga dapat membutuhkan ekonomi19/buku20, yang
poster biasa tidak dapat wakili. Counter aritmetika5 contoh dapat diulang
dengan `python docs/cp7/d17-14/ow04/temporal_counter_model.py`; hasil dan
hash terikat receipt. Ini bukan Native atau algoritme penerbitan. Varian
buka ulang900+100 tambahan masih source-only. Detail:
`ow04/TEMPORAL_COUNTER_20261020.md` dan `SETTLEMENT_SOURCE_MAP.md`.

Masih perlu implementasi kredit bertanggal, akun dan jurnal terikat sumber,
seluruh pembaca/detektor/koreksi/inverse, izin/race/replay/rollback serta
browser retur setelah lunas. Jangan menghapus guard lama, membuat batch
saldo awal palsu atau mengubah pembayaran asli. Tidak perlu keputusan owner
baru untuk memecahkan masalah rekayasa tanggal ini.

OW-01 berikutnya memerlukan live recheck dan forwarding DATA_REVIEW untuk
kebutuhan aksesori. Gross186 bukan tambahan pembelian186: pemasangan/sisa
alokasi belum terbukti. Source map, urutan kunci dan usulan golden yang
belum dijalankan: `ow01/ACCESSORY_NEED_NEXT_SCOPE.md`.

Skala5000 memerlukan79,40/88,22/105,27detik sampai server selesai dan halaman
hasil pertama terlihat pada riwayat1/30/100hari, dengan keuangan DEFERRED.
Seluruh26halaman diverifikasi;25perpindahan berikutnya diukur terpisah.
Buka ulang1,261–1,568detik belum memenuhi owner1detik. Keuangan langsung5000
timeout8detik. OW-12, keuangan/HPP/pembanding3600–5000 serta kecepatan tetap
terbuka; PASS pengukuran/penolakan jujur bukan hasil lengkap.

Semua butir lain tetap mengikuti register, termasuk OW-16 sebelum OW-15.
Kegagalan CP6 historis tidak baru diuji atau dinyatakan hijau di sini.
Paket eksternal baru belum siap karena OW-01 masih terbuka. Perselisihan
rancangan satu tanggal telah diselesaikan lewat sumber; implementasi dan
pembuktiannya tetap belum selesai. Tidak ada merge main, deploy, hosted,
Drive atau WA nyata; `feature_complete:false`, `audit_complete:false`,
`production_go:false`.
