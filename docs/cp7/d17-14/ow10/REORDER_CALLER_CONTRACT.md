# OW10 — satu pemanggil rencana dan pengingat stok (23 Oktober2026 WIB)

**Server/klien lengkap; Native19 PASS pada d5997235**, treee9fdbe91,
run39924999687/job120319097974. Seluruh19 ID/status dicocokkan dengan Original.
Receipt dan batas: [d599723-native19-pass.json](d599723-native19-pass.json).
Ini kualifikasi komponen penulis; pemasangan/pemulihan caller serta rantai A
dan audit independen tetap terbuka.
`cp7_reorder_caller_stage` v1 mengganti pemanggil ROP saat tahap ini dipasang.
Basis Native133 c0bb0d19 tetap PASS sebagai producer/reader; run itu **tidak**
memasang inputs/cache/caller di dokumen ini. Parent tetap5/16, bukan CP7C go.

## Perilaku yang sudah dibuat

- `compute` memakai satu snapshot server untuk sumber riwayat/aturan/stok serta
  sumber analisis operasional bila ada hasil global DONE yang masih disimpan.
  `cp7_reorder_reader.snapshot` menggunakan cache aturan tetapi membaca ulang
  stok dan reservasi. Tiga waktu dipisahkan: aturan, stok, dan analisis.
- Titik pesan ulang dan target memakai kernel Native yang sama. Titik untuk
  horizon L; jumlah produksi untuk L+R. Profil yang ditinjau dipakai persis,
  termasuk permintaan manual di profil. Default lama digunakan hanya pada
  keadaan tanpa profil yang dibolehkan kontrak inputs. Tampilan rata-rata
  menunjukkan input target sebenarnya, bukan rata-rata histori yang berbeda.
- WIP yang boleh mengurangi peringatan hanyalah barang baik terarah/tiba tepat
  waktu dari satu alokasi global. Query, hash sumber, ukuran, target, stok dan
  kedua tenggat diperiksa. WIP mentah per-model tidak dipakai. Kandidat tetap
  bersyarat; 7pcs yang dibagi3+4 tidak menjadi7pcs untuk setiap produk.
- Ketika analisis belum ada/gagal/lama/tidak lengkap, jumlah WIP dan posisi
  proyeksi null, bukan0. Peringatan tetap membandingkan stok bebas. Tick kecil
  tidak meminta atau menjalankan analisis besar dan tidak memanggil modul uang.
- Saat lock sibuk, pengingat memeriksa stok baru untuk **seluruh** barang,
  termasuk barang yang baru menipis, tanpa mengkreditkan WIP lama. Bila aturan/
  daftar barang berubah, sumber ditolak dan collector tidak menganggap daftar
  kosong sebagai bukti semua peringatan selesai. Evaluasi lama tidak diubah.
- Angka manual mengganti titik pemicu saja. Manual25 boleh lebih besar dari
  target5; posisi4 tetap dibandingkan dengan25, jumlah produksi dasar tetap1.
  UUID/revisi/riwayat append-only dipertahankan. Versi/ukuran berubah membuat
  angka manual lama menjadi referensi yang tidak aktif. Konflik ukuran dengan
  transaksi lama tetap ditolak oleh validator Native.
- Hak diperiksa sebelum/sesudah menunggu lock dan sesudah compute. Jawaban ulang
  UUID juga memeriksa hak lagi sebelum dikembalikan. Perubahan hak membatalkan
  seluruh penulisan dalam transaksi. Ini baru dibuktikan dengan adapter akses
  lokal; dua pengguna sungguhan masih harus diuji.
- PCS v2 berupa teks bulat persis, termasuk di atas batas aman JS. Klien v1
  tetap tertutup dan kompatibel. Pengingat/WA menyebut perkiraan tepat waktu;
  label barang yang panjang boleh dipotong, seluruh angka dipertahankan.
  Jam tick tidak dimasukkan ke detail/hash peringatan, sehingga fakta yang sama
  tidak membuat antrean WA baru tiap menit.

## Komposisi dan kepemilikan A

Urutan atas produksi18/target4/suplai/pemicu awal yang sudah diverifikasi:
`cp7_reorder_inputs` → `cp7_reorder_reader_stage` → `cp7_reorder_caller_stage`.
A memegang transaksi, envelope lock, default installer, tipe generator,
registry, penggabungan dan backup/restore. B tidak mengubah semuanya itu.

API caller: `install_delta/verify/admit_catalog/rollback_preuse`. Satu schema,
dua fungsi privat, dua tabel privat RLS, delapan badan hook yang sudah ada,
tanpa endpoint publik atau DML ERP baru. Hook mempertahankan pemilik, ACL,
konfigurasi dan metadata asal. Pin sumber/Native dependency tepat di MANIFEST.

Hook: `compute`, `workspace`, `fg_source`, `alert_row`, `save_manual`,
`save_settings`, `refresh`, dan `cp7_alert_native.item_line`. Bahan/aksesori
tetap memakai mesin lama; format kewajiban uang dalam item_line dipertahankan.
Evaluasi FG baru berada di schema caller; tabel evaluasi/WIP model lama tidak
dibaca sebagai sumber proyeksi dan tidak dikosongkan saat pemasangan.

Keempat RPC publik lama tetap namanya. Bentuk baca menjadi `cp7.fg-reorder.v2`,
baris `cp7.fg-reorder-row.v2`, hasil manual `cp7.fg-reorder-manual.v2`, detail
pengingat `cp7.fg-reorder-detail.v2`. Klien dalam checkpoint ini menerima kedua
versi dengan parser tertutup. Refresh/settings mempertahankan bentuk v1.

Invers sebelum pakai memulihkan22 kelompok katalog tepat. Setelah `compute`
menulis evaluasi/use_marks, invers menolak sebelum DDL. Use marker immutable;
tidak boleh dihapus untuk memaksa invers. Balik urutan caller → cache → inputs
hanya sebelum pemakaian; setelah dipakai melalui backup/restore yang diuji A.

## Bukti saat checkpoint

| Pemeriksaan | Hasil dan batas |
|---|---|
| Inputs/history/cache/evaluate |35/35 SQL lokal; Native kernel/history aktual, ERP/identitas terkontrol;2000 produk/202000 pergerakan/60000 hari utuh. |
| Alur caller dan RPC SQL aktual |9/9; empat API installer22, invers/reapply, guard setelah pakai, manual/replay/clear, revokasi terkontrol, settings, busy/fresh stock, Native reader/projection, successor dan konflik ukuran. |
| Reader suplai setelah fixture dibagi |9/9; K3/read-only/ACL/hash/retensi dan API22 tetap lulus. |
| Klien/DOM |65/65 di4 berkas:51 kontrol lama +14 tambahan; fixture v2 diambil dari SQL aktual atas data sintetis. |
| TypeScript |PASS. |
| Clash PL/pgSQL |7 badan PL/pgSQL PASS; fungsi SQL bahasa lain tidak dihitung sebagai PL/pgSQL. |
| Sembilan SQL beku |Owning gate PASS, e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127. |
| Source registry bersama |Masih gagal tepat7 pasangan lama Mandor/OW16/pemicu awal; tidak ada RPC baru. Patch milik A tetap di ow13a/SHARED_INTEGRATION.patch. |

Receipt kecil: `local-reorder-caller.json`, `local-reorder-inputs.json`,
`local-supply-reader.json`, `local-reorder-caller-client.json`. Original/log
lengkap dan kegagalan pertama disimpan terpisah. Tidak ada data produksi/WA asli.

Kegagalan pertama klien61/63: parser baru salah mewajibkan buffer DAYS bernilai
ketika profil sudah tidak berlaku. Server benar memberikan UNKNOWN dengan
buffer null. Parser dibetulkan: rumus yang diketahui tetap wajib mempunyai
input lengkap; profil unknown tetap ditampilkan unknown. Oracle tidak diubah.
Kesalahan fixture awal (schema ganda, enum DIRECTED salah, helper sumber tidak
terekspor, hoisted satu deklarasi, setup timestamp) juga dicatat terpisah.

## Yang harus dibuktikan selanjutnya

1. Native19 sudah membuktikan Auth/PostgREST, dua pengguna/revokasi setelah
   menunggu, UUID, stok baru saat lock sibuk, browser komputer/HP dan invers22.
   Pemasangan/pemulihan caller setelah digunakan dan seluruh rantai A masih
   harus diuji oleh integrator; gerbang restore paket dasar bukan bukti itu.
2. Angka/oracle lama yang memang berubah dipetakan secara eksplisit. Kontrol
   lama tetap dijalankan pada pendahulunya; pengganti mengikuti Native penuh:
   `SS1_OUT_OF_STOCK_DAYS_NOT_ZERO_DEMAND` memakai availability intrahari;
   `SS1_LEAD_TIME_MEASURED_FROM_PRODUCTION` mendahulukan profil ditinjau;
   `SS1_FORMULA_FROM_POSTED_SALES` menghormati mean yang dipilih di profil;
   `SS1_IN_PRODUCTION_COUNTS_TOWARD_POSITION` menerima good/ETA global saja;
   manual/save/access/WA dan volume menggunakan kontrak v2. Jangan menyalin
   angka expected lama ke rumus baru atau meloloskan raw WIP agar kontrol hijau.
3. Volume2000 Native:5622ms dingin,2899/2845ms hangat pada202000 pergerakan,
   batas statement8detik dan hangat3detik tetap. Itu satu fixture sintetis,
   bukan janji waktu umum. PGlite cache terdahulu bukan bukti SLA Native.
   Produk sintetis yang mewakili
   riwayat harus memiliki established_at yang sesuai; jangan mengubah riwayat
   produk nyata agar dianggap tersedia. Factory3600 sebelum/sesudah tetap OW12b.
4. Jadwal pengingat tiap menit/pemicu awal/K4 tanpa ketergantungan WA dipasang
   A; tick alat uji tidak membuktikan cron aktif. Callback Master/registry/
   generator nullable pemicu awal tetap permintaan A sebelumnya.
5. OW11a/b, OW12b dan OW13c tetap berjalan sesuai pembagian. Fallback bukan
   alasan menyebut model kompleks atau saran produk baru sudah selesai.
