# Uji pemasangan SQL Global pada fixture disposable

Sumber Global `c9248b8770ec8cfe0f7e2f2fd8da26c141ea67c5`, rencana pemasangan SHA-256 `96ce9eee5c4e12f2669cb1e9636080632a5f84c043e1d01b6c14c1c72a288a40`. PostgreSQL 17.6 loopback memulihkan 215 blok COPY dari dump ERP awal yang byte-identik pada Original E4EA. Katalog E4EA memasok tipe, domain dan identitas fungsi yang diperlukan fixture.

Seluruh 12 potongan SQL dan delapan adaptasi fungsi terpasang dengan pemeriksaan body aktif. Pemeriksa mencocokkan 16 fungsi, tiga tabel, RLS, ACL, serta OID dan hak fungsi lama. Fingerprint SQL cocok dengan pembacaan Python untuk seluruh 25 grup katalog fixture. Percobaan DDL dari koneksi kedua tertahan saat 64 relasi katalog dikunci. Delegasi relasi sebelum kunci katalog ditolak sesuai kontrak. Rollback mengembalikan seluruh 25 grup dan identitas delapan fungsi. Cluster fixture dihapus.

Percobaan fixture awal berhenti sebelum pemasangan karena domain `cp7_credit.cent_amount`, role `cp7_credit_write`, dan pengaturan `check_function_bodies` dari dump belum dipulihkan untuk pemeriksaan ini. Fixture berikutnya mengambil domain dan role dari katalog arsip, lalu mengaktifkan pemeriksaan body sebelum pemasangan. SQL Global tetap sama.

Masukan produksi dan admission Global masih tertutup. Uji ini memberi kredit nol kasus ERP. Global masih memerlukan hasil SKU, katalog aktual, profil writer/authority/advisors, D1/E dan pemulihan pada kandidat gabungan.
