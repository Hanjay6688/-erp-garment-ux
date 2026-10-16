# Keputusan owner atas pertanyaan Fable cp17c (16 Okt 2026) — dicatat auditor sesudah laporan dikunci

Dicatat Fable sesudah penguncian `LOCK.md` (commit ccafdb18). Laporan yang terkunci tidak diubah. Nomor keputusan resmi
ditetapkan penulis di `docs/cp7/OWNER_DECISIONS_20261008.md`; di sini hanya teks owner apa adanya dan oracle uji ulang
Fable, yang ditetapkan sebelum perbaikan dibuat.

## 1. Kas tidak boleh minus (FABLE-013)
**Teks owner:** "Ya, untuk aturan kas minus, ikuti rekomendasi Fable: periksa saldo harian per rekening menurut tanggal
ekonomi dan tanggal buku/pengakuan. Tolak transaksi jika salah satunya menjadi minus. Terapkan juga pada detektor dan
koreksi/pembalikan, tanpa mengubah tanggal asli atau membuka ulang periode tertutup secara otomatis."

**Oracle uji ulang Fable:**
- Skenario `fable_cp17c_cash_basis.py` (run 38786227211) dijalankan ulang tanpa perubahan. Pengeluaran 1.500,00 bertanggal
  15 Okt sesudah pemasukan periode tertutup harus **ditolak** `CP7_CASH_NEGATIVE`; saldo per tanggal buku tidak pernah < 0.
- Koreksi dan pembalikan (pemasukan lain-lain, penerimaan pelanggan, setoran modal) yang membuat saldo per tanggal
  ekonomi **atau** per tanggal buku minus pada hari mana pun di rekening itu: ditolak.
- `cp7_guard.findings()` melaporkan saldo minus lama di kedua dasar tanggal, per rekening per hari.
- Tidak ada perubahan `economic_date`/`transaction_date` jurnal yang sudah ada; `closed_through` tidak berubah oleh
  penjaga atau koreksi.
- Kasus penulis `CP17_CASH_*` tetap lulus; tidak ada penjaga lain yang dilonggarkan.

## 2. Layar uang dan absensi di mode Enteng (FABLE-015)
**Teks owner:** "sembunyikan begitu terhubung langsung muncul, doesnt matter juga kalau mau langsung muncul karena gabakal
dipakai juga jadi ga kerja 2 kali sih klo mau munculin"

**Tafsiran auditor (dikembalikan ke owner bila keliru):** di Enteng, 11 layar itu disembunyikan sampai tersambung, lalu
langsung tampil begitu tersambung. Penulis boleh tidak membuat langkah sembunyi terpisah bila layar itu langsung
disambungkan, karena owner belum akan memakainya sebelum tersambung.

**Oracle uji ulang Fable:** di build mode Enteng, tidak ada menu yang menampilkan angka contoh tanpa label. Setiap layar
uang/absensi bersifat salah satu: tersambung (komponen yang sama dengan mode uji), atau tidak tampil / layar batas tanpa
angka. Diperiksa dari kode routing dan sensus layar `fable_cp17c_screens.mjs`.

## 3. Layar data master (FABLE-017)
**Teks owner:** "dibuatkan layar tapi jangan simple banget juga, sedeng lah muat info dan fitur yg dibutuhkan"

**Oracle uji ulang Fable:**
- Di kedua mode tersambung, layar pelanggan, supplier/vendor, mandor, gudang/lokasi, master kain dan aksesori, serta tarif
  upah mandor (per model × komponen kerja × mandor, dengan tanggal berlaku) bisa membuat, mengubah dan menonaktifkan data
  dengan riwayat perubahan dan hak akses. Data yang sudah dipakai transaksi tidak bisa dihapus.
- Rantai dari layar saja: mandor baru + tarif baru → Bagi Potongan → "Catat selesai jahit" berhasil dengan upah sesuai
  tarif yang berlaku pada tanggal jahit. Tarif yang diubah sesudahnya tidak mengubah upah yang sudah tercatat.
- Pelanggan dan supplier baru dari layar master langsung bisa dipakai di penjualan dan penerimaan.
- Ada uji browser (desktop dan HP), HTTP, dan balapan dua tab untuk setiap layar master.

## 4. Buka ulang PO yang sudah selesai (FABLE-014)
**Teks owner:** "Tombol buka ulang PO dibuat, dengan penghalang seperti fitur koreksi lain"

**Oracle uji ulang Fable:**
- Tombol memanggil penulis Native `erp.reopen_production_order` lewat fasad dengan token tinjauan, alasan, idempotensi,
  dan riwayat yang tidak bisa diubah.
- Penghalang disebut di layar dan menolak, misalnya barang jadi PO itu sudah terjual atau dipakai, atau periode sudah
  ditutup sesuai aturan Native.
- Sesudah buka ulang, WIP dan HPP PO konsisten dengan buku besar. Menyelesaikan lagi menghasilkan HPP final yang sama
  bila tidak ada transaksi baru.
- Ada uji browser, HTTP, dan dua tab bersamaan (satu menang).
