# Perlindungan kualifikasi saat runner terputus

Audit membaca byte asli 352 definisi workflow pada tree SKU
`3317ba38` dan 6 definisi pada `main` `a58385e4`. Pemindaian mencari
perintah `supabase start` literal. Cakupannya 331 job pada tree SKU
serta 5 pada `main`, termasuk definisi historis. Satu job memuat unggahan
checkpoint bernama eksplisit sebelum database. Delapan jalur CP7 memakai
penjaga stop database yang perlu diperbarui saat diadopsi lagi. Workflow
Mandor pada head aktif `e63c7589` juga diperiksa terpisah.

## Celah yang direproduksi

Lima implementasi asli mengizinkan `--allow-database-stop` dengan laporan
worker dari run, attempt, dan commit lain. Lima-limanya juga mengizinkan
stop saat laporan hilang. Afui, Mandor dan SKU memakai versi turunan dari
implementasi yang sama. Reproduksi hanya memanggil pemeriksaan izin pada
fixture lokal. Dua shutdown SKU yang sudah tercatat belum menunjukkan bahwa
celah ini menyebabkan runner dihentikan.

## Perbaikan yang siap ditinjau

Kandidat `87c60856783395e0aa25af97b7f839538b4e2c0d` memperbarui jalur SKU.
Langkah 71 menguji guard lalu menulis receipt lokal sebelum database.
Receipt mengikat repo, job, run, attempt dan commit. Worker dan cleanup
berebut satu keputusan atomik. Cleanup bisa berjalan setelah keputusan
stop sebelum worker, atau setelah bukti terminal menunjukkan worker dan
pohon prosesnya sudah berhenti. Bukti hilang, rusak atau berasal dari run
lain menyebabkan penolakan. Proses yang sudah berhenti tetap memerlukan
pemeriksaan pemulihan dan arsip asli untuk memperoleh kredit kualifikasi.

36 kontrol lokal lulus, termasuk 13 kontrol guard. Simulasi SIGKILL memakai
proses sungguhan. Pengujian supervisor asli juga menerima SIGTERM lokal,
mencatat hasil INCOMPLETE dan menunjukkan pohon proses kosong. Satu kelas
uji parent penuh masih memerlukan checkout Git lengkap. Workflow yang
diturunkan tetap 83 langkah dan hanya perintah langkah 71 yang berubah.
Pencocokan 93 pin sumber dan validasi template lulus.

## Penerapan di kandidat berikutnya

Jalankan kontrol guard dan tulis receipt sebelum mulai database. Gunakan
`claim_worker()` sebelum supervisor mulai, `finish()` pada laporan terminal
asli, dan `authorize_stop()` pada cleanup. Pertahankan checkpoint awal dengan
nama yang berbeda dari arsip akhir. Untuk pipeline baru, jalankan audit
workflow pada tree kandidat yang tepat dan cek titik start, cleanup dan
unggah arsip. Tiga job database di `main` memiliki pembatalan otomatis untuk
job yang sedang berjalan. Inventaris mencatatnya untuk ditinjau ketika
masing-masing alur mendapat perubahan yang diotorisasi.

Hasil ini disimpan untuk review. Global masih tertutup dan sumber SKU baru
sudah dibandingkan pada 216 path tanpa benturan dengan baseline Global.
Shutdown penyedia runner masih bisa menghentikan job. Jika itu terjadi,
checkpoint awal membantu diagnosis dan status lulus tetap menunggu bukti
terminal dari run yang sama.

[Perbandingan kandidat](https://github.com/Hanjay6688/-erp-garment-ux/compare/6a087cec56aed0e0e4bec4ea8ba2132d573e8f7e...87c60856783395e0aa25af97b7f839538b4e2c0d)
