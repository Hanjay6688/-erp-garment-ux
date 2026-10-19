# AUDIT SOL — commit 17fa2507 — 19 Oktober 2026

Kandidat: `17fa25075ba77f0853c3c16f504288ace03eec35`.
Tree: `65f778479093d869a3354c0b9f19b4d9a541d98a`.

**Paket uji ulang r5 selesai; penutupan penuh CP1–7 tetap HOLD.** CP6 tetap CLOSED dalam lingkup yang sudah diterima. `feature_complete=false`, `audit_complete=false`, `production_go=false`.

## Ringkasan

- Temuan akar produk baru: S0 0, S1 0, S2 0, S3 0. S1 lama SOL-R4-001 tertutup pada kandidat r5 yang dipasang di lingkungan uji. S2 lama KNOWN-P19-DIRECT-LATENCY masih terbuka.
- Invarian: **74 PASS /0 FAIL /8 INCOMPLETE** dari 82. Skenario: **22 PASS /7 INCOMPLETE** dari 29. Sambungan: **20 PASS** dalam lingkup tertulis, bukan 20 alur lengkap dalam satu browser.
- Inventaris 57 kebutuhan dan 47 layar bukan persentase ERP selesai. Bukti r4 yang dipertahankan tidak mendapat kredit eksekusi r5.
- Semua 12 run milik Sol sudah terminal: 9 SUCCESS/3 FAILURE. Dari 31 job, 28 SUCCESS/3 FAILURE. Tiga kegagalan berasal dari alat/fixture auditor dan tetap disimpan.
- Dari 30 laporan primer dengan byte berbeda terdapat 1.039 kemunculan kasus: 1.036 PASS/3 INCOMPLETE, dengan 1.034 string ID unik. Ini bukan 1.039 skenario bisnis independen. Empat kontrol decoder murni terpisah menambah nol eksekusi Native.

## Identitas, lingkungan, dan perintah

Acuan r4 adalah `663f6faefcbb9c70f0f99bbc7e78164e03521329`, segel Sol `ecb44425710a0a29203835076f32ef83f7d436d2`. Cabang Sol: `audit/sol-cp1-7-r5-17fa2507-20261019`. Writer `claude/new-session-deapao` tetap pada `2766a9092f51f240267b9cbe1201d49a836fb490` saat pemeriksaan akhir; sembilan perubahan sesudah kandidat hanya dokumen. Sebelas root produk/subroot cocok. Sol tidak mengubah produk.

`SOURCE_FREEZE_INITIAL.json`, `SOURCE_FREEZE_END.json`, manifest, dan `STATIC_IMPACT_MAP.json` merekam batas sumber. `src` dan `supabase` tidak berubah terhadap r4. R5 mengubah 12 signature melalui 11 reader dan satu checker. Peta dampak memuat sepuluh path produk yang berubah beserta caller terkait.

CI memakai Ubuntu 24.04. Ekspor runtime CP17/kualifikasi mencatat PostgreSQL 17.6, Node 22.23.3, Python 3.12.15; psycopg 3.2.10 dan Supabase CLI 2.116.0. Client PostgreSQL 17 serta tag image 17.6.1.165 tidak menggantikan versi server yang diamati. Tidak semua job regresi mengekspor versi runtime tersendiri. Browser memakai Chromium Playwright dengan emulasi desktop/mobile/iPad. Build Enteng menghubungkan API yang dicegat ke database lokal, bukan hosted Enteng; perangkat Apple fisik tidak diuji.

Panduan: `docs/AUDIT_PANDUAN_PRO_MAX.md`, SHA256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`.

Perintah tepat tiap run ada di `COMMAND_LEDGER.json`, terikat pada SHA workflow di `RUN_REGISTER.json`. Di antaranya `npm ci`, `npx playwright install --with-deps chromium`, pencatatan identitas before/after, serta skrip Sol `reader_graph_qualification.py`, `reader_mapping_q3_qualification.py`, dan `repair_negative_vector_qualification.py`. `qualify_multirow_capture.py` membaca arsip yang sudah dipatok tanpa mengulang SQL. Log asli menunjukkan langkah yang berjalan, dilewati, atau gagal.

SHA workflow berbeda dari SHA kandidat; checkout aplikasi tetap dipatok ke kandidat. Identitas GitHub tidak dipalsukan. Ke-42 pasang rekaman before/after semuanya cocok; hitungan ini termasuk salinan artifact complete-json, bukan 42 job independen. Seluruh run memakai attempt 1. Bootstrap aktual tiap job Native berhasil pada percobaan pertama; pengulangan startup dibatasi dua sebelum uji bisnis dan pengulangan bisnis dinonaktifkan. Batas produk delapan detik dan cap tidak dilonggarkan.

## Temuan dan hasil perbaikan

### SOL-R4-001 — alarm palsu Nota FG_REPAIR tertutup pada kandidat terpasang

Keparahan historis **S1**, terkait INV-D01/D02/D03, sambungan S3, FUN-039/FUN-041. Rantai dampak: sumber perbaikan FG → Nota → payroll_work_items → resolver kontraktor checker → alarm integritas palsu.

1. Buat upah perbaikan Native 2 PCS dan 1 PCS dengan tarif Rp2.000; simpan dan POST melalui Nota CP7. Total benar Rp6.000.
2. Oracle Sol asli dijalankan tanpa perubahan: seluruh 167 detektor nol sebelum transaksi, sesudah sumber, DRAFT, POST, dan rollback. Checker lama tetap mereproduksi +2 sehingga uji masih membedakan versi.
3. Tambahan independen: Nota sah → REVERSED Native → Nota pengganti Rp6.000. Seluruh 167 detektor nol pada lima tahap; jurnal, stok, dan HPP tidak berubah.
4. Kontrol negatif mengekspor 167 baris pada enam tahap: awal nol, Nota sah nol, kontraktor salah tepat satu, rollback nol, upah sumber hilang tepat satu, rollback nol. Guard upah dimatikan hanya saat memasukkan inkonsistensi terkontrol, aktif kembali saat detektor dibaca, dan dipulihkan oleh rollback. Ini bukti sensitivitas, bukan bukti hak akses atau pencegahan guard.

**TERBUKTI / NATIVE_QUALIFIED.** Run 39237249873, 39239045650, 39246794670; `READER_AND_DETECTOR_RESULT_REVIEW.json`. Lokasi perubahan: `scripts/cp7_payroll_checks_bundle.py`; jalur sumber `scripts/cp7-src/payroll/source.sql`; pengujian `scripts/cp7_r5_cases.py`. Peta caller serta definisi ada di `STATIC_IMPACT_MAP.json`. Tidak ada klaim bahwa nominal keuangan dahulu salah atau UI pembayaran/tutup periode dahulu terblokir. Kandidat belum dipasang ke Enteng.

### KNOWN-P19-DIRECT-LATENCY — sasaran tiga detik belum konsisten

Keparahan **S2 lama**, acuan D17-2; bukan temuan akar baru. Rantai: sumber operasional/keuangan → capture analisis → pembacaan book/proyeksi → RPC → hasil atau refusal di browser.

|Uji browser|Histori 1 hari|30 hari|100 hari|
|---|---:|---:|---:|
|100 barang dengan keuangan|2.977,1 ms|2.936,3 ms|**3.448,8 ms**|
|300 barang operasional|6.219,0 ms|6.636,1 ms|8.044,2 ms|
|300 barang dengan keuangan|10.241,6 ms|10.714,7 ms|8.045,6 ms: refusal 57014|

Refusal jujur bukan bukti kapasitas berhasil. **TERBUKTI / NATIVE_QUALIFIED**, run 39237719026, job 118010759185, artifact 12183472678/12182948458. ID pengukuran serta byte asli ada di `PERFORMANCE_RESULT_REVIEW.json`. Satu hasil 100 barang masih melewati 3.000 ms. Perbandingan r4/r5 bukan eksperimen pasangan pada VM sama, sehingga tidak diberi klaim sebab akibat percepatan tertentu.

Staged **operasional** 5.000 target selesai lengkap pada tiga sampel, masing-masing 26 halaman: 79.237,4/88.283,8/108.775,6 ms. Progress terlihat 2.293,5/2.618,9/3.154,2 ms; buka ulang hasil 1.056,6/1.298,7/1.413,3 ms. Pengecualian staged bernama dinilai tersendiri: pengakuan awal di bawah satu detik terpenuhi, bukan seluruh alur selesai dalam tiga detik. Progress 3.154,2 ms disimpan sebagai observasi, bukan akar bug baru. Tidak ada klaim staged keuangan 5.000 target.

Lokasi telusur: `scripts/cp7-src/planning/analysis-finance.sql`, `analysis.sql`, `scripts/cp7_report_accounts_bundle.py`; peta dampak memuat caller/fase terkait. Profil diagnosis 100 barang finance dengan jit ON mencatat `erp.account_id(text)` 2.476 panggilan (212,973 ms total/35,178 ms sendiri), `require_internal` 3.652 panggilan (266,698/201,477 ms), dan resolver opening FG HPP 588 panggilan. Ini diagnosis, bukan waktu aplikasi dan bukan bukti lookup akun satu-satunya penyebab.

Saran writer: lanjutkan di cabang terpisah sesuai D17-2; kurangi pembacaan book dan perhitungan berulang, lalu evaluasi agregasi per query. Ukur ulang ID/workload sama dengan hasil lengkap, otoritas, source hash, batas delapan detik, dan cap tetap. Sampling, pemotongan hasil, atau menaikkan batas tidak menutup temuan.

## Dampak r5 dan regresi

- **Kesetaraan 11 reader:** seluruh badan old canonical dipasang bersama dalam savepoint, sehingga nested call juga benar-benar memakai graf lama. Produksi PO 10 unit dengan total HPP120 → jual dua: FG96/COGS24 → retur satu: FG108/COGS12. Lifecycle penjualan +24 dan retur −12. Seluruh 11 hasil cocok pada tiga tahap, termasuk missing/NULL/empty; seluruh 167 detektor Owner nol sesudah alur sah. Bukti ini terbatas pada input yang diuji.
- **Mapping:** statement PREPARE yang sama membaca 120→0→120 ketika mapping FG asal dipindah ke akun ASSET baru lalu dikembalikan. Semua 11 graf lama/baru cocok pada tiga mapping. DELETE/RENAME core mapping ditolak Native P0001; guard aktif dan restore lengkap.
- **Banyak baris dalam satu SQL:** seluruh 11 hasil old/new serta WHERE FALSE cocok. PO108/12/0, missing/NULL0; lifecycle24/−12/**SQL NULL**/24. Kasus mentah tetap INCOMPLETE karena Python `json.loads(None)` sesudah pembandingan SQL. Capture dikualifikasi baca saja memakai empat kontrol decoder; tidak ada SQL baru. Assertion fingerprint inner terakhir tidak berjalan dan tidak diklaim; strict outer/case restore terbukti.
- **CP17:** 345 PASS: 165 Native, 39 races, 27 HTTP, 57 browser, 57 build Enteng lokal. Label 39 races tidak otomatis berarti 39 overlap kritis terbukti.
- **Regresi:** seluruh delapan bucket F03 PASS; nota correction PASS; 12 kelompok P19 terminal; P21 rehearsal PASS. Oracle writer yang dieksekusi Sol diberi label terpisah dari kontrol serta perhitungan literal Sol.
- **Pemulihan:** backup terpakai → salinan baru cocok pada 590 tabel; backup preinstall → salinan baru juga cocok. Rollback sebelum pemakaian exact dan katalog reinstall cocok. Sesudah dipakai, uninstall/harness **bukan** pemulihan data exact: 116 tabel bisnis berubah, komponen `erp_platform_auth_schema_acl=false`, dan 54 role cluster tersisa setelah restore preinstall. Gunakan alur restore ke salinan baru yang terbukti.
- **K3:** boundary B masih menulis ke replacement sebelum mismatch; replacement tetap ada. PASS mentah bukan bukti perlindungan tanpa penulisan. Patch tetap ditunda ke CP7C sesuai D13-9a. `REGRESSION_AND_RESTORE_REVIEW.json` membedakan batas ini.

## Matriks dan yang belum ditutup Sol

Rincian per ID, bukti, serta tindakan berikutnya ada di matriks invarian/skenario/sambungan, `DETECTOR_DISPOSITIONS.json`, `FUNCTION_DETAIL.json`, dan `OPEN_BOUNDARIES.json`.

|Kelompok|Belum lengkap|Alasan atau batas|
|---|---|---|
|INV-D01/SKN-19|Kontrol negatif seluruh detektor|R5: 11/167 qualified, 156 belum diuji ulang negatif. Seluruh putaran Sol: 22 pernah qualified, 145 belum. Nol normal/penolakan guard bukan sensitivitas.|
|INV-T02|Semua entrypoint periode|25 jalur Data API tertutup; Native legacy/grant ditunda ke CP7C, D14-9.|
|INV-T04|Arbitrary historical as-known|Filed/captured Original immutable teruji; query pengetahuan umum belum tersedia.|
|INV-L07/SKN-29|File history/audit yang sudah dimuat sesudah revoke tanpa refetch|Batas probe akses sesi terdahulu tetap ditahan, termasuk bila berganti nama/transport.|
|INV-M01/M03/M04; SKN-16/21/22|Hosted aktual, sumber saldo nyata, cutover, shadow|Tidak ada SQL hosted; fixture atau clone aligned bukan dokumen cutover bertanda tangan.|
|INV-D04|Snapshot sebelum/sesudah seluruh 29 skenario|Dependensi skenario nyata tertunda; global akhir nol tidak menggantikan.|
|SKN-07|Seluruh alokasi 1/3 dan batas pecahan intermediate|Uji sen/besar terpilih ada; oracle alokasi lengkap belum diamati.|
|SKN-09|Lintas tengah malam WIB aktual|Kontrol UTC/WIB/sintetis bukan wall-clock crossing.|
|Lain|Staff fresh transaction allow, tiga desain probe yang ditahan, Apple fisik|Batas lama dipertahankan; bukan bug produk baru.|

Ini menjelaskan apa yang **Sol belum tutup**, bukan menyatakan auditor lain belum menguji; laporan sejawat r5 tidak dibaca. Keputusan CP7C dan D17-2 tidak dibuka kembali. Seluruh job putaran ini sudah selesai; penutupan global memerlukan prasyarat dan batas di atas.

## Hasil merah yang bukan temuan produk

|Run/kasus asal|Klasifikasi|Kejadian serta kualifikasi|
|---|---|---|
|39239045650: reader mapping|AUDITOR_TOOL|Constructor akun kurang NOT NULL report_group; gagal sebelum PREPARE. Sibling full graph/reversed repair PASS tetap disimpan.|
|39240123342: reader multirow|AUDITOR_TOOL|Python mendecode SQL NULL setelah pembandingan SQL direkam. Run39241538078 hanya mengkualifikasi capture, menambah nol Native. Raw FAILURE/INCOMPLETE tidak diubah.|
|39240645298: mapping Q2|AUDITOR_TOOL|Rollback savepoint graf memicu cache prepared psycopg3.2.10 menghapus PREPARE manual; 26000 tertutup cleanup25P02. Q3 run39242137321 memisahkan masa hidup PREPARE dan rollback graf; oracle120/0/120 tetap dan PASS.|

Tidak ada rerun job asal; seluruh run_attempt1. `AUDITOR_TOOL_FAILURES.json` serta `PSYCOPG_ROLLBACK_SOURCE_REVIEW.json` memuat kualifikasi, sumber resmi, dan koreksi metadata hitungan awal.

Receipt writer juga tidak dianggap semuanya hijau: 116 run terdiri dari 94 success/22 failure; 179 job terdiri dari 157 success/22 failure. Sebanyak 22 hasil merah cocok pada metadata job/failing step dengan pembanding r4. Ini **bukan** bukti semua penyebab sama dan **bukan** kredit Native Sol.

## Label asal bukti per klaim

|Klaim|Asal eksekusi dan oracle|Rujukan|
|---|---|---|
|Nota6000, negatif, PO/jual/retur, graf/mapping|INDEPENDENT_NATIVE_RERUN; oracle literal/kontrol Sol|Run39237249873,39239045650,39246794670,39242137321|
|CP17/F03/note/P19/P21|INDEPENDENT_NATIVE_RERUN; WRITER_ACCEPTED_ORACLE_EXECUTED_BY_SOL|RUN_REGISTER/CASE_LEDGER; fixture Native writer disposable|
|Multirow dari artifact|INDEPENDENT_CAPTURE_REVIEW; nol Native baru|39241538078 dan artifact asal12181840235|
|Peta dampak/definisi/freeze|INDEPENDENT_SOURCE_REVIEW|STATIC_IMPACT_MAP, manifest, SOURCE_FREEZE_*|
|Status r4 dipertahankan|REUSED_AUDITOR_LOG_READ; nol kredit r5|Segel r4ecb4442 serta matriks per ID|
|Receipt CI writer|REUSED_WRITER_EVIDENCE ditambah pemeriksaan metadata provider independen|Receipt dalam arsip; bukan temuan peer|

## Bukti dan keterulangan

Seluruh 43 arsip provider diunduh dan size/SHA256 cocok. Sebanyak 695 member teks asli berukuran 654.178.828 byte dipertahankan. Ke-31 job log adalah UTF-8 decoded exact yang dikembalikan konektor; hash ZIP log provider tidak tersedia. Arsip akhir berisi 808 member termasuk receipt, metadata, dan log, dengan total 674.415.492 byte sebelum kompresi. Gambar/binary tidak dipilih dan tidak ada klaim inspeksi screenshot.

Arsip: **Sol-r5-bukti-20261019.zip**, 35.193.963 byte; SHA256 `13d650feb033c02abc4d35d562e53f8503071ff7ffe96e56c78e73445bf43e3c`; CRC PASS. Whitelist SHA256 `001f60607218dde419c243102c8a8ef32e90199ff333184a5f2f7447313cd065` mengunci setiap path, jumlah byte, dan hash. Bukti r4 tetap di arsip lama yang tersegel; tidak diganti. Lihat `ARCHIVE_RECEIPT.json` serta `REPRODUCE.md`.

Tidak ada penulisan produk, main, cabang writer, hosted, atau produksi. Penulisan hanya ke cabang audit sendiri dan database CI sekali pakai. Pembandingan reader internal memakai sesi administratif pemilik database dengan Owner JWT claims; bukti public Auth/HTTP/browser terpisah. Jangan memakai pembandingan internal sebagai bukti otorisasi UI.

## Pertanyaan untuk owner

Tidak ada pertanyaan baru. D17-2 sudah mengatur cabang percepatan terpisah; D14-9 dan D13-9a sudah mengatur CP7C. Pemasangan ke Enteng tetap ditahan.

## Ringkasan untuk owner

Uji ulang Sol r5 dan paket bukti sudah selesai. Alarm palsu Nota Rp6.000 tertutup pada kandidat baru. Angka PO, penjualan, retur, serta mapping yang diuji tetap cocok. Target tiga detik belum konsisten karena 100 barang dengan histori100 hari masih 3,45 detik. Seluruh 5.000 target operasional staged selesai lengkap dengan batas pengecualiannya. Sebagian bukti detektor negatif, akses, perangkat, dan sumber cutover nyata belum ditutup Sol. Tiga kegagalan alat uji saya tetap dicatat. Tidak ada keputusan baru yang perlu Bos ulang. CP6 tetap ditutup dalam lingkup diterima; CP7 dan audit penuh tetap HOLD.

## Fokus tambahan paling berisiko

Nol alarm normal tidak membuktikan seluruh detektor sensitif. Penguatan uji permanen: assert baseline aktual 167 detektor nol; bandingkan seluruh graf old canonical bersama; pakai hasil PO/lifecycle nonzero 120/24/−12; bedakan SQL NULL dari nol; pertahankan output negatif lengkap serta restore. Ini saran penguatan uji, bukan tambahan bug produk yang telah terbukti. Percepatan analisis harus mempertahankan kelengkapan angka dan izin.
