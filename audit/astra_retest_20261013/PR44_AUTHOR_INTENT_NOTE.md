# PR44: catatan penulis probe, bukan penerimaan audit

Kandidat produk: `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2`.
Pembanding: `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`.
Asal bukti: `AUTHOR_INTENT_SOURCE_REVIEW`. Tidak digunakan menutup klaim runtime atau menerima PR44.

Perubahan writer pada `scripts/cp7_astra_timeline_reuse_probe.mjs` masih mengikuti tujuan awal probe:

- Daftar fungsi tidak lagi wajib sama persis dengan versi sebelum penambahan K7a. Dua fungsi `_within` yang memang ditambahkan K7a diperiksa melalui transformasi teks yang disebut satu per satu; setiap jangkar wajib muncul tepat sekali.
- Isi fungsi lain tetap diperiksa persis. Pembungkus lama wajib memanggil batas lama. Teks di luar fungsi tetap dibandingkan setelah hanya tambahan komentar dan kepemilikan yang disebut eksplisit dikeluarkan dari perbandingan.
- Mutan `ignores_supply` tetap menghilangkan pemeriksaan pasokan kosong, sambil mempertahankan guard baris yang baru. Mutan `wrong_target` tetap ada.
- Inventaris baru memerlukan kedua cacat baris duplikat. Deklarasi 595 kasus penuh = 571 + 24; 151 cepat = 145 + 6. Komentar yang menyebut `145+3 quick` tidak cocok dengan ekspresi 151, tetapi pemeriksaan kode menggunakan 151. Ini salah komentar, bukan bukti bug produk.

Catatan ini hanya menyatakan adaptasi probe sesuai maksudnya. Penerimaan optimasi PR44 harus diberikan Fable atau auditor lain yang tidak menulis optimasi tersebut. Menjalankan regresi aplikasi yang kebetulan menggunakan fungsi itu tidak menggantikan penerimaan terpisah tersebut.

`production_go:false` tetap.
