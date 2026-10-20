# Disposisi hasil pertama99kasus

Kandidat b040bc6492d2184efad0b9a06c1dd4e2a10b9053, run39458882424/job118752813669:97PASS/2INCOMPLETE, restore dan advisor gate true. Seluruh86kasus lama lulus;11dari13jenis tambahan mendapat actual fake-provider receipt. Log pertama utuh dan kedua traceback dipertahankan; ini bukan wholePASS.

1. **Cacat produk pesan laundry.** Label Native98karakter ditambah suffix40karakter menjadi138, tetapi item_line memotong seluruhnya ke120. Hasil nyata berakhir `nilai belum diketahu`. Perbaikan melindungi seluruh nilai/UNKNOWN dan review/jatuh tempo. Label tetap lengkap bila muat256; hanya label yang dipendekkan dengan elipsis bila perlu. Batas body1000, footer dan hitungan baris yang tidak tampil tetap. Fixture, detail/ID/hash sumber, serta assertion body lengkap pada13kasus tidak diubah. Actual SQL formatter lama4/10 versus baru10/10 pada expected yang sama; root mengulang10/10. Ini PGlite terisolasi, bukan provider/Native baru.

2. **Cacat alat reassembly.** layout.prefix adalah indeks sisip, bukan panjang seluruh array header. Server mempertahankan suffix asumsi kain; helper Python keliru menuntut panjang2=prefix1. Server REASSEMBLE_SQL dan klien sudah memakai prefix+pageitems+suffix. Helper sekarang mempertahankan kedua sisi indeks, tanpa menghapus hash, identity, UTF8, ranges atau exact item count. Actual fetch lama mereproduksi error persis;18kontrol syntheticRPC memakai fungsi baru lulus, termasuk suffix yang utuh dan penolakan metadata/hash/range/jumlah yang salah. Ini bukan perubahan hitungan hasil produk.

Expected, red-first controls dan hasil lokal ada pada message-format/ dan reassembly/. Uji Native99 harus dijalankan kembali pada commit perbaikan; tidak dijalankan ulang pada kode yang sama untuk menyembunyikan kegagalan. OW01 belum ditutup sebelum hasilnya lengkap.

P19b7 yang lama sudah selesai:11job sukses, transport gagal sebelum suite karena port54322 terpakai. Ukuran5000 staged selesai87–105detik pada run itu, halaman lanjut<1detik, buka ulang sekitar1,2detik; finance5000 tetap timeout8detik. PASS pengukuran bukan penerimaanSLA atau OW12 selesai. Perubahan formatter tidak mengubah kernel perencanaan.
