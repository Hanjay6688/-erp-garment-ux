# CP6: perapihan sebelum pemasangan pertama

Arahan owner 1 Oktober 2026: bereskan enam risiko dari auditor sebelum membahas go produksi. Titik awal kode: CP6 diterima untuk lingkup kontrak, commit `10a834712e515af86c6d8baa89bbe40cff9793e3`. Cabang perbaikan `cp6/release-readiness` tidak membawa perubahan CP7. Paket database AC–BF tetap 30 berkas dengan byte dan hash yang sama; tidak ada perubahan cara menghitung uang, stok, atau HPP.

## Hasil yang harus dibedakan

| Risiko auditor | Perbaikan pada cabang ini | Batas penerimaan |
|---|---|---|
| Belum dipasang di hosted | Preflight baca saja, identitas paket, dan runbook maintenance serta pemulihan disiapkan | Uji pada hosted baru bisa dilakukan di jendela yang disetujui. Uji CI tidak disebut pemasangan hosted |
| Sen W8 menumpuk per PO | Catatan di HPP per SKU dan oracle baru tujuh dokumen, koreksi langsung serta invoice terlambat | Keputusan T3=A tetap berlaku; tidak dibuat batas sen per PO |
| Tes BF masih memakai tarif SKU | Semua entrypoint `cp6_bf_free_*` memakai tarif Native vendor, SKU menyimpan `laundry_rates: []` | Receipt dan verdict lama tetap historis; tidak diganti label PASS |
| UI belum dilihat langsung | Pemeriksaan browser dengan Auth/PostgREST asli, desktop dan ponsel, screenshot pengaturan dan pembulatan | Kesesuaian tampilan terhadap demo memerlukan demo acuan. Pemeriksaan ini tidak mengklaim seluruh UI sama dengan demo |
| Delapan isian kosong | Status keputusan owner dan status penerapan dipisahkan; pesan terlihat sebelum posting; empat keputusan punya tombol pengisian formulir | Tombol mengisi formulir, belum menyimpan. Akun, kategori, dan syarat vendor tidak ditebak |
| Oracle auditor terbatas | Tambahan oracle prasyarat invoice, campuran FREE/WAIVED/UNKNOWN/KNOWN, pembulatan tujuh dokumen dan HPP 16 PCS | Ini bukti penulis penerus, bukan pengesahan auditor lain atau klaim kepercayaan 100% |

## Pengaturan: delapan isian, empat keputusan, satu sengaja kosong

Dasar lengkap: [D11 dan keputusan owner 26 Sep](../cp6-d11-kebijakan-dan-gbd03.md). Ada **13 kode**, bukan hanya delapan. Delapan berikut masih membutuhkan isian atau konfirmasi terhadap akun/perjanjian nyata:

| Kode | Isian yang dibutuhkan | Selama kosong |
|---|---|---|
| ACC-DEC01 | Penegasan dua garis waktu nyata; satu pilihan server | Tanggal tetap terpisah; transaksi tidak tertahan |
| ACC-DEC03 | Akun kredit aktif dan postable (pendapatan/beban), batas harga rata-rata atau tanpa batas | Penilaian titipan tertahan; penerimaan dan pemeriksaan tetap berjalan |
| ACC-DEC04 | Akun beban aktif dan postable untuk servis pelanggan/perbaikan FG sendiri | Tujuan yang belum punya akun tertahan; pemakaian pabrik tetap berjalan |
| ACC-DEC06 | Akun selisih pembulatan naik dan turun yang diterima server | Pembulatan nota tertahan |
| ERP-DEC02 | Daftar kategori aksesori aktif yang boleh gratis; daftar kosong juga sah bila memang dipilih | Baris gratis tertahan; harga belum diketahui tidak dianggap nol |
| LAU-DEC01 | Borongan/minimum hanya bila digunakan vendor | Tarif per PCS tetap berjalan; kosong dapat disengaja bila fitur tidak digunakan |
| LAU-DEC02 | Hasil baik/BS/cuci gagal yang benar-benar boleh ditagih menurut perjanjian | Posting invoice tertahan; draf dan penerimaan tetap berjalan |
| LAU-DEC03 | Diskon, tambahan, pembulatan; akun pajak bila memang digunakan | Pemakaian unsur tambahan itu tertahan |

Empat nilai **sudah diputuskan** owner; formulir dapat diisi melalui tombol “Isi sesuai keputusan owner”, lalu diperiksa dan disimpan lewat RPC yang sama dengan pengaturan biasa:

| Kode | Keputusan 26 September |
|---|---|
| ACC-DEC05 | `CREDIT_THEN_CARRY`, kondisi `USABLE` |
| ACC-DEC07 | `approval: NONE`; bukan ambang `0.00` yang justru mewajibkan persetujuan |
| LAU-DEC04 | `ALLOW_PENDING`; HPP belum final dan tutup buku terdampak tetap tertahan |
| LAU-DEC06 | `PRODUCT_COST` + `CORRECTION_DOCUMENT` |

**LAU-DEC05 sengaja tidak diaktifkan.** Tarif vendor/proses/paket biasa tetap berjalan. Nilai yang sudah SET di aplikasi selalu ditampilkan sebagai nilai yang berlaku; riwayat keputusan tidak dipakai untuk menimpa pengaturan yang telah diubah owner.

Koreksi penjelasan lama: kode Native memperbolehkan **draf** invoice tanpa LAU-DEC02/06; pengaturan diperiksa saat **posting**. Oracle baru memeriksa kedua penolakan satu per satu, tanpa perubahan status dokumen/utang/accrual, kemudian posting setelah kedua pengaturan diterapkan.

## W8 untuk keuangan

Contoh oracle baru: tujuh nota masing-masing `10.006` dibulatkan menjadi `10.01`, sehingga total **70.07**. Membulatkan total mentah hanya sekali menghasilkan **70.04**; angka kedua bukan oracle sistem ini. Sen dapat terkumpul di satu PO karena harga rata-rata berjalan. Yang wajib cocok adalah total per dokumen, posisi pada setiap tanggal, nilai stok habis nol, dan jejak biaya ke sumber serta PO. Ini mengikuti keputusan T3=A; tidak ada perubahan mesin biaya.

## Bukti dan status

Receipt baru berada di folder ini setelah run selesai. Workflow Native bernama “CP6 Release Readiness (Native package and UI)” memasang paket yang byte-nya sama pada salinan sekali pakai, lalu menjalankan kasus baru bersama regresi lama, race, Auth HTTP, browser, pemeriksaan advisor dan backup/restore. Workflow Shell memeriksa tes, batas kepemilikan, keamanan dan build.

Lolos kontrak CP6 tetap terpisah dari **go produksi**. Tidak ada maintenance, pemasangan hosted, merge utama, atau nilai pengaturan nyata yang dilakukan oleh cabang ini.
