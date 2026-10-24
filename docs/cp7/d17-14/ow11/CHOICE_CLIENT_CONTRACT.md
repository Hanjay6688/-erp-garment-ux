# Client konfirmasi pembanding

Form opt-in `choiceReview` pada NativeProductAnalogPanel. Parent belum menyalakan
prop ini. Database Native6 qualified714d66f5; transport10 serta browser nyata belum
selesai saat kontrak ini ditulis. Forecast tidak dipakai dan target tidak berubah.

- Pilih kandidat yang sedang terlihat, skala positif eksplisit, alasan, dan checkbox
  pemeriksaan. Tidak ada kandidat/skala/reason/review default.
- Baca revisi dan epoch saat ini. Konfirmasi memakai identitas actor,target,request,
  run,query,kedua clock,producer/history/source/profile persis; CLEAR dapat memakai
  workspace terbaru tanpa memerlukan snapshot lama.
- Catatan localStorage berversi terpisah perproject/actor/target, typed command dan
  proof minimal. Simpan sebelum RPC; jika penyimpanan perangkat atau lock browser
  gagal, jangan kirim. Kunci browser memakai productionLockName(scope) existing.
- Hasil hilang atau response salah tetap uncertain; UUID/payload/proof tidak diganti.
  Buka ulang halaman lalu tombol rekonsiliasi mengirim command sama. Refusal replay
  termasuk revoked tidak menghapus bukti yang mungkin pernah committed.
- Hanya refusal database pertama yang pasti boleh melepas command. Auth selalu
  diputuskan server; UI permission hanya affordance. Balasan terlambat setelah
  unmount/target/tab berubah tidak boleh menghapus command atau menampilkan sukses.
- Setelah receipt valid, kosongkan hanya command persis yang diakui; baca workspace
  terbaru secara terpisah. Receipt revisi lama setelah koreksi tetap receipt lama.
- 20 pasangan registry pending adalah proposal kepada A, bukan perubahan checker.
  Reader sebelumnya tetap read-only ketika prop tidak disediakan.

Validasi lokal62/62: parser/decimal/clock/identity, reply loss+reload+exact replay,
revoked replay, first definite rollback, malformed success, storage failure,
lock absence, cross-tab late result, corrupted/foreign storage, reader-only,
serta regresi quantity/advisory. TS dan CSS64 PASS. Bukti DOM bukan Auth/browser.
