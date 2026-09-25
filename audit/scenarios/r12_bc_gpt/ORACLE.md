# GPT BC — oracle tambahan mandiri, dibekukan sebelum probe baru

Status: PROPOSED; seluruh kasus belum diuji oleh skenario GPT baru. Dokumen ini diturunkan dari kontrak Master Pulih; kontrak Perubahan Pulih dan Addendum CP7 hanya menetapkan batas/cakupan, bukan memberi hasil uji. Setelah melihat kode/log writer dan laporan Fable sebelumnya, GPT sudah terpapar terhadap daftar kasus BC serta dua celah F3/ACC-C12. Ini *follow-up independen* untuk celah itu, bukan oracle yang dibuat sebelum implementasi BC atau audit seluruh 39 ACC.

## GBC-1 — sumber fisik sama dengan identitas permintaan berbeda

- Sumber: Master Pulih M:3931–3935 (custody/value pending, barang sama tidak menjadi stok dua kali), M:5281–5283 (C02/C03), M:5290 (C12); M:5311–5313 untuk fixture dan klasifikasi.
- Fixture klon sekali pakai: baseline historis 3 PCS dengan satu identitas fisik yang dapat ditelusuri ke sumber; 3 PCS baru yang benar-benar berbeda sebagai kontrol positif. Semua operasi biasa lewat RPC resmi, actor berizin, masa pembukuan terbuka.
- Jalur A: daftarkan 3 PCS historis sebagai custody pending, inspeksi dan nilai, lalu ajukan lagi sumber fisik yang *sama* dengan request UUID lain dan bila API memungkinkan custody key lain; coba inspeksi dan nilai. Expected: stok siap maksimum 3 PCS untuk sumber itu, nilai resmi satu kali, klaim kedua ditolak atau ditautkan ke sumber tanpa tambahan stok. Satu error harus menyisakan qty, jurnal, dan custody persis semula. Periksa semua boundary setelah dua operasi, bukan hanya hasil RPC.
- Jalur B: 3 PCS fisik baru dengan identitas sumber yang benar-benar lain diterima, diinspeksi dan dinilai. Expected: stok siap bertambah 3 PCS, sehingga total 6 PCS untuk dua sumber berbeda. Pembelian baru tidak boleh dipakai sebagai kontrol duplikasi sumber lama.
- Jika API tidak dapat membuktikan dua permintaan menunjuk barang fisik yang sama, status `INCOMPLETE / NEEDS_SOURCE_POLICY`, bukan PASS dan bukan counterexample produk.

## GBC-2 — data mandor lama yang diterima database

- Sumber: Master Pulih M:1691 (layar tersambung sumber nyata), M:3900–3902 (nota mandor dan stok resmi), M:5304 (D09 desktop/HP, reload, error/loading dan 7 PCS), M:5311–5313.
- Dua fixture pada klon terpisah: mandor aktif UUID v4 dan mandor aktif UUID bentuk kanonis 8-4-4-4-12 dengan nibble versi 0 yang sudah diterima oleh kolom PostgreSQL uuid. Jangan menganggap UUID uji tersebut ada di hosted atau legacy.
- Expected pada v4: halaman Nota Ambil Aksesori memuat, stok server 7 PCS ditampilkan, satu POST 7 PCS membuat saldo 0 walaupun tombol ditekan dua kali/reload. Expected pada ID lama yang memang diterima database: data mandor aktif tidak membuat seluruh workspace kosong; bila format legacy ini secara kontrak harus ditolak, ada validasi/import report spesifik sebelum halaman digunakan. Error parser tidak boleh dilabel sebagai layanan jaringan terputus. Cek desktop dan HP.
- Jika baseline seed tidak mewakili data bisnis yang diizinkan kontrak, klasifikasi persoalan data dan parser secara terpisah. Hasil v4 tidak menutup hasil kasus non-RFC; jangan menyimpulkan data hosted tercemar tanpa inventaris baca saja.

## GBC-3 — pencarian lintas tab sesudah dokumen diposting

- Sumber: Master Pulih M:5120–5126 (pencarian/daftar nyata), M:5304 (UI), M:5307 (server-side search/paging).
- Di UI, cari kode SKU stok, POST pengisian pos yang sah, pindah ke tab Dokumen tanpa menghapus pencarian, lalu temukan dokumen yang baru dibuat dari tab itu dengan indikator filter yang terlihat dan bisa diubah. Buka dan balikkan satu kali; saldo akhir kembali sama dengan sebelum pengisian, jurnal/inversi cocok. Ulangi setelah reload. Jika tab sengaja membagi filter, query setiap tab harus tertera dan terkendali.
- Expected: dokumen tidak lenyap akibat filter yang tersembunyi; saldo/ledger tidak mengganda. Kegagalan navigasi fixture/selector menghasilkan INCOMPLETE, bukan putusan produk.

## Kriteria bukti dan status

Pin SHA skenario Python/browser dan tool_head/product_ref; satu workflow native pada database disposable; log case input, expected, actual, actor, timezone, before/after qty/nilai/jurnal, cleanup/primary_unchanged dan run/job ID. Hasil writer T1 44/44, Fable 49/49, T3 27 file, rollback 135/135 tetap bukti mereka, tidak dipindahkan menjadi hasil skenario GPT. Full BC `UNVERIFIED` sampai 39 ACC/ALL terdampak direkonsiliasi dan ketiga probe ini dinilai. CP6 HOLD / audit_complete=false / production_go=false.
