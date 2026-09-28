# Handoff writer: SKU-01 dan RANGE-02

**CP6 HOLD.** `production_go=false`, `audit_complete=false`, `release_evidence=false`.
Writer menyiapkan patch dan bukti retest; auditor/owner tetap menentukan penutupan independen. Tidak ada deploy, merge main, atau tulisan ke production/UAT/legacy.

**Koreksi dasar bisnis, 28 September 2026 14:59 WIB:** tarif laundry berasal dari vendor/proses/paket/komponen yang dipilih; SKU final opsional dan biasanya baru muncul saat finishing. Ini aturan lama LAU-DEC05, ditegaskan ulang owner. Sebagian kasus di bawah memakai tarif master SKU sebagai oracle: PASS teknisnya tetap tercatat, tetapi **bukan bukti bahwa sumber tarif laundry sesuai aturan owner**. Jangan memakai angka125 untuk menutup kekurangan ini. Alasan R04/R05 yang mewajibkan tarif SKU telah ditarik; prioritas override BF perlu ditangani sebagai R16 pada [laporan yang dikoreksi](cp6-range-followup-20260928.md). Tidak ada kode produk atau snapshot posted yang diubah oleh koreksi laporan ini.

**Hasil akhir writer untuk cakupan terdaftar: PASS.** Kode produk `fb8fb11` mendapat bukti gabungan **67 native DB +22 race +9 real HTTP +27 kasus browser unik =125 kasus PASS**. Dua browser retest berada pada `9e04af4`, yang hanya mengubah pengujian/bukti. Ini hasil gabungan pada produk identik, bukan satu run berisi125 kasus dan bukan seluruh variasi bisnis sudah selesai.

## Kandidat dan perubahan

- `04c620954cf2b9fd25b5ba50641895b1015911c9`: perbaikan SKU-01. Parser master laundry COMPONENT mengharuskan positif hanya untuk KNOWN; FREE/WAIVED memakai nol dan alasan sah. UNKNOWN/null dan guard format nominal tetap.
- `fb8fb11217e572d8c428e3796fddc28f1a2b2903`: menambah RANGE-02. Referensi tarif wave sekarang mengambil **ukuran unik**, sehingga ukuran31 yang ada dalam dua slot gambar tidak menjadi dua referensi SKU. Memperbaiki setup dua tes race dan selector dua tes browser yang belum lengkap pada run pertama.
- `9e04af4dbcf121a056250be40645c944887b8af6`: hanya koreksi timing navigasi tes setelah reload HP, retest browser terarah, dan bukti. Kode produk sama persis dengan `fb8fb11`.
- Hash development BF pada kandidat gabungan: `e100e8f97b8531bc7dfc6ebfd352af5d3d75594887205aecaef63c6ef4aa5b60`.
- SQL product BE dan paket release BE tidak diubah. BF tetap development family; paket BE lama tidak dianggap paket rilis BF baru.

Lokasi implementasi: `scripts/cp6_bf_objects_rates.sql`, `scripts/cp6_bf_objects_router.sql`, generated `supabase/dev/cp6_bf_t1_family.sql`. Bukti baru: `cp6_bf_free_probe.py`, `cp6_bf_free_modes.py`, `cp6_bf_free_browser.mjs`, `cp6_bf_free_browser_fixture.py`, `cp6_bf_range_followup.py`, dan unit normalisasi `src/skuMaster.test.ts`.

## Hasil yang sudah tersedia

Run pertama pada `04c6209`: [36389571961](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36389571961), job108822184343.

| Lapisan | Hasil | Makna |
|---|---|---|
| Native DB | 66PASS | SKU-01 master, 9 invalid matrix +PROCESS guard, gratis sampaiQC/HPP, dan regresi BE/BF/BD yang tercantum |
| Real Auth/HTTP | 9PASS | FREE/WAIVED/KNOWN/UNKNOWN tersimpan; invalid menolak; anon/role/current-permission-before-replay benar; regresi HTTP |
| Dua sesi | 20PASS +2INCOMPLETE | Dua kasus baru salah menerapkan helper izin khusus HTTP pada race clone yang sudah memiliki grant uji; bukan PASS dan bukan bukti kegagalan transaksi produk |
| Browser | 25PASS +2INCOMPLETE | Dua kasus baru berhenti pada selector labelselectVendor; tidak dianggap lolos simpan/muat ulang |
| Build UX | PASS, run36389572048 | Build resmi dan pemeriksaan bawaan |
| CodeQL | PASS, run36389571988 | Gate source kandidat pertama |

Runtime self-test lulus; primary unchanged=true, salinan native/race/HTTP/browser dibersihkan, Auth kembali ke baseline. Bukti beserta kegagalan yang tidak disembunyikan: [04c6209.json](evidence/cp6-bf/04c6209.json).

Uji lokal: generator BF `--check`, Python/JS syntax, diffcheck; build resmi lulus. Unit terkait SKU/laundry/helperlusin:3file29testPASS. Ini bukan pengganti DB/HTTP/browser.

Kandidat gabungan `fb8fb11`: [run36390618767](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36390618767), job108825401061. **Native67PASS, races22PASS, HTTP9PASS, browser26PASS+1INCOMPLETE.** RANGE-02 lolos dengan empat slot asli/5–8–3/tiga binding/replay. FREE/WAIVED desktop simpan+reload lolos. HP berhasil menyimpan, tetapi helper tes terlalu cepat memeriksa tombol menu sebelum Auth selesai setelah reload; klik berikutnya mengenai sidebar di luar viewport. Ini tetap INCOMPLETE, bukan PASS. Build36390618814 dan CodeQL36390618670 lulus. Primary unchanged=true, seluruh salinan dibersihkan. [Bukti fb8fb11](evidence/cp6-bf/fb8fb11.json).

Retest `9e04af4` menunggu sidebar terpasang, lalu menekan tombol menu HP secara normal; tidak menggunakan force-click dan tidak mengubah produk. [Run36391872107](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36391872107), **job108829312793**, menjalankan dua kasus browser FREE/WAIVED desktop/HP: **2PASS**, termasuk simpan dan reload. Native business cases kosong pada retest ini; **jangan menghitung group kosong sebagai bukti bisnis**. Native/race/HTTP tetap merujuk hasil lengkap `fb8fb11` yang source produknya identik. Desktop diuji ulang, sehingga total browser unik tetap27, bukan28.

Installer retest memverifikasi hash BF `e100e8f97b8531bc7dfc6ebfd352af5d3d75594887205aecaef63c6ef4aa5b60` yang sama dengan run lengkap. Primary unchanged=true, clone_remaining=0, database browser dihapus, Auth kembali ke baseline, console_errors=0. Build36391872117 dan CodeQL36391872112 (empat job) lulus. Runtime self-test job108829312576 lulus; deliberate INCOMPLETE di self-test adalah alat deteksi yang diuji, bukan hasil produk. [Bukti retest dan daftar125kasus](evidence/cp6-bf/9e04af4.json).

Untuk mengulang seluruh regresi, gunakan `cp6_bf_free_modes.py` bersama `cp6_bf_free_browser.mjs`. Dispatch revision35 sengaja menunjuk retest browser saja; jangan membacanya sebagai pengganti seluruh suite pada perubahan produk berikutnya.

## Oracle bisnis yang benar-benar diperiksa

1. Satu master dengan tiga physical roots menyimpan FREE0+alasan, WAIVED0+alasan, KNOWN101,23, UNKNOWNnull. Replay hanya satu revisi.
2. FREE/WAIVED alasan hilang/spasi atau rate0,01; KNOWN0; negatif; UNKNOWN angka ditolak tanpa revisi/harga/request parsial. PROCESS tidak memperoleh jalur FREE lewat perubahan ini.
3. Satu range31–33: stok5/8/3; jahit127,19 perPCS menghasilkan635,95/1017,52/381,57, total2035,04. FREE wash mencakup16PCS; WAIVED finishing mencakup3PCS ukuran32. Laundry0, complete=true, bukan UNKNOWN, AP vendor0, laundry accrual desired0.
4. Fixture writer mempunyai kain100 dari purchase/cut normal. HPP menjadi667,20/1067,52/400,32, total2135,04, weighted133,44. Jangan menyebut total2035,04 tanpa menjelaskan kain100. Auditor dapat mengulang fixture mereka yang kainnya0 dengan oracle total2035,04.
5. Charge menyimpan status/alasan/versiSKU dan penerima ukuran; replay kirim tidak menggandakan efek. Master baru berbayar tidak mengganti biaya lot lama.
6. Dua editor dari revisi sama: commit pertama menyebabkan stale writer; rollback pertama membolehkan writer kedua. Satu revisi bisnis tetap utuh untuk seluruh anggota.
7. Browser desktop dan HP emulasi harus menyimpan kedua statusgratis, lalu muat ulang dan memperlihatkan status/alasan yang sama. HP fisik belum.
8. Potong size31 drawingA2PCS+ drawingB3PCS, size32=8,33=3: tetap4slot/16PCS tetapi3pilihanSKU/tigabinding. Payload diambil dari publicworkspace sebagaimana UI, tanpa deduplikasi tersembunyi dalamtest. Replay binding sekali; belum adaFG yang diciptakan dari sekadar referensi.

## Serah terima retest dan pekerjaan yang tetap terbuka

Audit independen ulangi SKU-01 pada kandidat gabungan, termasuk empat tahap sebelumnya BLOCKED (work/ship/receive/QC) memakai prasyarat mereka, penolakan invalid, izin/replay, browser dan race. Tambahkan RANGE-02 potong dengan drawing berulang, bukan hanya satu slot per ukuran.

Temuan dan potensi tambahan berikut terpetakan dalam [pemeriksaan range lanjutan](cp6-range-followup-20260928.md): batas dua referensi pekerjaan berukuran sama dalam satu wave; prioritas tarifSKU yang keliru terhadap aturan vendor (R16); PO sedangjalan dan anggota34; perpindahan range saatBS/rework; kodeSKU komersial versus produkfisik; penjualan connected; retur lintasrange; impor versiidentitas; paket/extra/rewash; HPP lintastanggal/lokasi. Laundry tanpa SKU dan celupulang memakai tarif vendor tidak lagi diklasifikasikan sebagai bug sumber tarif.

**Empat batas owner tetap terbuka:** penutupan independen alur gratis; seluruh variasi rework/range; paket rilis kandidat terbaru; last check CP6. Hasil writer terbatas tidak memberi izin CP7 dan tidak membuktikan data bisnis live sudah aman.
