# Checkpoint keluarga 1 — P00–P02

**Untuk Sol / auditor independen.** Status: fondasi dengan cakupan di bawah lulus T1 writer; independent acceptance **BELUM**. CP6 tetap CLOSED sesuai kontrak yang diterima. `production_go=false`.

## Kandidat yang diperiksa

- Kode: [`735056db3b42cc7fc3999149b42e2cadac7b42b2`](https://github.com/Hanjay6688/-erp-garment-ux/commit/735056db3b42cc7fc3999149b42e2cadac7b42b2).
- Tree: `a1d59c31b67deb0ba3c815784d9d5d8b6bcd191e`.
- [Run native](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36505788525): **10 database, 4 concurrency, 2 real Auth/HTTP — semua PASS**.
- [Run aplikasi](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36505793360): tests, build, security, browser cangkang dan dua bahasa CodeQL lulus. Browser ini bukan R10 connected.
- [Receipt lengkap](evidence/p02-facade/VERIFICATION.json), [laporan asli terkompresi](evidence/p02-facade/CP7_P02_FACADE.json.gz), [laporan sebelum perbaikan waktu](evidence/p02-facade/CP7_P02_BEFORE_CLOCK.json.gz).
- Commit dokumentasi sesudah kandidat tidak memindahkan label tes ke kode berbeda: cocokkan hash tiap source/test/workflow di receipt. P03 yang sedang dikerjakan adalah delta keluarga berikutnya.

## Yang diserahkan

P00: accepted CP6 receipt, katalog efektif dan framework/rusuk/cangkang asli. P01: kontrak, oracle, batas permission dan nilai UNKNOWN. P02: capture berizin melalui server, fakta dan dependency tersimpan atomik, halaman immutable, replay, deteksi perubahan sumber, pencabutan akses dan penolakan hasil parsial.

Cakupan capture: satu physical root/exact size; lima domain operasional dan lot cost hanya bila berizin; CURRENT; maksimal 500 fakta/domain, 100/halaman. Cutting masih kandidat belum terikat. Ini belum engine WIP/forecast, seluruh sumber ERP, arbitrary AS_KNOWN/RESTATED, atau UI operasional tersambung.

## Bukti penting untuk diperiksa

1. Fakta dua child cutting 6+7, gerakan FG9, draft2, cost UNKNOWN; tidak ada mutasi bisnis.
2. Dua belas capture saat 30 perubahan stok/sale serentak hanya menghasilkan pasangan utuh (9,2) atau (12,5).
3. Request duplikat menghasilkan satu run; pencabutan akses saat menunggu menolak tanpa run parsial.
4. Ops tidak mengumpulkan/menyimpan biaya. Perubahan biaya tidak bocor melalui hash/status stale. Hak finansial baru membutuhkan capture baru; hak dicabut langsung meredaksi/menolak.
5. Data backdate/insert/delete/status/recost mengubah stale yang relevan, arsip tetap utuh.
6. Source 1/101/500 baris dibaca lengkap; 501 ditolak. Angka profil ada di receipt, bukan klaim SLA produksi.
7. Principal compute tidak dapat menulis domain atau memanggil mutator, sekalipun JWT aktor punya hak luas. Private tables tidak tersedia untuk authenticated.
8. Pemulihan CP6, batas primary database, cleanup role/session dan advisor delta lulus. Ada kelas INFO RLS private tanpa policy yang dijelaskan; tidak mengklaim zero finding universal.

## Kegagalan yang sudah diselesaikan

- Fixture role huruf kecil melanggar constraint uppercase: diperbaiki pada fixture, aturan produk tetap.
- **Bug produk waktu capture:** transaksi yang masuk saat menunggu request lock terlewat karena cutoff memakai waktu awal request. Before run `36505409042` menghasilkan [2], oracle [2,3]. Cutoff sekarang ditetapkan sekali saat pengambilan fakta setelah antrean; kasus identik lulus pada kandidat ini. Harness before menyebut INCOMPLETE; adjudikasi writer adalah PRODUCT_DEFECT.

## Arahan audit

Kunci oracle dari backbone/rusuk dahulu, lalu periksa source kandidat. Jalankan probe sendiri untuk snapshot saat antrean, revoked role/replay, kebocoran biaya lewat metadata, jumlah halaman, duplikat request dan larangan mutasi. Gunakan database sementara; jangan mengubah branch writer atau hosted.

Laporkan ACCEPT/HOLD/INCOMPLETE dengan cakupan, SHA, expected/actual, artifact dan akar masalah. Jangan menutup seluruh E09/E14/E15/E20/E22/X09 dari subset di atas: report/apply, shared capacity, historical knowledge dan browser connected tetap perlu bukti saat paket pemiliknya dibuat. R10 tetap P11; gajian/Nota mandor tetap P12. T2/P20/P21 tetap wajib.

Writer melanjutkan keluarga 2 P03–P04 sesuai instruksi owner. Temuan material yang merusak dependency harus diperbaiki sebelum hasil berikutnya bergantung padanya. Tidak ada klaim auditor sudah menerima checkpoint ini.
