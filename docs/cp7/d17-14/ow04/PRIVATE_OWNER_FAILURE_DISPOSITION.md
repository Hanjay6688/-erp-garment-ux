# Hasil pertama fffc54fc dan perbaikan kepemilikan

Run39473461357/job118803249673 berhasil memasang komposisi atomik dan
menjalankan32slot:6PASS/26INCOMPLETE. Semua12skenario settlement baru tertahan
saat persiapan pembacaan sumber. Tidak ada settlement baru yang lulus.
Pemulihan CP6 true; advisor gate awal false. Report lengkap dan log pertama
disimpan gzip, SHA dan32disposisi di CI_FFFC_FIRST_FAILURE.json.

**Cacat komposisi produk.** current_leaf_assignment dan family_read_v1 serta
sebagian objek proposal masih dimiliki supabase_admin yang menjalankan DDL.
Fungsi bisnis postgres tidak mendapat EXEC setelah PUBLIC dicabut. Dua schema
aritmetika dan beberapa tabel/domain juga mewarisi pemilik pemasang.

Finalizer hanya menyentuh empat schema OW04 yang baru dibuat, dalam transaksi
pemasangan yang sama. Schema, domain, tabel dan fungsi privat dimiliki postgres,
kecuali dua fungsi dan dua tabel yang memang milik capability writer masing-masing.
Definisi/kontrol sumber tidak diubah. Tidak ada grant tabel ERP atau perubahan
guard Native. Hak SELECT postgres pada dua tabel request/scope baru dinyatakan
eksplisit; UPDATE dibatasi sembilan kolom scope yang diisi server. Tidak ada
hak mengubah payload request, INSERT atau DELETE request untuk postgres.

Counter internal menemukan bahwa pin fungsi/tabel saja belum menangkap perubahan
pemilik schema/domain. Sekarang pemilik/ACL empat schema dan domain, constraint
domain, fungsi, tabel, column ACL serta policy dipin dan dibandingkan kembali.
Keterlihatan request/scope juga diperiksa sebagai postgres. Counter hak scope
dan kesembilan kolom selesai lewat pembacaan actual statements, bukan voting.

**Advisor.**36temuan awal semuanya INFO RLS/no-policy:30dari predecessor F05
yang tidak berubah dan6scope baru. Pada enam tabel baru, policy PUBLIC false
ditambahkan; ini sama dengan default-deny ketika RLS aktif tanpa policy.
Tidak ada kebijakan yang memberi akses baru. Tiga puluh temuan lama tidak
dianggap temuan OW04: daftar objek tepatnya ditangkap setelah predecessor
terverifikasi, SEBELUM DDL OW04. Hanya INFO default-deny pada objek persis
itu mendapat disposisi F05 yang sudah berlaku. Temuan baru, WARNING, jenis
lain dan keadaan tidak dapat dibandingkan tetap menolak qualification.
Hasil strict gate pertama false tetap dipertahankan, bukan ditulis ulang.

**Bukti lokal.**16kontrol menjalankan SQL actual finalizer terhadap fixture
izin terisolasi: penolakan fungsi/tabel sebelum perbaikan, keberhasilan sesudahnya,
penolakan perubahan payload/INSERT request, dua owner khusus, schema/domain,
dan policy false. PGlite tidak dapat menurunkan hak bootstrap postgres; fixture
mengganti HANYA nama target role dengan ow04_business yang bukan superuser.
Percobaan bootstrap yang gagal dan kesalahan batas transaksi fixture disimpan.
Ini bukan bukti Native atau otoritas bisnis. Tujuh kontrol disposisi advisor
dan36temuan nyata pertama membuktikan6temuan baru tetap ditolak;30INFO lama
saja dapat diklasifikasikan. Expected uang dan32ID kasus tidak berubah.

Run ERP berikutnya harus membuktikan hasil pada role/struktur asli. OW04 tetap
BELUM SELESAI; HTTP/browser/race, Native EMPTY, keluarga terkoreksi dan alur
lanjutan belum selesai. production_go:false.
