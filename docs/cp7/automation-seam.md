# CP7 — pemicu analisis dan sambungan CP7C

28 September 2026. Usulan teknis dari permintaan owner agar ERP dapat belajar
pola dan bekerja di backend. **S0 saja; CP6 HOLD; accepted base null.**

`docs/cp7/prototypes/automation.ts` adalah prototipe kontrak yang dapat diuji
untuk mengusulkan urutan kerja. File berada di luar runtime aplikasi sesuai
aturan source ownership proyek; bukan backend produksi yang telah terpasang.
Ia tidak dipasang di UI, tidak membaca CP6, tidak memasang timer/cron, tidak
membuat queue, tidak menjalankan forecast/training, dan tidak mengirim pesan.
Semua hasil selalu `SHELL_ONLY` dan `operational: false`. Typed input adalah
fixture, bukan parser input tidak tepercaya atau bukti authorization server.

## Pemicu yang diusulkan

| Pemicu | Tujuan | Kapan / batas |
|---|---|---|
| Perubahan fakta committed | Snapshot konsisten → analisis bersama → observasi kondisi | Sesudah transaksi berhasil commit; draft/rollback bukan fakta posted |
| Perubahan kebijakan/BOM/kalender sah | Analisis baru sesuai dependency yang berubah | Adaptasi sumber/revision ditentukan setelah P01; bukan perubahan tersembunyi pada hasil lama |
| Jadwal refresh analisis | Periksa risiko yang berubah karena waktu berjalan | Hari/jam/timezone/quiet hours/catch-up dikonfigurasi; belum ada jadwal aktif |
| Jadwal evaluasi model | Bandingkan kandidat pada histori eligible dan periode uji | Hanya ketika ada tambahan/koreksi data yang layak; tidak setiap transaksi |
| Permintaan manual | Refresh atau evaluasi eksplisit | Hak actor diperiksa backend kelak; tidak mengaktifkan otomatisasi |

Jam harian atau hari evaluasi mingguan belum dipilih. Zona waktu rancangan
jadwal adalah Asia/Jakarta. CP7C kelak tetap berjalan ketika browser ditutup;
S0 saat ini belum menyediakan kemampuan tersebut. Status sumber, reminder,
ACK/snooze, dan status pengiriman adalah hal berbeda.

## Apa yang dibuktikan oleh tes cangkang

Sumber uncommitted dan jadwal disabled tidak mengusulkan pekerjaan. Perubahan
fakta tidak otomatis melatih model. UNKNOWN/INSUFFICIENT tidak dianggap cukup
untuk training; NO_NEW_DATA tidak memicu latihan berulang. Evaluasi model
tidak mempromosikan pemenang atau menerbitkan perintah produksi.

Identitas usulan mencakup allocation scope, versi policy/model, tujuan, serta
source+revision atau schedule+revision+occurrence. Replay fixture menghasilkan
identitas sama; koreksi, scope, atau versi berbeda tidak bertabrakan. Ini belum
membuktikan dedupe durable, penguncian dua worker, ataupun exactly-once efek.

## Pekerjaan backend yang tetap menunggu

1. Accepted CP6 + kontrak sumber/identity/izin, pemetaan dependency dan snapshot
   native yang konsisten. Satu allocation scope mencakup sumber bersama;
   filter tampilan tidak mengubah anggaran fisik.
2. Finalisasi event/outbox commit atomik atau mekanisme invalidasi setara.
   Callback browser bukan sumber kebenaran dan HTTP tidak masuk transaksi bisnis.
3. Queue durable, claim atomik, lease/fencing, retry terikat identitas,
   penggabungan perubahan tanpa kehilangan revision, dan pemeriksaan izin terbaru.
   Kejadian berulang/retry harus aman; queue delivery tidak otomatis membuktikan
   efek bisnis persis sekali.
4. Jalankan engine authoritative di backend sesuai ADR-01. Rancangan sekarang
   Postgres privat; runtime training ML lain memerlukan delta ADR yang jelas,
   profil beban, dan satu model authoritative—bukan SQL/JS beda rumus.
5. Snapshot baru menghasilkan run baru. Perubahan saat compute menandai hasil
   lama stale; worker terlambat tidak boleh menimpa pointer hasil yang lebih baru.
6. Model kandidat dievaluasi melawan baseline dengan cutoff kronologis, holdout,
   bias, risiko kehabisan/kelebihan stok dan kebutuhan modal yang datanya valid.
   Jadwal training bukan izin auto-promote. Threshold dan rollback harus eksplisit.
7. Bukti native: crash sesudah commit/sebelum ACK, replay, dua worker, revocation,
   downtime/catch-up, source out-of-order, stale result, model gagal, serta tidak
   ada domain write/delivery melalui worker analisis. Lalu acceptance CP7C.

Saldo, alokasi, ledger dan status STOP tetap mengikuti aturan sumber. Model
prediksi tidak boleh mengubah stock aktual, membuat invoice lunas, atau
menjadikan kapasitas yang belum diketahui sebagai kapasitas tersedia.

## Landasan platform

Dokumentasi Supabase saat dibaca menyediakan Cron untuk pekerjaan berjadwal
dan Queues untuk pesan durable. Ini membuktikan kapabilitas platform, bukan
bahwa extension/job/worker sudah diaktifkan pada ERP ini. Pemilihan dan
konfigurasi final masih bagian integrasi CP7C.

- https://supabase.com/docs/guides/cron
- https://supabase.com/docs/guides/queues

Tidak ada migration, deployment, kredensial, recipient WA, atau mutasi CP6
dalam tambahan S0 ini.
