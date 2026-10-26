# D17-18 — komposisi persiapan pilihan dan keuangan

Pembaruan setelah run pertama a3ce9317/run40297810688/art12642445168:
status INCOMPLETE,2PASS/4INCOMPLETE; kegagalan penuh tetap tersimpan di
FIRST_RUNTIME_FAILURE_A3CE.json dan Original. Tiga kasus berhenti pada
pembanding STEP/GET dalam satu transaksi: GET melihat lock transaksi STEP
yang masih sah. Adapter A mempertahankan seluruh isi B.ready, mengganti
hanya assertion GET dengan pemeriksaan PID/kunci tepat dan seluruh field
lain tetap persis. B tidak diedit, kontrak HTTP antar transaksi tidak diubah.

Kasus pembatalan berhenti pada pemeriksaan konteks pemanggil. Runner secara
tertulis memulihkan pengaturan yang sebelumnya belum ada menjadi string
kosong. Penerus mencatat ketiga nilai mentah sebelum/sesudah, menuntut setiap
nilai non-null tetap persis, dan membandingkan auth.uid()/auth.jwt() efektif.
Batas8s tetap terpisah dan keras; tidak ada nilai identitas yang diabaikan.
Hasil runtime penerus masih diperlukan untuk memastikan diagnosis ini.

Satu INFO RLS tanpa policy pada tabel privat baru belum masuk review lama.
Review baru hanya untuk cp7_frozen_choice_preparation.work setelah pemilik,
RLS, tidak adanya policy/ACL PUBLIC dan seluruh hak langsung lima role
terverifikasi tertutup. Review pendahulu disimpan utuh, tidak diperluas;
warning/tabel lain/privilege baru tetap menahan gate. Produk tidak diubah.
Sembilan uji penjaga lokal bukan pengganti hasil Native6 aktual.

Status: prasyarat Progress Native5 aktual sudah PASS5 pada0c86d277;
Native6 ini belum mempunyai hasil runtime. SOURCE diikat hanya ke Original
tersebut setelah pemeriksaan sumber dan pemulihannya selesai.

Enam kasus terfokus menjalankan pemasang A lengkap, lima endpoint baru B,
antrean K4 yang tetap memuat keuangan resmi, retensi, pemeriksaan 22 kelompok
katalog, penolakan inverse setelah dipakai, dan pemulihan seluruh basis CP6.
Tiga helper fixture B berasal byte-exact dari commit yang ada di
B_FIXTURE_SOURCE.json. Jalur Native6/factory asli B tidak diganti.

Kasus membuktikan sumber dingin menunggu persiapan; permintaan ulang memakai
identitas yang sama; pemeriksaan izin dan sumber saat SAVE; kegagalan simpan
atomik; payload kedaluwarsa dibersihkan tanpa menghapus identitas/receipt;
pembatalan dapat dipulihkan; error tak dikenal tetap gagal; runner lama
menyelesaikan persiapan dan angka resmi tanpa mengubah uang, stok, atau HPP.

Setiap statement kecil tetap dibatasi 8 detik. Waktu seluruh kasus dicatat,
tanpa syarat total 8 detik dan tanpa menjadikannya ukuran satu operasi pengguna.
Pembatalan 57014 disuntikkan untuk menguji pemulihan; itu bukan pengukuran
timeout nyata. Pemanggilan K4 dari SQL bukan bukti pemicu cron per menit.

Perbaikan B b96e2f74 juga diuji sebelum compiler: injeksi SQL57014 pada awal
pemeriksaan akses harus dicatat pada baris kerja yang sama, pulih setelah satu
gangguan, dan berhenti FAILED setelah tiga gangguan. Definisi pemeriksa akses
dikembalikan persis, tanpa mengubah aturan hak akses produk. Ini tetap uji
injeksi pada runner gabungan, bukan bukti penghentian proses server secara paksa.

Belum membuktikan Auth/HTTP, browser, dua sesi, data pabrik penuh, penerimaan
gabungan atau produksi. Kegagalan lama tetap INCOMPLETE. production_go=false.

Alur: bind_sources.py memeriksa proof aktual dan mengikat semua berkas;
admission.py mengulang penerimaan sumber lama dan memeriksa Original induk;
probe.py menjalankan kasus, inverse dan pemulihan penuh. Fetch Original dan
admission selalu berada pada langkah workflow yang berbeda.

Induk Native5 kini disiapkan pada0c86d277, menggantikan546 yang gagal.
Seluruh sembilan berkas harness induk disalin byte-exact; runtime0c masih
berjalan ketika perubahan ini disiapkan. Binder tetap menolak Original bukan
PASS dan SOURCE Native6 belum dibuat. Kegagalan546 tetap dipertahankan.

Pembaruan26 Oktober2026: run40286627929/job121451709620 selesai09:02:39UTC,
artifact12637959084. Lima kasus PASS, 24 ukuran keuangan persis sumber resmi,
perubahan sumber terlihat gagal dan permintaan baru pulih; seluruh22 kelompok
katalog, data, sequence, CP6 dan pemeriksa keamanan kembali persis. Pembacaan
status terukur4,779–11,814ms. Keterangan “masih berjalan” di atas adalah riwayat
persiapan, bukan keadaan terakhir. Ini tidak memberi kredit Auth/browser,
analisis pabrik lengkap, audit independen atau produksi kepada Native6.
