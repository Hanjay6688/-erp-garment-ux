# OW10 — sumber riwayat yang sama untuk ROP (23 Oktober2026 WIB)

`scripts/cp7_reorder_inputs/history.sql` menyiapkan input ROP lewat fungsi
histori dan target Native yang sebenarnya. Tidak mengulang rumus penjualan,
ketersediaan, permintaan, lead, cadangan atau target. Ini helper privat murni;
**belum mengganti compute/pemanggil ROP atau dipasang oleh bundle A**.

Satu tangkapan Native lengkap +query tanggal/pengelompokan tertutup masuk ke
history_prep/events_validate/history_validate. Batas targets/history-cells/
events dan penolakan sumber tetap milik mesin lama. Ketersediaan dan riwayat
diproses per chunk dari batas asli12.500 sel; seluruh baris stok dibaca oleh
history_stock, target disusun baseline_rows yang sama. Tidak membuat job,
menulis ERP, menyaring scope alokasi atau menjalankan analisis keuangan.

Hasil `cp7.reorder-native-inputs.v1` memuat query, waktu dan hash sumber,
produk/identitas, seluruh riwayat, stok kini dan target. Unknown/censored, inverse jurnal,
retur sebagai informasi terpisah dari permintaan bruto, pilihan profil manual
serta nol yang diketahui mengikuti Native. SQL immutable invoker, owner
cp7_capture, search_path kosong/UTC; role luar tidak mempunyai akses.

Enam kelompok awal SQL lokal lulus; pembandingnya **history_build utuh yang lama**,
bukan salinan orkestrasi helper. Seluruh JSON riwayat/stok dan target dari
baseline_rows cocok. Fixture420 produk/12.600 hari memaksa dua chunk dengan
semua produk/hari tetap ada; ini bukan ukuran pabrik atau SLA. Kasus stok90
→0→90 di hari sama menjadi STOCKOUT; perhitungan ROP lama yang hanya melihat
stok awal hari akan menganggap hari itu tersedia. Profil manual, mean0,
retur4/gross10, pembatalan dan perubahan periode/profil juga diperiksa.

Setup pertama berhenti sebelum kasus karena harness ikut memuat reader Native
yang memerlukan tabel run. Kini hanya dua fungsi murni yang diambil lengkap;
kode produk/oracle tidak dilonggarkan. Receipt kecil
`local-reorder-inputs-first-setup-failure.json` tetap disimpan.

## Kompilasi titik dan API privat

`points(native_inputs,defaults,leads,manuals)` sekarang tersedia. Profil Native
yang ditinjau mempertahankan **seluruh target JSON persis**, termasuk pilihan
mean manual/nol, lead dan satu cadangan. Titik ROP mengambil reorder_point_pcs
dari hasil itu. Lead terukur tidak diam-diam mengganti pilihan lead profil.

Produk tanpa profil memakai aturan ROP yang sudah ada (14 hari tersedia,
service90/95/99%, lead terukur dari≥3 grup), dengan **riwayat Native yang sama**
dan kernel target yang sama. Review0 di jalur ini hanya horizon ROP; bukan
asumsi periode tinjau produksi. Full target Native yang belum ditinjau tetap
unknown. Nol yang terbukti tetap0. Identitas/profil yang berubah tidak diam-diam
beralih ke aturan default. Angka lead wajib berasal dari tangkapan server yang
baru; helper murni tidak membuktikan keaslian input caller.

Override manual mengganti titik, bukan menambah cadangan.0 aktif berarti tidak
memicu; null berarti hapus override. Versi/ukuran produk berubah membuat titik
unknown dengan referensi manual lama tetap tersedia. Target produksi tidak
diubah diam-diam untuk mengikuti override; alokasi WIP harus diikat eksplisit.
Pemilih memberi `supply_alignment=NATIVE_TARGET` hanya untuk target profil tanpa
override. Nilai default/manual tidak mendapat klaim keserasian tersebut.

Selection_hash mencakup sumber Native, query, default, seluruh lead/manual dan
versi compiler. Ini identitas pemilihan, **bukan bukti sumber masih segar**;
caller masih wajib mengambil sumber baru, memeriksa hak sebelum/sesudah dan
engine/dependensi sebelum memakai cache. JSON privat tidak boleh disalurkan
mentah ke facade gudang.

API `install_delta/verify/admit_catalog/rollback_preuse` menambah1 schema dan
2 fungsi invoker immutable, tanpa body lama/tabel/kolom/Native DML/RPC/cron.
Sepuluh badan Native yang dipanggil dipin; owner/ACL/body/config baru diperiksa.
A tetap memegang transaksi/envelope/global after-use guard. Helper stateless
tidak menyimpan bisnis; invers menolak sebelum DDL bila masih ada pemanggil
SQL terpasang. Balikkan lapisan caller dahulu sesuai guard/rantai A; tidak
menghapus evaluasi/riwayat agar invers diizinkan.

Bukti kini **11/11 kelompok lokal PASS**, termasuk pemasang aktual/katalog22
apply/admit/inverse/reapply dan penolakan saat caller SQL fixture masih ada.
Ini kontrol dependensi caller, bukan klaim pemakaian Native telah dikualifikasi.
Perubahan yang akan tampak sesudah caller dipasang: hari stok habis di tengah
hari dikeluarkan dari latihan; mean manual dan nol dari profil benar dipakai;
lead profil yang dipilih sama dengan Native. Default lama hanya untuk produk
tanpa profil, dengan labelnya sendiri. Caller hidup **belum berubah**.

Berikutnya: sumber lead terukur/manual dari server dan sambungan compute ROP,
proyeksi WIP yang serasi, label waktu/kandidat serta Native/performa. Pengingat stok bebas harus
tetap tiap menit tanpa menunggu job analisis besar. Parent5/16, OW10 OPEN.
