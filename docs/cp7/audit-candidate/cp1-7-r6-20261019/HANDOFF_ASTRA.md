# Uji ulang r6 CP1–CP7 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Astra, auditor independen. Ini UJI ULANG PUTARAN r6 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r5 17fa2507 (audit/astra_cp17_r5/, cabang audit/astra-cp1-7-r5-17fa2507-20261019,
kunci ff9fc3da; vonis FUNCTIONAL_RETEST_PASS_WITH_EVIDENCE_LIMITS_LATENCY_OPEN: tidak ada temuan baru; 396 slot cakupan
PASS; belum diperiksa termasuk iPad fisik dan WA langsung). Di r6 penulis menguatkan kasus R5 sesuai usulan Sol dan membangun penerusan
pengingat ke WhatsApp owner atas keputusan owner D17-3..D17-6. Ini pemeriksaan terakhir sebelum CP7C (CP7C tetap ditahan,
D13-9a). Fable, Astra dan Sol menguji ulang kandidat yang sama secara terpisah.
KANDIDAT
- Commit b1649535c42e9d8641a1128b02e60c23093a0685, tree 954d3ef3c9cbf544cfd66d6f8ddb49d8fd243329. Basis r5: 17fa25075ba77f0853c3c16f504288ace03eec35
  (tree 65f778479093d869a3354c0b9f19b4d9a541d98a). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only b1649535c42e9d8641a1128b02e60c23093a0685 origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- supabase/ tidak berubah sejak 17fa2507. Yang berubah: src/ (layar Reminder tab Pengingat sistem dan Sambungan WhatsApp),
  scripts/ (modul cp7_alert_native, pemasang, kasus WA, server CallMeBot palsu, pemeriksa repo, kasus R5) dan workflow baru
  .github/workflows/claude-wa-forward.yml: git diff --stat 17fa25075ba77f0853c3c16f504288ace03eec35 b1649535c42e9d8641a1128b02e60c23093a0685 -- src supabase scripts tests .github.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-r6-20261019/CI_RECEIPT.json (semua run dan job pada kandidat; ringkasan di
  README.md bagian Kandidat); docs/cp7/cp17/CP17_FIXES.json (345 kasus CP17) dan docs/cp7/wa/WA_FORWARD.json (24 kasus WA),
  keduanya dideklarasikan sebelum dijalankan. Run, job dan kasus disebut terpisah.
- Paket: docs/cp7/audit-candidate/cp1-7-r6-20261019/ (README.md per butir R6-01..R6-02, CROSS_AUDIT.md audit silang penulis
  atas ketiga laporan r5). Isinya titik awal penulis, bukan bukti lulus.

KEPUTUSAN OWNER BARU (kutipan persis di docs/cp7/OWNER_DECISIONS_20261008.md, D17-3..D17-6): "yaudah desain callmebot
buat gw"; "gw maunya tiap kena safety stock dll auto kirim terus, yg sehari 2kali itu juga mau kan ringkasan"; "bukan cuma
itu, semua hal yg masuk ke reminder harus langsung forward wa biar realtime"; "ya boleh pake yg palsu". Nomor dan kunci
diisi owner sendiri di layar saat pemasangan, tidak lewat chat; uji hanya dengan server palsu. Keputusan yang sudah
disahkan tidak dibuka ulang; uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu → klaim penulis; uji dengan kasusmu sendiri, angka dan hasil yang kamu harapkan tidak diganti)
- Tidak ada temuanmu yang terbuka dari r5. "WA langsung" yang kamu catat belum diperiksa: r6 menambahkan penerusan WA,
  tetapi tetap tanpa pesan sungguhan (server CallMeBot palsu saja, D17-6). iPad fisik tetap di luar jangkauan penulis.

JUGA PERIKSA (bukan temuanmu, dan regresi di sekitarnya)
- R6-01 (lima usulan penguatan uji Sol r5, bukan cacat produk): hanya scripts/cp7_r5_cases.py, id kasus sama.
  (1) baseline wajib tepat 167 identitas detektor, semuanya nol; (2) ke-11 pembaca lama dipasang bersama di erp dalam
  savepoint yang dibatalkan, jadi panggilan bersarang memakai grafik lama; (3) nilai buku persis di kedua grafik: PO 120/0/0
  → 96/24/0 → 108/12/0, siklus +24/−12, NULL untuk jurnal yang tidak ada, jawaban banyak baris dan kosong; (4) satu PREPARE
  manual lintas ganti pemetaan FG_INVENTORY dengan auto-prepare mati: 120 → 0 → 120; (5) ke-167 keluaran detektor disimpan
  per fase di kontrol. CP17 run 39280347023 pada 97e42575: 345 kasus PASS.
- R6-02 (owner D17-3..D17-6) Pengingat sistem dan penerusan ke WhatsApp owner lewat CallMeBot: modul CP7 baru
  cp7_alert_native (scripts/cp7-src/alerts/alerts.sql, pemasang scripts/cp7_alert_bundle.py, desain
  docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md) dan layar Reminder tab Pengingat sistem dan Sambungan WhatsApp (src/waContract.ts,
  src/SystemRemindersPanel.tsx, src/WaConnectionPanel.tsx). 24 kasus dideklarasikan sebelum dijalankan
  (docs/cp7/wa/WA_FORWARD.json: Native 15, race 4, HTTP Auth nyata 2, browser 3; workflow "CP7 WA Forward"), hanya server
  CallMeBot palsu di CI, nomor +620000000000, kunci FAKEKEY-*. Coba patahkan:
  - kunci CallMeBot hanya di Vault: tidak pernah dijawab balik oleh RPC mana pun, tidak tersimpan di tabel, browser storage
    atau log, teks jawaban penyedia disamarkan; hanya Owner yang boleh mengatur, menguji dan menandai pesan;
  - pengingat pribadi staf tidak pernah diteruskan atau dibaca; nama pelanggan/supplier hanya di mode Rinci; Pengingat sistem
    hanya menampilkan jenis yang boleh dibaca akun itu lewat hak layar sumbernya;
  - setiap kondisi dicek ulang tepat sebelum dikirim; yang sudah beres tidak dikirim; transaksi yang dibatalkan tidak
    meninggalkan antrean; satu pesan per menit, digabung sesudah batas harian, jam tenang, ringkasan sekali per jam
    ringkasan, ulangan sesudah jeda; jawaban "ditolak" dikirim lagi sesudah jeda, jawaban "belum pasti" tidak pernah
    dikirim ulang sampai owner menandainya "tidak masuk";
  - kekurangan produksi dan kain dari analisis owner sendiri sama dengan bacaan dan cek ulang modul pengingat itu sendiri
    (aturan pengingat harus menyala); kebutuhan aksesori sengaja tidak diteruskan; jam analisis hanya menahan analisis
    otomatis yang baru;
  - tick hanya bisa dijalankan postgres dengan batas waktu pernyataan; jadwal pg_cron dibuat tetapi tidak dipasang;
  - pemasangan sebagai postgres (bukan superuser): temuan F1/F2 di docs/cp7/wa/CP7C_INSTALL_FINDINGS_20261019.md berlaku
    untuk semua bundle CP7, modul WA sudah memakai jalan amannya.
- Tab Pengingat saya tetap seperti r5 (pengingat pribadi per akun, aturan pelaku OWNER/ADMIN/STAFF).
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, delta Native yang dideklarasikan hanya berlaku di dalam perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Lapisan CP7, termasuk WhatsApp, belum terpasang di Enteng (CP7C ditahan, D13-9a); tidak ada pesan atau kunci nyata.
- Kebutuhan aksesori tidak diteruskan ke WA; STOCK_AT_REORDER_POINT belum dibuat.
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- KNOWN-P19-DIRECT-LATENCY tidak diubah di r6: 100 target dengan angka keuangan sekitar 2,8–3,5 detik di browser pada run
  ketiga auditor r5; 300 target di atas 3 detik. 3 detik tidak ditandai tercapai.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain dari
  putaran ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini (ketiga laporan r5)
  boleh dibaca; audit silang penulis ada di CROSS_AUDIT.md.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun paling
  banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head sudah
  bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D17-6).
  Pertanyaan yang sudah dijawab owner tidak ditulis ulang sebagai terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token, kunci CallMeBot atau nomor HP di chat;
  jangan mengirim pesan WhatsApp sungguhan.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan putaran sebelumnya). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/astra-cp1-7-r6-b1649535-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/astra_cp17_r6/RETEST_ASTRA_b1649535.md — per temuan dan per butir: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/astra_cp17_r6/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng (CP7C); daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````
