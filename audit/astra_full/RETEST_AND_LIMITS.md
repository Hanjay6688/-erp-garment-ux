# Perbaikan lama dan batas audit penuh CP7

Kandidat `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`. Ini bagian laporan yang sedang disusun; bukan putusan GO.

| Temuan/acuan lama | Hasil uji Astra pada kandidat ini | Status yang boleh diklaim |
|---|---|---|
| P20 F01: kapasitas v1+v2 menerima61 dari 60 | Transaksi v1 menahan 59; v2 meminta 2 dan menunggu kunci yang sama; sesudah v1 commit, v2 ditolak 40001 `CP7_PLAN_V2_CAPACITY_USED`; total tetap 59 | Perbaikan diretest PASS. Tidak dibebankan ulang ke writer. |
| P20 F02: nama cron lintas database | Dua database pada scheduler yang sama tetap mempunyai job terpisah; empat definisi dijalankan lewat pg_cron nyata di salinan; uninstall tidak memindahkan job database lain | PASS pada kondisi diuji; pemasangan asli tetap belum dilakukan. |
| P20 F03: receipt backup tertimpa | Retry gagal dengan detik sama membuat nama baru; hash dump dan receipt verified sebelumnya tetap;15 dump/restore nyata,14 retensi; malam gagal tidak memangkas | PASS; waktu tabrakan dan urutan malam disimulasikan, operasi dump/restore nyata. |
| P20 F04: detektor metadata dalam copy dilemahkan | Raw `AS20-39_VALIDATION_NEGATIVE` tetap COUNTEREXAMPLE pada4 mutasi semantik setelah immutable trigger sengaja dimatikan; jalur biasa tetap ditolak 55000 | Batas detektor yang sudah didokumentasikan, bukan bug aplikasi baru atau klaim semua korupsi pasti tertangkap. |
| P20 F05: finalizer mock NameError | Shell kandidat menjalankan finalizer aktual dan kontrol pemulihan;1.724 tes dalam 201 berkas, security/build,6 browser selesai | PASS; semua flag dibaca dari signature. Benchmark assembler kondisional cabang tidak berjalan dalam job ini dan tidak diklaim sebagai bukti. |
| SOL-K4-01: heartbeat pertama memblokir tick kedua | Dua tick dingin dengan penghalang pada output; tick kedua selesai tanpa menunggu dan job/unit berbeda; batas timeout serta role diperiksa sendiri | PASS pada probe independen ASF-07, ditambah regresi K4 terpisah. |
| Alat tanggal WIB lama | Kontrol positif mempertahankan log pertama; kontrol gagal aritmetika tak terkait tanggal tetap di-retry dan hasil utama upaya kedua PASS | **ASF-F01 OPEN_TOOLING S3**, temuan baru mandiri; rincian handoff. |
| K4 browser mobile diam pada 2 run writer sebelum kandidat | Dua kegagalan lama tetap tersedia. Kandidat menambah batas waktu dan penanda langkah; rerun auditor 17/17 PASS; desktop TAB_CLOSED dan mobile STOPPED_WATCHING dicatat terpisah | Akar diam lama belum terbukti. Jangan menyebut terselesaikan hanya karena sekali hijau; tidak otomatis dianggap bug produk baru. |
| Diagnostik readiness pada susunan CP6 saja | Dua INCOMPLETE karena RPC CP7 recost memang tidak dipasang; script sama pada susunan CP7 penuh PASS desktop/mobile. Seluruh 31 browser pre-freeze PASS termasuk FREE/WAIVED, extra paket, paginasi dan range | Batas susunan runtime lama; nol kredit kasus untuk diagnostik merah, bukan bug CP7 baru. |
| PR44 timeline | Astra pernah menulis optimasi tersebut. Bukti Sol sebelum putaran dicatat sebagai crosscheck; bukti suite kini tidak diberi label penerimaan independen oleh penulisnya | Penerimaan area ini harus tetap bebas konflik oleh auditor lain; tidak meminta writer mengubah kode yang belum terbukti salah. |

## Batas yang tetap jujur

- Oracle Astra, oracle writer yang dijalankan ulang Astra, review statis, dan dokumen writer dipisahkan. Total ID unik bukan klaim jumlah oracle unik; satu kasus bisa memuat beberapa kontrol.
- Smoke 48 rute pada 2 viewport tidak sama dengan setiap tombol di semua peran. Dua alur tulis jual–retur menguji Grade A/Grade B, respons hilang sesudah commit, replay, dan pembalikan; browser lain diperluas lewat suite writer yang dieksekusi auditor.
- Chromium dengan ukuran layar/zone HP adalah emulasi, bukan HP fisik/Safari. Screenshot nyata diperiksa dan hash disimpan; PR45 tidak masuk kandidat.
- Helper privat diperiksa lewat inventaris ACL lengkap, panggilan SQL nyata yang dipilih, dan Auth/REST nyata. Tidak diklaim setiap fungsi diulang lewat setiap peran HTTP.
- Model/matching kernel dilabeli kernel. Tidak mengubah suatu counterexample privat menjadi klaim stok produksi salah.
- Angka 5.000 berasal dari semua target/halaman nyata dan proses server; waktu satu tick bukan waktu layar keseluruhan. `pg_column_size` bukan bukti ruang disk langsung kembali ke OS setelah DELETE.
- Scheduler dan backup hanya dipasang di database sekali pakai. Tujuan backup operasional, konfigurasi nyata, WA/penyedia AI nyata, hosted install dan production GO tidak diuji/diberi izin oleh audit ini.
- Gladi P21 bukan pemasangan. Restore backup pra-pasang memang membuang transaksi setelah titik backup; jangan menjanjikan pemulihan tanpa kehilangan data. Restore database tidak menghapus role tingkat cluster; gladi mencatat 38 role masih ada.
- CP6 sudah tertutup sesuai cakupan; regresi lama yang superseded oleh UI terhubung tidak membuka kebijakan owner lagi. Audit seluruh CP1–7 adalah tahap terpisah.
