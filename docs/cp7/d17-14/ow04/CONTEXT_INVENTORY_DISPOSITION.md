# Perbaikan penghalang komposisi f6a05315

Run39469756271/job118790414794 berhenti sebelum SQL OW04 dan sebelum32kasus.
Kesalahan writer: daftar10 cabang admisi `require_internal` dianggap sama
dengan semua konteks privat. Koreksi nota/retur dan beberapa modul lain
memiliki pengaman sendiri. Menghapus assertion akan meninggalkan lubang
penolakan konteks, sehingga assertion tidak sekadar dibuang.

Komposer tetap memverifikasi guard asli dan dispatch10 yang sama. Daftar
sumber tertutup30 tabel diperiksa terhadap katalog seluruh namespace,
tanpa filter awalan nama. Jenisnya26 pasangan PID/transaksi, satu transaksi
tanpa PID, dua txid bigint, dan satu txid xid8. Nama dengan akhiran_v1 sah
hanya bila termasuk daftar sumber tersebut. Tabel hilang/asing, tipe,
pemilik, izin, kebijakan atau struktur yang berubah ditolak.

Keterlihatan29 tabel diperiksa sebagai postgres, pemilik guard sebenarnya,
bukan supabase_admin installer. Penanda apply rencana hanya terlihat oleh
pemiliknya, cp7_plan_writer. Satu pembaca boolean tetap pada schema BARU
cp7_credit mengembalikan apakah txid kini memiliki penanda itu. Pembaca
tidak menerima argumen, tidak menulis, tidak membuka admisi Native, dan
hanya bisa dipanggil postgres. CREATE schema sementara untuk pemilik fungsi
dicabut lagi. Tidak ada tambahan izin tabel ERP atau perubahan ACL schema
lama. Definisi, pemilik, konfigurasi dan ACL pembaca diperiksa persis.

Kedua guard penolakan memakai daftar typed yang sama. Guard milik retur
hanya mengecualikan tepat satu konteks SALES/RETURN milik aktor dan nota
yang benar. Semua baris compound_scope ditolak, termasuk depth0. Tidak
ada pengecualian berdasarkan status/jumlah/depth yang tidak ada di sumber.
Setelah pemasangan, katalog baseline dibandingkan utuh; hanya empat schema
baru yang dikecualikan. Uninstall menghapus pembaca bersama schema baru.

Dua pemeriksa internal mencatat penilaian awal sendiri sebelum bertukar
temuan. Keduanya mengonfirmasi kesalahan asumsi daftar; counter tambahan
menemukan bentuk txid, aturan depth0, dan kebutuhan menjalankan pemeriksaan
sebagai postgres. Ini counter-review writer, bukan audit independen.

Pemuatan Python dan30 deklarasi sumber lulus lokal.12 fixture baru juga
memaksa constraint/trigger tertunda sebelum rollback internal, tanpa mengubah
expected uang atau32 ID kasus. Hasil lokal bukan bukti Native. Kegagalan
pertama disimpan lengkap dalam CI_F6_FIRST_RUNTIME.log.gz dan receipt JSON.
OW04 tetap BELUM SELESAI, production_go:false.
