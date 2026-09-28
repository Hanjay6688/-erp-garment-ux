# BE — revisi lima temuan auditor, 28 September 2026

**CP6 HOLD.** `production_go=false`, `audit_complete=false`. Ini serah terima writer untuk retest independen; tidak menutup temuan atas nama auditor. Tidak ada perubahan production/UAT/legacy, deployment, atau merge main.

Input: `BE_WRITER_HANDOFF_20260928.md` versi 2 dan retest `BE_INDEPENDENT_AUDIT_20260928(1).md` versi 2, kandidat `e96db5a`, audit head `88534ca460435af4336cc20f489663a27f13a33e`. Temuan nominal invoice besar dalam laporan lama sudah CLOSED pada input ini; bukan lima temuan aktif di bawah.

## Kandidat dan pembagian audit

- Audit range/BF tetap memakai produk `616f4ec95b3f78d134647332885af6288d3a992a` dan `docs/cp6-bf-sku-range-handoff-20260928.md`.
- Revisi produk BE: `ec1cf2a214e3ee5513269c46757b32b4f4669743`, dilengkapi `6739a2f37939b4c76a5d064790d0aaba0049a7e8`.
- Kandidat qualification dengan paket BE selaras dan perbaikan fixture/selector: `efec399c4e2639d9ee854f34b27f8294c16a8de7`.
- Rollback yang diregenerasi dari capture: `04c88dbcb232d118ff8dd74cde246e76eaab4a1e`. Harness `a215b8aece97cfa4a94113447f905d0f780e1afe` menambah pemeriksaan inverse/replay konversi PO dan non-PO ketika kedua keluarga sumber hidup bersama; `146b3660134555f7c30df0bfc846612f5c148f4d` membetulkan pembanding penolakan legacy ke exact message + SQLSTATE. Source produk sama dengan `efec399`.
- Kandidat retest final: `231d29064b8ccf7221ad004cd8ef0017598242fc`. Uji inverse campuran memakai konversi PO tambahan yang belum dipakai; konversi PO lama yang sudah memiliki penjualan/retur tetap hidup, sesuai guard downstream. Source aplikasi, development SQL, dan paket release tetap identik dengan `efec399`.
- **Qualification writer selesai: lima temuan siap retest auditor pada `231d290`.** Run `36378513772`/job `108789168846`: native **63 PASS**, race **20 PASS**, HTTP **8 PASS**, browser **25 PASS**; tanpa FAIL/INCOMPLETE atau kasus hilang. Primary disposable tetap sama dan clone sudah dibuang. Hasil ini termasuk regresi BF/BD/BE; bukan penutupan empat gap range yang disebut di akhir dokumen.
- Pada kandidat final yang sama: Build UX `36378513769` PASS, CodeQL `36378513758` keempat bahasa PASS, BE T1 `36378513811` PASS. Package dan rollback memakai source/SQL yang sama dengan kandidat final: package `36377094023` PASS, rollback `36377504800` **143 pemeriksaan PASS**.
- Bukti utama: `docs/evidence/cp6-be/231d290.json`. Commit sesudah kandidat final hanya mengunci dokumen/bukti; tidak mengubah produk yang diuji.

## Perubahan dan dampak yang harus diuji ulang

| ID auditor | Perubahan | Sambungan / oracle retest |
|---|---|---|
| OWN-BE-01 | Komponen CONVERSION boleh bertanda negatif hanya bila cocok dengan allocation dan sumber recovery asli. HPP akhir barang tetap tidak boleh negatif. Trigger memeriksa sumber, lot, kuantitas, total, dan nilai unit. | Empat kombinasi PO/non-PO × tanpa/dengan aksesori baru. Dari 5 PCS yang dikonversi dan 1 sudah terjual, recovery 2 × 7,13 menurunkan FG 11,41 dan COGS 2,85; bukan pendapatan tambahan. Hanya 2 aksesori usable kembali ke stok; 2 masih outstanding. Replay, inverse, snapshot penjualan, dan penolakan recovery melebihi nilai barang. |
| OWN-BE-02 | Buku non-PO hanya mengakui jurnal konversi yang sumbernya non-PO, termasuk saat membaca jurnal reversal. Jurnal historis tidak ditulis ulang. | PO dan non-PO dengan produk sumber/tujuan yang sama tetap hidup bersama: konversi 5 non-PO, 3 PO, 1 non-PO, penjualan, retur, invoice PO terlambat dan inverse, alokasi kain kantong dan inverse, kemudian inverse/replay konversi PO serta non-PO. Target HPP non-PO harus tetap sama dengan buku setelah setiap sambungan. |
| OWN-BE-04 | Riwayat alokasi kain kantong memiliki pencarian ID/tanggal dan halaman berikutnya, 50 baris per halaman. Tanggal di dalam rentang periode juga cocok. Form draft tetap ada saat memuat halaman berikutnya. | Satu periode aktif lama + 51 periode baru yang sudah dibatalkan. Temukan periode lama lewat halaman kedua, tanggal, dan ID; batalkan dari browser. Inverse tepat WIP −5,62, FG −3,38, COGS −2,25, beban +11,25; tidak membuat gerakan stok kain lagi. |
| OWN-BE-05 | Order rework/rewash umum baru tanpa lineage PO/produk ditolak sebelum dispatch, dengan alasan `BE_NONPO_REWORK_UNSUPPORTED`. UI menjelaskan jalur penerimaan perbaikan non-PO. | Tidak terbentuk order setengah jadi. AX repair tetap bisa menerima 2 PCS dan mengonversi 1 PCS. Cabang CANCEL order yang sudah ada tidak dihapus. Dukungan GOOD completion generic non-PO tidak diklaim. |
| RELATED-01 | Facade public pembatalan hasil jahit menerima expected version lewat overload empat argumen. Identitas tiga argumen dipertahankan untuk rollback exact; panggilan lama menolak versi yang tidak diberikan secara jelas. | Owner/admin, stale version, dependency alokasi kain kantong aktif, pembatalan setelah dependency dibatalkan, replay UUID sekali, anon/warehouse, pencabutan akses sesudah UUID tersimpan. |

## Lokasi implementasi

- `scripts/cp6_be_objects_revision.sql`: guard biaya recovery, pencarian/pagination periode, dua signature facade pembatalan jahit.
- `scripts/cp6_be_build.py`: batas jurnal non-PO, penolakan awal rework, registry replacement dan grants; `scripts/cp6_be_pocket_build.py`: workspace memakai halaman periode yang sama.
- `src/ConnectedPocketFabricPage.tsx`: pencarian/halaman berikutnya dengan pembatalan stale reads dan draft tetap tersimpan.
- `src/ConnectedBsResolutionPage.tsx`: penolakan UI untuk lineage yang belum didukung.
- `scripts/cp6_be_revision_probe.py`, `cp6_be_revision_modes.py`, `cp6_be_revision_browser.mjs`, `cp6_be_revision_browser_fixture.py`: oracle baru dan gabungan regresi BF/BD/BE.
- `supabase/dev/cp6_be_t1_family.sql` SHA-256: `695475db3719617bd2c10d82c4dee2eaa567f4c10f322697a1714b17b60d29f6`.
- `supabase/release/cp6-t3-src/` dan `supabase/release/cp6-t3/`: BE yang sama dengan pins dari capture disposable. Regenerasi rollback memakai capture katalog, bukan mengganti hash tanpa pengujian.

## Bukti writer dan riwayat koreksi

- Lokal pada produk `6739a2f`: 52 file / 574 unit test PASS; `npm run build` dan `npm run test:security` PASS. Pemeriksaan generator BE/BF dan diff whitespace PASS.
- Build UX resmi run `36376468987` PASS, termasuk contract browser yang sudah menjadi gate dan deployment dry-run. CodeQL run `36376469032` PASS. BE T1 run `36376468955` PASS.
- Kandidat pertama `ec1cf2a`, scenario run `36375883826`: native 57 PASS / 1 FAIL / 5 INCOMPLETE, race 20 PASS, HTTP 7 PASS / 1 FAIL, browser 24 PASS / 1 INCOMPLETE. Ini bukan kelulusan. Lima recovery tertahan pada izin schema fixture native; dua refusal dibandingkan dengan potongan pesan alih-alih prefix lengkap; HTTP owner guard P0001 memang memakai status 400 dengan pesan spesifik; pencarian browser sempat cocok dengan tombol Cari di header.
- Fixture native sekarang mengembalikan grant sementara yang diperlukan oleh prerequisite penjualan, seperti probe BE yang sudah ada. Grant ini tidak dipakai pada pengujian HTTP. Selector browser dibatasi pada form kain kantong. Oracle nilai, stok, replay, dan inverse tidak dilonggarkan.
- Pada `efec399`, scenario `36377094059`/job `108785042643`: native 62 PASS / 1 FAIL, race 20 PASS, HTTP 8 PASS, browser 25 PASS; tidak ada INCOMPLETE. Semua empat recovery dan penolakan nilai berlebih lolos. Satu FAIL berisi dua pesan refusal yang tepat, tetapi helper `b.refused` mengharapkan kode simbolik; memberikan kalimat lengkap tetap tidak cocok dengan hasil `code_of`. Revisi `146b366` memeriksa kedua kalimat legacy secara persis dengan SQLSTATE P0001, tanpa mengubah helper umum atau server. Hasil lama tetap dicatat FAIL di `docs/evidence/cp6-be/efec399.json`.
- Perluasan inverse pada `a215b8a`, run `36377734592`/job `108786918027`: native 61 PASS / 1 FAIL / 1 INCOMPLETE; race 20, HTTP 8, browser 25 PASS. INCOMPLETE berasal dari percobaan membatalkan konversi PO yang masih memiliki transaksi jual/retur aktif. Server menolak dengan guard downstream yang benar. `231d290` memperbaiki persiapan uji dengan konversi PO lain yang belum digunakan, tetap memeriksa buku/HPP kedua asal, kuantitas kembali tepat, dan replay. Bukti kegagalan awal disimpan di `docs/evidence/cp6-be/a215b8a.json`.
- `146b366`, run `36378014002`: native 62 PASS / 1 INCOMPLETE, race 20, HTTP 8, browser 25 PASS. Exact message + SQLSTATE sudah lolos; hanya persiapan inverse konversi terpakai di atas yang masih tertahan. Bukti tetap disimpan di `docs/evidence/cp6-be/146b366.json`. Pada `231d290` kedua perbaikan harness bersama-sama sudah lolos.
- Capture run `36376468953` sudah berhasil memasang 29 file dan memverifikasi source AW..BE; job merah karena paket BE yang saat itu masih lama. Paket baru dibangun dari `docs/evidence/cp6-t3/be_revision_pins_36376468953.json` lalu dimasukkan ke `efec399` untuk diuji ulang.
- Pada `efec399`: Build UX `36377094084` PASS dan CodeQL `36377094033` empat job PASS; BE T1 `36377094085` PASS. Package run `36377094023` ketiga job PASS: 29 file terpasang, source AW..BE cocok, pins hasil capture ulang identik, backup/restore `RESTORED_SAME_MEANING`, dan 10 kasus browser paket PASS tanpa console error. Primary disposable tetap sama dan Auth seed dibersihkan.
- Advisor paket tetap berstatus `REVIEW_REQUIRED`: 73 temuan baseline menjadi 205, tambahan berupa INFO `rls_enabled_no_policy` pada tabel private `erp`. Gate yang sudah ada menerima kelas temuan ini; bukan klaim nol temuan keamanan atau penutupan audit.
- Rollback capture `36377094040`/job `108785042337` berhasil, digest payload `31d5874daac4a872f01d1d310f1f2dfee0355c651d2b41f8471476d8804407d4`. BE menambah 305 objek, tidak menghapus identitas lama; builder memverifikasi setiap perubahan yang boleh dipulihkan. AW..BD hanya berubah komentar digest capture; perubahan BE memulihkan constraint biaya lama dan menghapus trigger/facade baru dengan urutan yang tepat.
- Rollback cycle `36377504800`/job `108786249333` pada `04c88db`: **143 pemeriksaan PASS**, termasuk dua siklus restore/reinstall exact, penolakan urutan/admission salah, serta penolakan pascapemakaian untuk setiap file AC..BE tanpa perubahan data. Primary disposable tidak berubah. Bukti: `docs/evidence/cp6-be/rollback_04c88db.json`; bukti package: `docs/evidence/cp6-be/package_efec399.json`.

## Batas penutupan

Auditor perlu menjalankan ulang lima temuan terhadap kandidat BE final. Kelulusan writer, CodeQL, dan rollback tidak menggantikan keputusan auditor. HP fisik belum diuji. Tidak ada verifikasi data bisnis live atau klaim migration production selesai.

Empat sambungan range yang tetap terbuka untuk audit/perbaikan BF: recipe pin PO legacy ketika anggota berubah; perubahan anggota 31–33 menjadi 31–34 dengan stok/transaksi nyata; rework memakai tarif SKU lintas kontraktor dan inverse; integrasi override SKU pada jalur celup ulang BE. Revisi lima temuan BE ini tidak menutup empat sambungan tersebut maupun HOLD CP6 yang diwariskan.
