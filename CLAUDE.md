# Aturan untuk Claude di repo ini

## Kerangka kerja berkelanjutan (owner21 Okt2026)

Baca dan ikuti `AGENTS.md`. Checkpoint disimpan dan dilaporkan, lalu pekerjaan
yang sudah diotorisasi diteruskan sampai scope selesai; permintaan status atau
checkpoint tidak menjadi alasan mengakhiri giliran dan menunggu "lanjut" lagi.

## Laporan ke owner (aturan owner, 8 Okt 2026)

Owner: "RULE BUAT CLAUDE KASIH REPORT AFTER WORK itu jelas bahasa manusia."

- Tulis dengan bahasa sehari-hari. Owner bukan programmer.
- Kalimat pertama: apa yang sudah beres dan apa yang belum. Langsung, tanpa pembukaan.
- Jangan pakai istilah teknis tanpa penjelasan (SHA, workflow, fast-forward, RPC, oracle, dan sejenisnya). Kalau terpaksa,
  jelaskan dalam satu kalimat biasa.
- Kalau butuh sesuatu dari owner, tulis jelas: "Saya perlu Bos memutuskan X: pilihan A atau B." Pertanyaan ya/tidak bila bisa.
- Jangan menyebut sesuatu sebagai "isian/tugas owner" kalau itu sebenarnya diisi di aplikasi nanti saat dipakai.
- Jangan muter-muter dan jangan mengulang hal yang sama. Laporan pendek; detail teknis taruh di dokumen, bukan di chat.

## Best practice teknis (owner 16 Okt 2026: "jadikan best practice buat erp kita")

- Saat menulis atau mengubah kode ERP, ikuti `docs/ERP_BEST_PRACTICES.md` (disusun dari temuan audit Fable, Astra, Sol).
- Jalankan daftar periksa di akhir berkas itu sebelum menyerahkan kandidat ke auditor.
- Temuan audit baru yang mengajarkan pelajaran umum ditambahkan ke berkas itu dengan ID temuannya.

## Kuota dan pembantu (owner 23 Okt 2026)

- Kerja bertahap dengan checkpoint: setiap langkah selesai langsung di-commit dan di-push, catatan posisi kerja diperbarui.
- Selama kuota sesi 5 jam masih banyak, jalan normal dan boleh banyak pembantu. Bila mulai tipis (patokan sekitar 80% terpakai),
  masuk mode hemat: jangan mulai pekerjaan baru, gabung dan push hasil yang ada. Sesudah reset, jalan normal lagi.
- Pembantu yang sudah jalan jangan dihentikan tiba-tiba ("jangan stop tiba tiba pembantu yg udah jalan"), termasuk saat mode hemat.
