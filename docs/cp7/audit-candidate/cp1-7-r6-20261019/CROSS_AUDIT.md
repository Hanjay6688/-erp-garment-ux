# Audit silang r5 dan rencana r6 (ditulis penulis sesudah ketiga laporan r5 dikunci)

Laporan r5 yang sudah dikunci atas kandidat `17fa2507`:

| Auditor | Cabang / kunci | Vonis |
|---|---|---|
| Fable | `audit/fable-cp1-7-r5-17fa2507-20261019`, kunci `2e3d5b38` (`audit/fable_cp17_r5/`) | Tidak ada temuan baru; oracle D16-1 tetap ditutup; R5-02 "jawaban sama" bertahan (probe Fable sendiri: 17 jawaban dasar, 8 PO dalam satu query, REMAP 16 dari 17 kunci inti, NULL/DELETE/RENAME ditolak); R5-01 diperbaiki tanpa melonggarkan; latensi seperti diungkapkan (browser 100 target dengan angka 2,84/2,87/3,25 detik). Catatan alat Fable sendiri FABLE-R5-TOOL-01..03. Sebelum Enteng: ke-17 pemetaan akun inti harus terisi; keputusan owner soal pemakaian harian layar analisis dengan angka keuangan |
| Astra | `audit/astra-cp1-7-r5-17fa2507-20261019`, kunci `ff9fc3da` (`audit/astra_cp17_r5/`) | FUNCTIONAL_RETEST_PASS_WITH_EVIDENCE_LIMITS_LATENCY_OPEN: tidak ada temuan baru; SOL-R4-001 ditutup dengan kasus Astra sendiri; 396 slot cakupan PASS (2 INCOMPLETE alat Astra dikualifikasi ulang); KNOWN-P19-DIRECT-LATENCY terbuka S2 (100 target 1,88–2,19 detik, 300 target 6,57–7,75 detik di run Astra); belum diperiksa: iPad fisik dan WA langsung |
| Sol | `audit/sol-cp1-7-r5-17fa2507-20261019`, segel `8f414e96` (`audit/sol_cp17_r5/`) | FINAL_SOL_R5_BOUNDED_RETEST_COMPLETE_FULL_CP17_HOLD: tidak ada temuan produk baru; SOL-R4-001 ditutup di kandidat terpasang (167 detektor nol melalui sumber, DRAFT, POST, pembalikan dan pengganti; pemeriksa lama +2; upah salah dan upah hilang tepat +1, rollback 0); R5-02 PASS dalam masukan yang diuji (Sol memasang ke-11 pembaca lama bersama: PO 120 → FG 96/HPP 24 → FG 108/HPP 12, siklus +24/−12, NULL/kosong/banyak baris sama); KNOWN-P19-DIRECT-LATENCY terbuka S2 (100 target dengan angka 2,98/2,94/3,45 detik); CP7 HOLD untuk batas CP7C yang sudah diputuskan |

## Per akar masalah

| Akar | Asal | Pemeriksaan keabsahan oleh penulis | Butir r6 |
|---|---|---|---|
| Kasus R5 penulis membuktikan lebih sedikit daripada yang bisa | Sol, `audit/sol_cp17_r5/WRITER_HANDOFF.md` bagian "Penguatan uji permanen" (lima butir; bukan cacat produk) | Sah: (1) baseline 167 identitas hanya dicatat, belum diwajibkan nol dan tepat 167; (2) tiap salinan pembaca lama memanggil pembaca terpasang yang ia panggil di dalamnya, jadi panggilan bersarang tidak memakai grafik lama; (3) `with_value` menerima `'0'`, jadi nilai buku yang salah tetap lulus; (4) prepared statement manual lintas ganti pemetaan belum diuji (cache psycopg berbeda); (5) kontrol tidak menyimpan ke-167 keluaran per fase | R6-01 |
| Latensi analisis langsung dengan angka keuangan | Ketiga auditor: KNOWN-P19-DIRECT-LATENCY S2 | Sah sebagai pengukuran; tidak ada perubahan produk di r6 untuk ini. 3 detik tetap tidak ditandai tercapai | tetap terbuka, diungkapkan |

## Pekerjaan baru atas keputusan owner (bukan temuan audit)

| Butir | Keputusan | Isi |
|---|---|---|
| R6-02 Pengingat sistem dan penerusan ke WhatsApp owner | D17-3..D17-7 (kutipan di `docs/cp7/OWNER_DECISIONS_20261008.md`) | Modul CP7 baru `cp7_alert_native` (`scripts/cp7-src/alerts/alerts.sql`), layar Reminder tab Pengingat sistem dan Sambungan WhatsApp, kasus yang dideklarasikan (`docs/cp7/wa/WA_FORWARD.json`; 24 di kandidat pertama `b1649535`), workflow "CP7 WA Forward". Analisis otomatis bawaan tiap 240 menit (D17-7). Hanya server CallMeBot palsu di CI; tidak ada pesan atau kunci nyata. Belum dipasang di Enteng (CP7C ditahan, D13-9a) |
| R6-03 Titik pesan ulang dengan rumus (barang jadi, kain, aksesori) | D17-8, D17-9 (usulan `docs/cp7/wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md` disetujui) | Modul CP7 baru `cp7_stock_formula` (`scripts/cp7-src/stock-formula/`), tiga jenis pengingat baru yang diteruskan ke WhatsApp dan dicek ulang sebelum dikirim, panel Titik pesan ulang di layar gudang dan Master Data, lama kirim per bahan diisi Owner/Admin. Kasus di suite WA yang sama (57 di kandidat `3b7bb381`). Desain dan tiga beda dari usulan: `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md`; dua di antaranya menunggu keputusan owner |

Batas bukti yang sama di ketiga laporan (CP7C, salinan data nyata, preflight hosted, restore CP2 penuh, cakupan 12 jalur lama,
kontrol negatif detektor INV-D01, perangkat Apple fisik, WA langsung) tetap ditahan sesuai keputusan owner; tidak dibuka
ulang.

## Keputusan owner di putaran ini

- D17-3..D17-6 (19 Okt 2026 WIB), kutipan persis di `docs/cp7/OWNER_DECISIONS_20261008.md`: "yaudah desain callmebot
  buat gw"; "gw maunya tiap kena safety stock dll auto kirim terus, yg sehari 2kali itu juga mau kan ringkasan"; "bukan
  cuma itu, semua hal yg masuk ke reminder harus langsung forward wa biar realtime"; "ya boleh pake yg palsu". Jam
  ringkasan bawaan 08.00 dan 15.00 adalah isian awal penulis, bisa diubah owner di aplikasi.
- D17-7..D17-9 (20 Okt 2026 WIB), kutipan persis di berkas yang sama: analisis otomatis bawaan tiap 4 jam; titik pesan
  ulang barang jadi dihitung dengan rumus seperti bahan, dihitung ulang di belakang dan diteruskan ke WhatsApp; "Konek in lah
  rumus rumus itu penting loh, kenapa writer gak hubungi itu sama sekali ya??". Karena itu kandidat pertama `b1649535` tidak
  dikirim; paket ini kini memakai `3b7bb381`.
