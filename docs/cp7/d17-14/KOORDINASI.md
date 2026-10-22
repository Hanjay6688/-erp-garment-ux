# Koordinasi dua penulis — D17-16, 22 Oktober 2026 WIB

Rencana utama: [PEMBAGIAN_DUA_PENULIS_20261022.md versi2](../PEMBAGIAN_DUA_PENULIS_20261022.md).
Salinan di cabang produksi sama persis dengan blob `696626126b7a438b1394cb2a701ec0c64c4e18d4`
dari `claude/new-session-deapao` commit `349a3b30580394f66b29637fcba51ff644e36959`.
Catatan ini menangani penerimaan dan titik temu, bukan membuat pembagian ketiga.

## B/20261022-01 — penerimaan scope oleh Penulis B

**Disiapkan, belum menambah fitur selesai.** Codex di sesi ini adalah Penulis B yang disebut Astra dalam rencana.
Tidak ada pesan yang dikirim ke sesi Claude dan belum ada pengakuan mulai dari Penulis A yang diamati di sini.

| Pemilik | Scope | Cabang |
|---|---|---|
| A/Claude, integrator | OW06, OW07, OW08a/b, OW09, OW12a, OW15 dan pembaca/penulis uang/stok/HPP/laporan | `claude/d17-14-uang` sesuai rencana; dibuat/dijalankan oleh Claude |
| B/Codex/Astra | OW16, OW10, OW11a/b, OW12b, OW13a/b/c, OW14a/b bagian tampilan/aturan | `astra/d17-14-produksi`, sudah dibuat |

Cabang B dimulai pada `a255e48f76ce502d9e571f2bfdd8a52a1a2b1306`, kepala integrasi saat persiapan.
Perbedaannya terhadap titik produk `01c5f8565cdae2ed36acb71fcf8a62154a4dda74` hanya empat berkas dokumen;
kode dan seluruh bukti OW05/OW06 sama. Ini mempertahankan catatan persiapan yang lebih baru tanpa mundur produk.
Cabang sumber dokumen Claude tidak dijadikan dasar produk karena riwayatnya lebih tua; hanya rencana/D17-16 yang diambil.

Cabang lama `claude/ow06-supplier-transfer` dan `codex/ow07-hpp-close` tidak diteruskan untuk pembagian ini.
Tidak dihapus atau ditulis ulang. B tidak menggabung ke integrasi dan tidak mengambil OW07 lagi.
Status keseluruhan tetap5/16; OW06 belum selesai; laporan kredit masih BLOCKED. Persiapan ini bukan production_go.

## B/20261022-02 — titik temu dan batas penulisan

- Gunakan kepemilikan di bagian3 rencana. Satu berkas hanya diedit satu penulis pada suatu waktu, termasuk bila
  bagiannya berbeda. Pekerjaan OW09 pada layar yang juga diperlukan B harus dicatat sebelum mulai, lalu pemilik lain
  menunggu berkas itu dilepas atau meminta pemilik menerapkan sambungannya. Nomor baris tidak menjadi batas kepemilikan.
- B tidak mengubah pemasang, `scripts/cp7_*bundle*.py`, Native `supabase/**`, tipe database generator, modul angka
  keuangan A, `planning/report-staged.sql`, atau patch SQL milik uang/HPP. B menuliskan permintaan berkas/fungsi,
  alasan, bentuk perubahan, sumber awal dan bukti yang perlu dijalankan di catatan ini. A/pemilik yang menerapkannya.
- Berkas sumber dan semua fungsi SQL yang diturunkannya diperiksa bersama. Dua berkas Python berbeda tidak boleh
  membuat dua pengganti atas fungsi SQL yang sama. Perubahan kontrak API, tanggal, hak, source pin atau urutan lock
  dicatat sebelum pemanggil memakai perubahan itu; oracle uang/stock/HPP dan ACL tidak dilonggarkan.
- `src/Native*Analysis*` dan `src/NativeStaged*` adalah scope B, kecuali panel laporan bertahap/keuangan yang dipegang A.
  Nama berkas panel bersama harus ditetapkan dahulu; wildcard tidak memberi dua penulis hak pada berkas yang sama.
- A menulis kontrak modul OW12a di sini (input, status kelengkapan, angka resmi, tanggal/snapshot, hak dan penolakan).
  B baru memasang panggilannya setelah kontrak tersedia. B tidak menghitung laba/HPP alternatif dan tidak membolehkan
  kesimpulan biaya/laba ketika bagian keuangan belum lengkap. Bagian B lainnya tidak perlu menunggu OW12a.
- OW14b: B membuat referensi konfigurasi lama dan penjelasan aturan aktif; A menambah pemeriksaan daftar pemasangan.
  Membaca/migrasi data Enteng nyata tetap belum diotorisasi dalam sesi ini; tidak ada penulisan produksi/hosted/WA.

## Langkah B selanjutnya

Mulai OW16 dengan memetakan kejadian potong fisik, status proses, kelompok bahan+pola+rentang ukuran dan riwayat
seluruh pabrik. Pisahkan apa yang sudah terbukti dari apa yang masih perlu dibuat. Nilai batas/minimal riwayat belum
diisi penulis; ajukan hanya ketika benar-benar diperlukan, sambil mengerjakan sambungan yang tidak bergantung nilainya.
Sesudah itu urutan B mengikuti ketergantungan mesin target, evaluasi metode, otomatisasi, saran potong dan gudang.
Semua fitur tetap lingkup; fallback/tampilan saja tidak menutup butir yang belum selesai.

Setiap checkpoint mencatat dasar/kandidat, berkas/fungsi berubah, bukti, kegagalan pertama, batas dan langkah berikutnya.
Uji silang memakai commit yang pasti dan tempat kerja/database uji terpisah. Log besar dan konteks personal tetap privat.
Jadwal17.00 WIB dan estimasi7–8 hari berasal dari rencana A; belum ada otomatisasi penggabungan atau janji durasi
yang dibuktikan oleh sesi ini. Hanya A yang menggabung dan memperbarui paket auditor dari hasil gabungan yang diuji.

## B/20261023-03 — implementasi OW13b dan OW16; sambungan yang diperlukan A

B sudah menulis kode, bukan hanya persiapan. OW13b menghapus batas201 kandidat pada history_source sambil mempertahankan
batch50, proof Native/current-facts, pembanding per model dan Wilson tepat. Bukti lokal BEFORE/AFTER di ow13b; kualifikasi
Native20 pertama19 PASS/1 INCOMPLETE akibat SKU fixture terlalu panjang, diperbaiki hanya nama contoh. Run berikutnya
0 kasus akibat pembatasan unduh image; kegagalan asli tetap disimpan. Pengerjaan berlanjut, belum klaim OW13b selesai.

OW16 sumber `scripts/cp7-src/cutting-yield/automatic-status.sql`, layar `src/NativeCuttingStatusPanel.tsx`, kontrak
`src/nativeCuttingStatus.ts`, tersambung dari `ConnectedCuttingPage`. Tidak mengubah folder uang/HPP atau pemasang A.
11 uji SQL lokal dan34 unit/DOM lulus; rincian/batas di ow16/README. Belum merupakan bukti Native/HTTP/browser/restore.

Permintaan untuk A selaku integrator:

1. Tambahkan sumber automatic-status.sql setelah planning/cutting-yield dan principal cp7_capture/cp7_policy tersedia.
   Ajarkan pemilik pemasangan/rollback/pemulihan/katalog22 tentang schema cp7_cutting_status, dua tabel, empat trigger,
   tujuh fungsi privat dan tiga wrapper publik. Jangan menurunkan standar pemeriksa lama.
2. Daftarkan tiga wrapper status dalam sensus route/capability sesuai pemeriksaan server dan kontrak yang tertutup;
   salin tiga tipe Args/Returns dari addon typed di nativeCuttingStatus.ts bila disatukan ke preconnect bersama.
3. `scripts/check-source-ownership.mjs` milik integrasi: tambahkan tepat tiga pasangan file/RPC baru. Baseline sendiri
   juga sudah merah untuk tiga RPC MandorCorrection (diverifikasi pada checkout sebelum OW16). Usulan enam entri tepat
   di ow16/SHARED_INTEGRATION.patch; A menerapkan setelah membandingkan sumber, tanpa menghapus pemeriksaan.
4. Delegasi metadata yang dinyatakan SQL: SELECT policy hanya cp7_capture; helper fields/utc hanya cp7_policy;
   pembaca metadata Native material_name dan size.sort_order. Tidak ada grant writer ERP. Semua ACL/schema/tipe baru
   perlu masuk komposisi dan bukti pasang/pulih gabungan. Versi usulan baru tidak mengubah Native writer/history.

Permintaan ini tidak menghalangi B menguji tahap OW16 secara terpisah dan mengerjakan bagian produksi/perencanaan lain.
Tidak ada keputusan owner baru tentang angka cakupan/minimum atau umur koreksi. Default fitur tidak diaktifkan lewat
fallback atau angka fixture. Butir selesai keseluruhan tetap5/16 sampai kebutuhan dan alurnya benar-benar terbukti.

## B/20261023-04 — hasil kualifikasi dan kontrak target privat

OW13b20/20 pada efe71123407312f562ef91068f60b11ef4243f76/run39824155178/job119982870102.
OW16 sekarang16/16 pada3f0e545/run39832859589/job120013305810: Native10, dua pengguna2, HTTP2, browser2;
restore/advisor lulus. Kegagalan boot sebelumnya0 kasus tetap disimpan. Sumber SQL45cf0b428fbe6b85d7e18367492ef188e7ac49d06f120e39156b66e9cf758d4f.
Sambungan pemasang/registry A pada bagian03 masih diperlukan; owner belum mengisi nilai produksi melalui form.

OW14a pada245b595/run39830370397/job120004613284 lulus99/99: Native55, dua pengguna30, HTTP5, browser9,
restore/advisor lulus. Desktop/HP memeriksa sumber/angka kain sama di Ringkasan Gudang, tanpa tombol konfigurasi.
Ini tidak menutup OW14b atau mengaktifkan pengiriman WA nyata. Receipt/hash Original di folder masing-masing.

Kontrak privat OW10 dicatat sebelum kualifikasi server: helper yang sama `cp7_baseline.target(jsonb)`, input
`cp7.target-input.v2`: contract_version/snapshot_id/scope_id/mode/daily_total_pcs/counted_days/daily_sd/lead_days/
review_days/buffer_days/service_level/refs. DAYS meminta daily_sd/service_level=null; STATISTICAL meminta buffer_days=null.
Output reorder_point_pcs/target_pcs dan rincian demand/cadangan. Kontrak v1/arsip tetap dibaca; endpoint publik,
UUID/periksa hak/lock penulis tidak berubah. Semua angka tetap string tepat, unknown bukan0 dan tidak ada dua cadangan.
Pemanggil: planning/baseline-source.sql, planning/analysis-stages.sql, stock-formula/formula.sql. Target memakai rasio
utuh; hash baseline dan planning/supply-source.sql diberi stempel target-unified-2. Tidak ada fungsi/role/table/grant baru;
kernel tetap22, tidak perlu penambahan daftar sumber bundle. Panel target membaca v1/v2. B tidak mengubah pemasang A.

OW10 belum selesai: konsistensi aturan permintaan, kapan mulai dengan suplai tepat waktu, alokasi WIP/rencana ke varian
masih terbuka.162 pembanding independen/129 jawaban lama/49 uji klien lokal lulus; Native38/analisis bertahap15 dan
stock formula99 pada commit baru belum boleh diasumsikan lulus. Modul angka/laporan A, uang/HPP dan Enteng tidak diubah.
