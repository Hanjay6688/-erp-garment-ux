# OW10 pilihan cadangan — kontrak sebelum caller

23 Oktober2026 WIB. Tambahan privat pada config profil yang sudah ada: pasangan opsional
`buffer_mode: DAYS|STATISTICAL` dan `service_level: null|0.90|0.95|0.99` (semua desimal teks).
Payload lama tanpa pasangan ini tetap berarti aturan lama dan dipertahankan persis saat retry.
DAYS meminta service_level=null; STATISTICAL meminta buffer_days=null, sumber permintaan riwayat
tersedia dan tingkat layanan yang dipilih eksplisit. Tidak menjumlahkan dua cadangan.

Langsung/bertahap mengambil total, jumlah hari dan stddev_samp dari hari AVAILABLE yang sama,
lalu kernel target-unified-2 yang sama dengan ROP. Syarat14 hari statistik milik kernel tetap.
Hari tersensor tidak diubah menjadi0; simpangan yang belum diketahui tetap null. Pilihan manual
permintaan tetap pada DAYS; ketidakpastian angka manual belum punya bukti distribusi.

ROP menghormati pilihan cadangan/tingkat layanan eksplisit profil. Profil lama tetap memakai
aturan ROP sebelumnya. Z per baris membaca tingkat layanan efektif; tampilan harus menerangkan
perubahan ini. Periode riwayat, waktu proses terukur vs asumsi dan alokasi WIP masih perlu
disatukan; penambahan pilihan statistik ini tidak menutup OW10.

Empat penggantian badan fungsi di tahap `cp7_target_policy_stage`, di atas tahap produksi B.
Tidak ada tabel, kolom, fungsi, endpoint atau grant baru; A mengomposisikan rantai, admisi22,
penjaga setelah-pakai dan pemulihan. Invers menolak profil yang sudah memakai pasangan baru.
Hasil langsung dengan pilihan statistik memakai cp7.native-baseline.v2 dan target_basis
UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS. Arsip v1 tetap dibaca tanpa mengubahnya.

Pilihan DAYS eksplisit juga meminta jumlah hari yang diketahui (0 dibolehkan), bukan cadangan null.
Konfigurasi legacy tetap boleh null dan tidak diubah. STATISTICAL pada ROP menghormati minimum hari
profil yang lebih ketat daripada14; jika belum terpenuhi, point tetap null dan reason
PROFILE_MINIMUM_NOT_MET, dijelaskan dengan jalan ke profil. Bukan dikatakan kurang14 ketika sudah14.
Ini penambahan alasan pada respons ROP lama; kunci respons, tabel/kolom dan endpoint tetap sama.
