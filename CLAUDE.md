# Aturan untuk Claude di repo ini

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
