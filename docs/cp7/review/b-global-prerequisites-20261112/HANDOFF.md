# CP7 B — celah pemeriksaan akun supplier dan prasyarat Global

12 November 2026 WIB. **Satu celah alat uji direproduksi; usulan perbaikannya lulus 14 kontrol lokal.** Kandidat SKU A tetap `e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e`, tree `ead4c59721d1fc1dc608a9f803dbaf2a076abbdd`. Paket ini melanjutkan cabang bukti B dari `0568c7fcde1be77444c3156f4b965f7f33404573`; berkas runtime A tidak diubah. A tetap integrator dan pemilik run SKU/Global.

## Temuan dan penutupan terarah

`erp.post_material_purchase(uuid)` pada katalog diagnostik asli A165 mendebit `MATERIAL_INVENTORY` dan mengkredit `AP_SUPPLIER`. Daftar delapan pemetaan akun pada preflight uang belum memeriksa `AP_SUPPLIER`. Adapter E4EA dan validator akhirnya juga belum mensyaratkan bukti pemetaan itu. Ini memungkinkan pemeriksa awal berkata PASS ketika konfigurasi akun yang dibutuhkan fixture belum lengkap.

Tidak ditemukan bukti bahwa `AP_SUPPLIER` hilang pada database run A. Temuan ini adalah kekurangan pemeriksaan setup, bukan bukti kesalahan saldo atau alasan menghentikan run A.

| Kasus | Harapan | E4EA sebelum patch | Usulan B | Status bukti |
| --- | --- | --- | --- | --- |
| Pemetaan `AP_SUPPLIER` hilang, akun nonaktif, tidak boleh diposting, tautan akun putus, atau lebih dari satu baris | Tolak sebelum kasus bisnis | Lima keadaan tetap PASS; akun tidak dibaca | Lima keadaan REFUSED | `FAIL` lama → `PASS` kontrol lokal |
| Satu akun aktif dan boleh diposting | Terima setup yang lengkap | PASS | PASS; validator menerima bukti yang lengkap | `PASS` kontrol lokal |
| Galat pembacaan akun selain data tidak lengkap | Galat tetap terlihat | Pembacaan tidak dilakukan | Galat diteruskan | `FAIL` lama → `PASS` kontrol lokal |
| Bukti pemetaan dihilangkan, kosong, salah, atau ditambah kunci tak dikenal | Validator menolak | Empat bentuk diterima | Empat bentuk ditolak | `FAIL` lama → `PASS` kontrol lokal |
| Izin dicabut, pembacaan aktor gagal, atau potret keadaan berubah | Tetap menolak; sesi aktor dipulihkan | Menolak | Menolak | `PASS` kontrol lokal |

[Kegagalan pertama](FIRST_FAILURE.json) tetap utuh: 10 dari 14 ekspektasi kontrol tidak terpenuhi. [Hasil usulan](PROPOSED_RESULT.json): 14/14 terpenuhi. Ini satu akar masalah, bukan sepuluh bug ERP. Pengujian menjalankan kode Python preflight E4EA, model protokol SQL lama yang sudah tersedia, validator uang asli, dan tubuh fungsi validator otomatis asli. PostgreSQL, Auth, transaksi keuangan dan seluruh runner akhir tidak dijalankan.

[Patch usulan](SUPPLIER_ACCOUNT_PREFLIGHT.patch) menambah satu SELECT pemetaan, menyertakan hasilnya pada bukti, dan mewajibkannya pada validator. Patch mencakup `native_preflight.py`, `final_gate.py`, pembaruan kontrol `test_final_gate.py`, serta tiga pin pada `SOURCE.json`. **93 pin lainnya tetap identik.** Tidak ada perubahan SQL produk, izin, tanggal, kuantitas, rumus uang, atau jumlah pengambilan potret keadaan.

Patch lulus pemeriksaan penerapan pada sumber tepat E4EA. Patch percepatan digest B sebelumnya lalu patch akun ini juga bisa diterapkan berurutan; keempat pin berkas yang berubah cocok. [Bukti penerapan bersama](COMBINED_PATCH_CHECK.json). Belum ada pengukuran waktu database untuk SELECT tambahan ini.

## Prasyarat dan bagian yang masih terbuka

| Jalur | Sumber/bukti yang dipakai ulang | Hasil baru dan batas klaim | Status |
| --- | --- | --- | --- |
| Global: identitas kandidat dan otoritas | Sumber Global beku `c9248b87` dari cadangan A; pemeriksaan 208 baris A pada A165 | Delapan syarat runtime masih kosong. Tidak diisi memakai hasil diagnostik atau model. | `BLOCKED` untuk runtime |
| Global: akun, aktor, unit, lokasi, master dan tanggal | Preflight diagnostik A165 dan koreksi ordinary actor E4EA oleh A | Delapan akun, PCS, lokasi dan master tercatat pada sumber lama; pemeriksaan tambahan akun supplier disiapkan. Hasil tersebut belum membuktikan salinan gabungan E4EA. | `BLOCKED` untuk runtime |
| Supplier: koreksi pembayaran | Original 23 kasus `38abb879` dan penerus `43265e22`; masing-masing lima JSON akar cocok byte/hash | Kedua paket berstatus PASS dalam cakupan asal. Penerus menggantikan 23 kasus yang sama. SQL, kasus, browser dan panel sekarang berbeda; dua berkas langsung tetap identik. Gunakan driver yang ada setelah sumber dan efek gabungan dicocokkan. | `PASS` verifikasi arsip; `BLOCKED` klaim versi gabungan |
| Kas dan jurnal | Original `d0b41469`, produk `7022148f`; lima JSON akar cocok byte/hash | 21 kasus historis PASS: termasuk pembaca kas/jurnal dan 10 perjalanan browser. Berkas kasus kas tetap identik, tetapi browser, fixture dan panel berubah. Belum menjadi kelulusan tampilan saat ini. | `PASS` verifikasi arsip; `BLOCKED` klaim versi gabungan |
| Aksesori dan invoice susulan | 19 kasus uang yang dipertahankan serta dua kasus PO rework/redye dalam Native25 A; regresi B `52b6cf93` | Invoice susulan, inverse dan replay sudah memiliki jalur A. Regresi dua biaya/dua retur B tetap berlaku pada fixture dan sumbernya. Tidak dibuat run kedua. | `BLOCKED` hasil gabungan; bukti lokal lama dipakai sesuai cakupan |
| QC, WIP dan Business Report INCLUDED | Handoff B `52b6cf93`; koreksi periode oleh A | Prasyarat tetap: biaya resmi Rp288 untuk 8 PCS, akun WIP/FG, owner berizin, dan periode berisi tanggal ekonomi QC. Harapan WIP 288→180, FG 0→108, HPP penjualan 0 belum mempunyai aktual gabungan. | `BLOCKED` |

[Review arsip dan perbandingan sumber](RETAINED_EVIDENCE_REVIEW.json) memuat 15 JSON akar terverifikasi dan 44 kasus historis unik; **nol kasus ERP baru**. Folder `qualified38-e05` ternyata menyimpan bukti payroll E05 sehingga tidak dipakai sebagai bukti koreksi pembayaran supplier. Bukti FREE3 juga hanya bukti prasyaratnya, bukan hasil Afui baru.

[Prasyarat lengkap](GLOBAL_PREREQUISITES.json) mencatat data yang belum tersedia. Arsip A165 berisi clone dasar T3 dan katalog diagnostik; tidak tersedia di sini database gabungan siap transaksi yang setara. B tidak membuat ulang pemasangan panjang dan tidak menghubungi database run A. Tidak ada perubahan database pada pekerjaan ini, sehingga tidak ada klaim pemulihan database baru.

## Penerapan dan reproduksi untuk A

Gunakan penerus kandidat setelah A menentukan kebutuhan integrasi. Jangan menerapkan validator baru pada artefak historis E4EA: artefak itu memang belum memiliki field tambahan. Cocokkan keempat preimage dalam [receipt](SOURCE_AND_RUN_RECEIPT.json) sebelum penerapan. Jika A sudah maju, pindahkan perubahan secara selektif. Sumber f167 yang dibekukan tidak diubah.

Di direktori lokal baru, siapkan empat berkas `native_preflight.py`, `final_gate.py`, `test_final_gate.py`, `SOURCE.json` dari E4EA di `baseline/scripts/current-sku-automatic-composite-preparation/`. Buat salinan `proposed/` lalu terapkan patch di sana. Siapkan `retained/` dengan:

- `native_preflight.py` dan `test_native_preflight.py` dari `f1674ae84739f577571d68415beabfca3f3b832b:scripts/current-sku-cost-money-qualification/`.
- `money_gate_support.py`, `EXECUTION_PREREQUISITES.json` dan `SOURCE_REFERENCE.json` dari `e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e:scripts/current-sku-money-composite-preparation/`.

```bash
python -B replay_supplier_preflight.py baseline retained FIRST_FAILURE_NEW.json
# Ekspektasi sumber lama: exit 1, 10 ekspektasi tidak terpenuhi.
python -B replay_supplier_preflight.py proposed retained PROPOSED_RESULT_NEW.json
# Ekspektasi usulan: exit 0, 14/14 kontrol lulus.
```

Output ditulis eksklusif agar kegagalan pertama tidak tertimpa. Sebelum penerimaan, A masih perlu pemeriksaan sumber gabungan dan kontrol runner yang relevan pada kandidat penerus. Run penuh SKU/Global, instalasi gabungan, audit independen dan produksi bukan bagian kelulusan paket B ini. Formal tetap 5/16; `production_go=false`, `independent_acceptance=false`.
