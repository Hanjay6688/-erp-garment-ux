# Contoh output Business Report — data uji, bukan kondisi pabrik

Periode:1–10 Oktober2026 · run:fixture-report-v2 · scenario:fixture-S1 · knowledge:AS_KNOWN.

**Produksi yang perlu ditinjau:** SKU A, size30, punya kebutuhan dasar18 PCS. Jika10 PCS kandidat B1 cocok dan siap pada6 Oktober, kebutuhan tambahan menjadi8 PCS. FG nyata tetap18 PCS. Kapasitas pabrik belum diketahui;8 PCS ini usulan bersyarat, belum bukti produksi feasible atau sudah dipesan.

| Urutan | Tindakan | Dasar | Status |
|---|---|---|---|
| 1 | Periksa tujuan dan ETA kandidat B1 |10 PCS kandidat dipakai skenario; jangan diberikan lagi ke SKU lain | Perlu konfirmasi |
| 2 | Periksa kelayakan rencana baru8 PCS | Lead time dan buffer berasal dari fixture; capacity belum tersedia | Belum dapat apply |
| 3 | Lengkapi sumber biaya | Biaya/revenue belum ditangkap pada contoh analysis.json | Margin belum dapat dihitung |

Contoh ini memakai angka O02. Jika directed WIP mundur dari3 ke8 Oktober, gap5 Oktober2 PCS tetap harus dilaporkan walaupun saldo akhir simulasi masih8. Batch di luar skenario tidak ditambahkan diam-diam.

**Contoh laporan finansial terpisah, hanya setelah fixture E01/E03 sah:** revenue bersih375; COGS225; laba kotor150 atau40%; cash diterima200; AR175. `200+175=375` pada fixture tanpa pajak/diskon/pendapatan lain ini. Angka tidak digabung dengan O02 sebagai data satu perusahaan. Report finansial harus memuat refs transaksi dan readiness yang sudah terbukti; jika belum, tampilkan UNKNOWN/PENDING.

Panel laporan menyediakan alasan, operand, physical lot/size, commercial membership version, as-of/known cutoff, dan tautan sumber sesuai hak pengguna. Arsip menyimpan hasil ini immutable; koreksi menerbitkan revisi tertaut. Format PDF/Excel baru belum diwajibkan.
