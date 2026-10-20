# Cakupan OW04 yang belum diterima oleh checkpoint browser4

Ini daftar batas bukti dari sumber, bukan keputusan bisnis baru atau klaim
implementasi berikutnya telah selesai. Dasar: ledger-proposal/README.md
bagian Accepted attribution constraints; coordinator/02_initial_projection.sql
dan06_finish_and_closed_routes.sql; NATIVE_EMPTY_INTEGRATION.md;
BROWSER_EXPECTED.json. Tiga item backlog lain sudah selesai; OW04 tetap terbuka.

- Browser4 saat ini hanya mencakup settlement awal dengan hak kredit positif.
  Retur biasa tanpa kredit sudah punya bukti Native EMPTY, tetapi belum bukti
  parent UI nyata yang baru. K=0 dengan komponen bertanda pada tanggal berbeda
  tetap berbeda dari target kosong seluruhnya; tidak boleh diubah menjadi
  retur biasa atau dianggap tidak memiliki pengakuan historis.
- Proyeksi HPP awal saat ini mensyaratkan biaya per pcs tepat dalam sen:
  coordinator/02_initial_projection.sql:75–79 dan103 menolak pecahan sen,
  dan memeriksa target penuh terhadap buku sebelum menerima proyeksi/quote.
  Browser4 memakai HPP10,00 per pcs; itu belum membuktikan biaya pecahan,
  beberapa lot/PO atau penyesuaian HPP susulan. Perlu proyeksi selisih target
  kumulatif Native yang tepat, tanpa membulatkan biaya per pcs agar lolos.
  Penolakan tertutup tersebut menjaga data, tetapi belum melengkapi fitur.
- Semua keluarga retur memiliki ordinal tetap. Koreksi/pembayaran berikutnya
  wajib menghitung ulang T_i setiap keluarga yang terpengaruh dan mem-posting
  target minus seluruh I aktual yang dipertahankan per pasangan tanggal.
  ΔF seluruh invoice tidak boleh ditaruh ke satu cohort atau dikurangi hanya
  dari K awal. Source lineage, account/mode, journal dan consumer harus terikat.
- Keluarga yang sebelumnya EMPTY dapat pertama kali membutuhkan pengakuan
  karena mutasi berikutnya. Pilihan akun/mode harus eksplisit pada saat itu,
  tanpa default baru; kenaikan berikutnya membutuhkan review segar dan tidak
  mengulang cash-out REFUND awal secara otomatis.
- Kredit masuk APPLY, konsumsi refund lanjutan, pembatalan consumer serta
  koreksi gabungan harus mempertahankan pendanaan pada kedua sumbu tanggal,
  mengunci seluruh sumber/cohort/target yang terkait dan selesai atomik.
  Menolak jalur tersebut secara tertutup menjaga data, belum memenuhi fitur.
- Note correction lama memutar ulang retur sebelum pembayaran salinan.
  Penggabungan baru harus membawa sumber settlement yang terikat atau
  mengubah urutan yang sah; tidak boleh membuat kredit nol palsu lalu
  kelebihan bayar, kehilangan buku sumber, atau menggandakan refund.
- Pesan/pembaca dependensi harus memberi dokumen dan langkah membalik yang
  bisa dipakai. Menampilkan kode unsupported saja belum memenuhi syarat
  owner. Parent UI, pembaca E dan seluruh backend harus dikomposisikan pada
  installer yang sama sebelum frontend produk diaktifkan.

Bukti Native44 ef98, HTTP8/race6 dan browser4 tetap memiliki kandidat dan
cakupan masing-masing. Tidak ada penerimaan penuh ERP/kecepatan pabrik,
audit independen atau izin produksi yang disimpulkan dari daftar ini.
