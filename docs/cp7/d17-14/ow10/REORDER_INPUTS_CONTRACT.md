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
seluruh riwayat, stok kini dan target. Unknown/censored, inverse jurnal,
retur sebagai informasi terpisah dari permintaan bruto, pilihan profil manual
serta nol yang diketahui mengikuti Native. SQL immutable invoker, owner
cp7_capture, search_path kosong/UTC; role luar tidak mempunyai akses.

Enam kelompok SQL lokal lulus; pembandingnya **history_build utuh yang lama**,
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

Berikutnya: kompilasi titik ROP dari input ini, sumber lead terukur/profil dan
aturan default yang sama; caller dan proyeksi WIP yang serasi; label waktu dan
kandidat; API invers/katalog serta Native/performa. Pengingat stok bebas harus
tetap tiap menit tanpa menunggu job analisis besar. Parent5/16, OW10 OPEN.
