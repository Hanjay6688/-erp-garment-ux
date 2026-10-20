# Uji ulang r6 CP1–CP7 — untuk Fable

Owner menyalin **seluruh isi kotak di bawah** ke sesi Fable. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Fable, auditor independen. Ini UJI ULANG PUTARAN r6 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r5 17fa2507 (audit/fable_cp17_r5/, cabang audit/fable-cp1-7-r5-17fa2507-20261019,
kunci 2e3d5b38; tidak ada temuan baru; oracle D16-1 tetap ditutup; R5-02 "jawaban sama" bertahan di probe-mu sendiri;
R5-01 diperbaiki tanpa melonggarkan; catatan alatmu FABLE-R5-TOOL-01..03). Di r6 penulis menguatkan kasus R5 sesuai usulan Sol, membangun penerusan
pengingat ke WhatsApp owner atas keputusan owner D17-3..D17-7, dan menyambungkan titik pesan ulang barang jadi, kain dan
aksesori ke data ERP dan ke WhatsApp atas D17-8..D17-12 (aksesori memakai batas minimum, tanpa rumus). Ini pemeriksaan terakhir sebelum CP7C (CP7C tetap ditahan,
D13-9a). Fable, Astra dan Sol menguji ulang kandidat yang sama secara terpisah.
KANDIDAT
- Commit 55c885d1a12336905e433e05852b99be4d933f74, tree 80622a93bbbd2fb6295546aa00f1dc5eb919d827. Basis r5: 17fa25075ba77f0853c3c16f504288ace03eec35
  (tree 65f778479093d869a3354c0b9f19b4d9a541d98a). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only 55c885d1a12336905e433e05852b99be4d933f74 origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
  Kandidat r6 sebelumnya tidak dikirim: b1649535 (owner meminta rumus stok disambungkan dulu, D17-9) dan 3b7bb381 (owner
  memutuskan aksesori memakai batas minimum dan kain satu judul pengingat, D17-10..D17-12; bedanya:
  git diff --stat 3b7bb381 55c885d1 -- src supabase scripts tests .github).
- supabase/ tidak berubah sejak 17fa2507. Yang berubah: src/ (layar Reminder tab Pengingat sistem dan Sambungan WhatsApp;
  panel Titik pesan ulang / Batas minimum aksesori di Ringkasan Barang Jadi, Bahan & Roll, Aksesori, Kain & Benchmark,
  Aksesori & Harga Mandor), scripts/ (modul cp7_alert_native dan cp7_stock_formula, pemasang, kasus WA dan stok, server CallMeBot palsu, pemeriksa
  repo, kasus R5) dan workflow baru .github/workflows/claude-wa-forward.yml:
  git diff --stat 17fa25075ba77f0853c3c16f504288ace03eec35 55c885d1a12336905e433e05852b99be4d933f74 -- src supabase scripts tests .github.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-r6-20261019/CI_RECEIPT.json (semua run dan job pada kandidat; ringkasan di
  README.md bagian Kandidat; run merah dibandingkan di RED_RUNS_VS_R6.json); docs/cp7/cp17/CP17_FIXES.json (345 kasus CP17)
  dan docs/cp7/wa/WA_FORWARD.json (58 kasus WA dan stok minimum), keduanya dideklarasikan sebelum dijalankan. Run, job dan
  kasus disebut terpisah.
- Paket: docs/cp7/audit-candidate/cp1-7-r6-20261019/ (README.md per butir R6-01..R6-03, CROSS_AUDIT.md audit silang penulis
  atas ketiga laporan r5). Isinya titik awal penulis, bukan bukti lulus.

KEPUTUSAN OWNER BARU (kutipan persis di docs/cp7/OWNER_DECISIONS_20261008.md, D17-3..D17-12): "yaudah desain callmebot
buat gw"; "gw maunya tiap kena safety stock dll auto kirim terus, yg sehari 2kali itu juga mau kan ringkasan"; "bukan cuma
itu, semua hal yg masuk ke reminder harus langsung forward wa biar realtime"; "ya boleh pake yg palsu" (D17-3..D17-6);
"Ya 4 jam, tapi kan analisis jalan tiap terjadi sesuatu di background kan? Atau gimana sih" (D17-7: analisis otomatis bawaan
240 menit); "Bro masalahnya safety stock buat barang jadi kan bakal adjust terus dan angkanya kan snap shot kan, setiap ada
perubahan dia baru hitung ulang safety stock kan? Itu bakal jalan di background simple. Jadi kalo kena safety stok itu ya
sama aja kek hitungan safety stock barang mentah dong?? Semua kan pake rumus kalo kita punya barang, gimana dah?" (D17-8);
"Lama kirim supplier cenderung gak ada data ke record pula" dan "Konek in lah rumus rumus itu penting loh, kenapa writer gak
hubungi itu sama sekali ya??" (D17-9, usulan docs/cp7/wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md disetujui); "aksesoris
pake batas minimum manual aja nanti gw kasih tau ke lu minimal order tuh berapa pcs dan lama kirim dari cina ya. tar bantu
hitungin stok minimum harus berapa. ini karena harus bulk order moq rumus ga penting keknya. lalu untuk judul itu merge aja
yg stok menipis atau di bawah minimum" (D17-10); "ya" lalu "erp lama mah gada datanya orang ini pertama kali wkwk" (D17-11:
ERP lama boleh dibaca dengan SELECT saja; pemakaian aksesori tidak ada di sana); "itu nanti lu bikin slot untuk diisi aja in
app kan?" (D17-12: isian per aksesori di aplikasi). Nomor dan kunci
diisi owner sendiri di layar saat pemasangan, tidak lewat chat; uji hanya dengan server palsu. Keputusan yang sudah
disahkan tidak dibuka ulang; uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu → klaim penulis; uji dengan kasusmu sendiri, angka dan hasil yang kamu harapkan tidak diganti)
- Tidak ada temuanmu yang terbuka dari r5. FABLE-012 → tidak berubah, tetap ditunda ke CP7C (D14-9).
- Sebelum Enteng (catatanmu r5): ke-17 pemetaan akun inti harus terisi; pemakaian harian layar analisis dengan angka
  keuangan masih keputusan owner. Tidak berubah di r6.

JUGA PERIKSA (bukan temuanmu, dan regresi di sekitarnya)
- R6-01 (lima usulan penguatan uji Sol r5, bukan cacat produk): hanya scripts/cp7_r5_cases.py, id kasus sama.
  (1) baseline wajib tepat 167 identitas detektor, semuanya nol; (2) ke-11 pembaca lama dipasang bersama di erp dalam
  savepoint yang dibatalkan, jadi panggilan bersarang memakai grafik lama; (3) nilai buku persis di kedua grafik: PO 120/0/0
  → 96/24/0 → 108/12/0, siklus +24/−12, NULL untuk jurnal yang tidak ada, jawaban banyak baris dan kosong; (4) satu PREPARE
  manual lintas ganti pemetaan FG_INVENTORY dengan auto-prepare mati: 120 → 0 → 120; (5) ke-167 keluaran detektor disimpan
  per fase di kontrol. CP17 run 39385547471 pada kandidat 55c885d1: 345 kasus PASS.
- R6-02 (owner D17-3..D17-7) Pengingat sistem dan penerusan ke WhatsApp owner lewat CallMeBot: modul CP7 baru
  cp7_alert_native (scripts/cp7-src/alerts/alerts.sql, pemasang scripts/cp7_alert_bundle.py, desain
  docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md) dan layar Reminder tab Pengingat sistem dan Sambungan WhatsApp (src/waContract.ts,
  src/SystemRemindersPanel.tsx, src/WaConnectionPanel.tsx). 58 kasus dideklarasikan sebelum dijalankan untuk R6-02 dan
  R6-03 bersama (docs/cp7/wa/WA_FORWARD.json: Native 41, race 6, HTTP Auth nyata 4, browser 7; workflow "CP7 WA Forward"),
  hanya server CallMeBot palsu di CI, nomor +620000000000, kunci FAKEKEY-*. Coba patahkan:
  - kunci CallMeBot hanya di Vault: tidak pernah dijawab balik oleh RPC mana pun, tidak tersimpan di tabel, browser storage
    atau log, teks jawaban penyedia disamarkan; hanya Owner yang boleh mengatur, menguji dan menandai pesan;
  - pengingat pribadi staf tidak pernah diteruskan atau dibaca; nama pelanggan/supplier hanya di mode Rinci; Pengingat sistem
    hanya menampilkan jenis yang boleh dibaca akun itu lewat hak layar sumbernya;
  - setiap kondisi dicek ulang tepat sebelum dikirim; yang sudah beres tidak dikirim; transaksi yang dibatalkan tidak
    meninggalkan antrean; satu pesan per menit, digabung sesudah batas harian, jam tenang, ringkasan sekali per jam
    ringkasan, ulangan sesudah jeda; jawaban "ditolak" dikirim lagi sesudah jeda, jawaban "belum pasti" tidak pernah
    dikirim ulang sampai owner menandainya "tidak masuk";
  - kekurangan produksi dan kain dari analisis owner sendiri sama dengan bacaan dan cek ulang modul pengingat itu sendiri
    (aturan pengingat harus menyala); kebutuhan aksesori dari rencana produksi sengaja tidak diteruskan; jam analisis
    hanya menahan analisis otomatis yang baru; analisis otomatis bawaan tiap 240 menit (D17-7);
  - tick hanya bisa dijalankan postgres dengan batas waktu pernyataan; jadwal pg_cron dibuat tetapi tidak dipasang;
  - pemasangan sebagai postgres (bukan superuser): temuan F1/F2 di docs/cp7/wa/CP7C_INSTALL_FINDINGS_20261019.md berlaku
    untuk semua bundle CP7, modul WA sudah memakai jalan amannya.
- R6-03 (owner D17-8, D17-9, D17-10, D17-12) Titik pesan ulang dan batas minimum: modul CP7 baru cp7_stock_formula
  (scripts/cp7-src/stock-formula/formula.sql barang jadi, materials.sql kain dan aksesori; desain
  docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md), dua jenis pengingat baru FG_AT_REORDER_POINT dan ACCESSORY_AT_REORDER_POINT, kain
  berumus di pengingat lama FABRIC_BELOW_MINIMUM, panel Titik pesan ulang / Batas minimum aksesori (src/FgReorderPanel.tsx,
  src/MaterialReorderPanel.tsx). Kasus SS1_*/SS2_*/SS3_* dan WAF_* terkait ada di suite WA yang sama. Coba patahkan dengan
  pembandingmu sendiri:
  - rumus barang jadi dan kain: titik = ceil(D × L + cadangan); cadangan z × σ × √L (90/95/99%) atau D × hari penyangga
    profil perencanaan, tidak pernah keduanya; jendela hari WIB penuh (bawaan 30, sampai kemarin); hari kehabisan stok tanpa
    pemakaian bukan permintaan nol; < 14 hari terhitung atau lama kirim kosong: belum cukup data, tidak ada pengingat dan
    tidak ditebak; bahan dibulatkan ke atas 0,01; hasil yang tepatnya bulat tidak boleh naik satu (penulis memperbaiki
    pembulatan ini di kandidat, best practice E25v);
  - barang jadi: hanya penjualan POSTED yang tidak dibalik; lama produksi terukur dari potong sampai QC (median, ≥ 3
    potongan), selain itu lead_days profil; barang dalam produksi ikut posisi; angka manual menggantikan rumus, 0 = tidak
    pernah diingatkan;
  - kain: pemakaian = keluar ke potong − kembali dari potong + pemakaian pabrik + keluar ke mandor, gerakan yang dibalik tidak
    dihitung; stok semua lokasi + sisa PO terbuka; satu judul "Stok kain di bawah minimum" (D17-10): kain yang punya
    minimum di Kain & Benchmark tetap memakai aturan Ringkasan Gudang (stok < minimum), kain lain memakai rumus (stok +
    dipesan ≤ titik); satu kain tidak muncul dua kali;
  - aksesori (D17-10, D17-12): tanpa rumus; batas minimum diketik (0 = tidak pernah diingatkan) atau dihitung dari isian owner
    per aksesori: ke atas 0,01 dari perkiraan pemakaian per bulan × (lama kirim dari Cina + cadangan hari) ÷ 30; yang diketik
    menang; isian kurang dan tanpa minimum: tidak diingatkan; MOQ tidak mengubah minimum; diingatkan bila stok ≤ minimum;
    kain menolak isian ini; pemakaian nyata (nota mandor + pemakaian pabrik − retur nota yang dikreditkan layak pakai) hanya
    ditampilkan; stok hanya yang "ada di gudang" menurut Bahan & Roll (bukan pos servis, area periksa, area rusak);
  - dihitung tiap menit sekali per perintah; saat kunci modul terpegang, barang yang menipis dicek ulang ke stok saat itu
    tanpa menulis; setiap pengingat dicek ulang sebelum dikirim ke WA, yang sudah aman tidak dikirim;
  - hak: barang jadi warehouse.fg.view; kain Bahan & Roll + Kain & Benchmark; aksesori Aksesori; mengubah lama kirim, angka
    manual, isian aksesori, tingkat layanan dan jendela hanya Owner/Admin, riwayatnya tidak bisa diubah; modul pengingat hanya boleh
    memanggil fg_source() dan material_source(text); hak baca Native baru hanya kolom yang disebut desain.
- Tab Pengingat saya tetap seperti r5 (pengingat pribadi per akun, aturan pelaku OWNER/ADMIN/STAFF).
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, delta Native yang dideklarasikan hanya berlaku di dalam perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Lapisan CP7, termasuk WhatsApp, belum terpasang di Enteng (CP7C ditahan, D13-9a); tidak ada pesan atau kunci nyata.
- Kebutuhan aksesori dari rencana produksi tidak diteruskan ke WA (analisis selalu menyatakannya "belum diketahui");
  gantinya "Stok aksesori menipis" dari batas minimum. Ini beda dari usulan dan belum ada keputusan owner soal itu (desain,
  bagian "Beda dari usulan"); jangan dianggap keputusan owner. Judul kain sudah diputuskan owner (D17-10). BOM aksesori per
  warna/ukuran dan laporan aksesori mandor belum diputuskan owner; tidak dikerjakan.
- Tingkat layanan 95% belum diuji ke data penjualan owner; lama kirim kain tidak tercatat di ERP sehingga kain tanpa isian
  lama kirim tidak diingatkan rumus; aksesori tidak diingatkan sampai batas minimum atau isian hitungannya diisi di aplikasi
  (ERP lama tidak menyimpan pemakaian aksesori, D17-11).
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
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D17-12).
  Pertanyaan yang sudah dijawab owner tidak ditulis ulang sebagai terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token, kunci CallMeBot atau nomor HP di chat;
  jangan mengirim pesan WhatsApp sungguhan.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan putaran sebelumnya). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/fable-cp1-7-r6-55c885d1-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/fable_cp17_r6/RETEST_FABLE_55c885d1.md — per temuan dan per butir: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/fable_cp17_r6/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng (CP7C); daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````
