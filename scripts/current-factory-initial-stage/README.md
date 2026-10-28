# Tahap awal analisis pabrik — kandidat D17-18

VENI. VIDI. VICI. ERP — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan, laporan, stok dan HPP adalah raja.

4ac gagal pada unit0 kedua job setelah tiga pembatalan 8 detik. Diagnosis exact
5b32 mengukur run_unit 7.324,137 ms (keluaran 3,53 MB), compiler 5.575,020 ms
(40,09 MB), status 45,341 ms. Waktu run_unit belum mencakup penyimpanan output
dan status step. Diagnosis serta seluruh pemulihannya lulus; diagnosis bukan
kelulusan backend. Tidak ada perubahan perhitungan resmi atau pemeriksaan angka.

Kandidat memberi unit0 frozen-v2 dengan targets_total >= 1000 satu jalur server
berbatas 16 detik, lock2 detik. Ini batas awal terukur untuk diuji dengan overhead
step lengkap, bukan jaminan performa dan bukan kenaikan berulang tanpa diagnosis.
Empat jadwal lama dan batas operasi biasa 8 detik tetap persis. Jadwal kelima
menjalankan maksimal empat unit awal per menit, masing-masing transaksi sendiri
(maksimal 64 detik kerja per pemanggilan jadwal); pg_cron menserialkan run jadwal
yang sama. Tidak ada tidur buatan, pekerjaan ganda atau progres buatan.

Pemilih kerja lama melewati hanya unit0 besar tersebut. Jalur baru menyalin
identitas pelaku, akses sebelum/sesudah, row lock SKIP LOCKED, step, percobaan
maksimal tiga, dan pencatatan progres Native. Dua fungsi baru privat, milik
cp7_capture; hanya pembungkus penjadwal boleh dipanggil postgres. Tidak ada RPC,
tabel atau peran baru. Heartbeat lama tetap dikelola jalur biasa dengan batas8s.

Step publik 8 detik menolak unit awal besar sebelum pekerjaan atau percobaan
dibebankan: SQLSTATE55000 / CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED.
Akses yang berubah tetap diperiksa dahulu. B menyesuaikan driver miliknya untuk
membaca get/status dengan UUID yang sama; total belum diketahui tetap belum
diketahui. Paket browser B belum boleh dibuka sebelum actual all7 kandidat ini
lulus beserta pemulihan dan bukti lengkap. Browser/Auth bukan bagian eksekusi A.

Installer memverifikasi pendahulu asli, seluruh22 kelompok katalog, seluruh data
dan sequence; hanya tiga fungsi pengganti dan dua fungsi baru yang diizinkan.
Inverse sebelum pakai menjaga seluruh data sebelum DDL. Setelah dipakai, hanya
pemulihan dump penuh yang sah. Baseline pembanding laporan tetap memakai fungsi
keuangan semula; perubahan worker tidak disisipkan ke baseline itu.

Tujuh kelompok lama, Native20, pembanding laporan penuh dan semua assertion
bisnis dipertahankan. Uji pabrik menambah dua definisi jadwal yang berasal dari
produk, tanpa override frekuensi; semua run kedua jadwal harus selesai dan dicatat.
Kontrol PostgreSQL menguji job kecil tidak diambil, step8s ditolak tanpa percobaan,
timeout0/8/16,001 detik ditolak, worker lama melewati job besar, akses berubah
mendahului penolakan batas, dan koneksi kedua melewati row lock. Kontrol itu
di-rollback penuh; penyelesaian pabrik hanya oleh penjadwal asli.

Sumber lama dan manifest historis tidak diubah. SOURCE.json dan ORIGIN.json
menyatakan penerus serta perubahan alat uji secara tepat. Semua bukti pendahulu
dan profile asli diverifikasi sebelum koneksi DB. Lingkup hanya localhost54322,
cp6_rollback. Default/hosted/Enteng/produksi/WA/CP7C tidak diaktifkan.
Formal5/16, independent_acceptance=false, production_go=false.

Rujukan teknis: PostgreSQL16 client connection defaults (statement_timeout per
statement), Supabase Cron dan upstream citusdata/pg_cron (satu run per job).
