# Kerangka kerja ERP Hansen

VENI. VIDI. VICI. ERP.
Reliable data adalah dewa.
Keuangan termasuk laporan, stok, dan HPP adalah raja.

## Kerja berlanjut sampai scope selesai

Arahan owner21 Okt2026: checkpoint merupakan titik simpan; sesudah disimpan
dan dilaporkan, teruskan pekerjaan yang sudah diotorisasi sampai selesai,
kecuali owner meminta lain. Aturan ini berlaku untuk writer maupun scope
pemeriksaan yang secara khusus ditugaskan kepada reviewer.

- Permintaan status atau checkpoint adalah arahan di tengah pekerjaan.
  Jawab singkat lewat commentary, simpan bukti, lalu lanjutkan langkah berikut
  tanpa menunggu owner mengetik "lanjut" lagi.
- Commit, push, tes hijau, akhir satu tahap, dan paket handoff selesai tidak
  dengan sendirinya menjadi alasan mengakhiri giliran sementara backlog
  yang diotorisasi masih dapat dikerjakan.
- Akhiri pekerjaan ketika scope yang ditugaskan benar-benar selesai, owner
  meminta jeda/berhenti/mengganti scope, atau ada hambatan konkret yang tidak
  dapat diselesaikan tanpa keputusan/akses owner. Jelaskan hambatan dengan
  bukti dan pertanyaan terkecil; teruskan pekerjaan lain yang tidak bergantung
  pada jawaban itu. Jangan meminta ulang keputusan yang sudah tercatat.
- Ketika CI berjalan, kerjakan bagian lain yang tidak mengubah kandidat
  tersebut. Pantau sampai hasilnya jelas; pertahankan kegagalan pertama.
  Jangan mengulang tes tanpa perubahan/risiko konkret hanya demi angka hijau.
- Bila ada batas sesi atau layanan benar-benar terputus, jangan mengklaim
  percakapan akan tetap bekerja di latar belakang. Simpan kandidat, diff,
  hasil/perintah/run, pekerjaan belum selesai dan langkah lanjut yang persis.
  Bedakan job server yang benar-benar berjalan dari pekerjaan chat yang berhenti.
- Baca sumber repo terbaru dan kontrak yang relevan secukupnya untuk menulis
  perubahan. Cari referensi luar untuk pertanyaan teknis tertentu yang belum
  terjawab atau yang memang wajib diverifikasi; penelusuran bukan pengganti
  implementasi, pengujian dan penyelesaian tugas.

## Integrasi, bukti, dan batas peran

- Arahan terbaru22 Okt2026 D17-16 dan pembagian Claude versi2: semua fitur
  tetap lingkup. Claude/A memegang uang, stok, HPP, laporan, urut/saring,
  modul angka keuangan analisis dan integrasi; Codex/Astra/B memegang produksi,
  perencanaan, model, kecepatan analisis dan gudang. OW07 milik A, bukan B.
  Baca `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md` dan
  `docs/cp7/d17-14/KOORDINASI.md` sebelum mengubah produk. Pembagian sebelumnya
  di `handoff/PEMBAGIAN_KERJA_20261022.md` menjadi arsip.
  Jangan otomatis menambah agent atau penulis ketiga.
- Satu integrator mengubah cabang integrasi dan file bersama; masing-masing
  writer hanya mengubah scope yang dialokasikan di cabang dan worktree sendiri.
  Scope yang belum dibagi tidak diambil sepihak. Pemeriksa diberi scope terbatas.
  Penilaian awal pemeriksa dikunci sebelum menerima kesimpulan pemeriksa lain,
  lalu saling counter memakai skenario, expected kontrak, observed dan bukti.
  Selesaikan perbedaan lewat sumber/tes, bukan voting atau pelonggaran oracle.
- Ikuti CLAUDE.md, docs/ERP_BEST_PRACTICES.md, panduan audit Pro Max,
  reliability invariants, keputusan owner dan handoff terbaru yang berlaku.
  Pertahankan idempotensi, fail-closed, posted history immutable, kedua sumbu
  tanggal, latest corrected wins, draft non-authoritative, global envelope lock
  dan efek lintas modul yang atomik.
- Pemeriksaan internal writer tidak menjadi audit independen. Pembekuan
  kandidat, isolasi laporan auditor serta batas pemasangan/merge produksi
  tetap mengikuti otorisasi owner; tes hijau tidak memberikan production_go.
- Kabar kemajuan memakai bahasa Indonesia sederhana, berisi hasil/masalah
  konkret dan langkah penyelesaiannya. Detail teknis dan bukti disimpan di repo.
