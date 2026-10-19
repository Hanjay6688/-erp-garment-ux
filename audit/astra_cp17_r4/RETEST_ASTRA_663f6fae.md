# Astra — uji ulang CP1–CP7, r4

**Audit putaran r4 selesai: LULUS UJI ULANG DENGAN BATAS BUKTI.** Empat akar temuan Astra yang terbuka pada r3 **DITUTUP** pada kandidat ini. Tidak ditemukan cacat produk baru dalam cakupan pemeriksaan r4: baru S0=0, S1=0, S2=0, S3=0. Ini tidak menghapus pekerjaan lama yang masih terbuka atau menjadi izin produksi. `round_r4_audit_complete=true`; `feature_complete=false`, `audit_complete=false` untuk seluruh gerbang Pro Max, dan `production_go=false`. Enteng/CP7C tetap HOLD.

Kandidat **`663f6faefcbb9c70f0f99bbc7e78164e03521329`**, tree **`023f3554432f80f994439f5d0b8cc164846a2041`**. Cabang Astra `audit/astra-cp1-7-r4-663f6fae-20261019`. Pendahulu r3 `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`; laporan r3 terkunci di `741ffdf30d9ff2709e4b60af901f6dba98a9c1e4`. Run berlangsung 19 Oktober 2026 UTC/WIB. Panduan Pro Max SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`.

## Identitas, asal bukti, dan batas lingkungan

Penulis dibaca pada `5eda90e10b2e87485ab710e9fd9ffa68d81a3565`, dan diperiksa lagi pada akhir audit: tetap commit yang sama. Sembilan path sesudah kandidat semuanya dokumen. `supabase/` tidak berubah sejak r3. Perubahan r3→r4 yang memengaruhi produk/alat/UI adalah 37 path; patch lengkap ada di `PRODUCT_DELTA.json`, hash/tree di `IDENTITY.json` dan pemeriksaan penutup di `FINAL_IDENTITY.json`.

Tujuh workflow Astra mem-pin aplikasi ke kandidat, sementara checkout baseline dan harness historis mempertahankan pin aslinya. Runtime CI sekali pakai: Ubuntu 24.04, Supabase CLI 2.116.0, PostgreSQL 17.6.1.165, Python 3.12/psycopg 3.2.10, Node 22 dan Playwright dari lockfile kandidat. Versi teramati dan identitas setiap checkout tersimpan pada 18 log mentah. Perintah pokok: `cp7_cp17_fix_probe.py`; runner Astra `risk_runner.py`, `audit_paging_runner.py`, `retained_runner.py`, `guard_runner.py`; 12 suite dalam workflow P19; Vitest dua oracle DOM Astra dan dua berkas DOM terdampak milik penulis; serta kontrol drain dan comparator. Seluruh langkah ada pada `.github/workflows/audit-astra-r4-*.yml`.

Tidak ada SQL hosted, mutasi Enteng/legacy, Drive, deployment, main, atau cabang penulis. Build Enteng dijalankan terhadap backend disposable dengan host proyek diarahkan ke loopback; hasil itu tidak membuktikan pemasangan hosted. Tidak ada pengiriman WA nyata. Matriks demo/tersambung 282 kasus dari r3 dipertahankan sebagai bukti r3, tidak dihitung sebagai run r4. Empat oracle DOM lama dan perjalanan browser yang relevan dijalankan ulang pada r4.

Tidak membaca laporan, isi cabang, run, artifact, atau komentar auditor lain dari r4 sebelum lock. Nama path direktori Sol sempat terlihat saat inventaris workspace awal; isinya tidak dibuka, dan checkout Astra terpisah dipakai. Metadata nama cabang yang dicetak checkout Git juga bukan pembacaan laporan. Ini pernyataan disiplin, bukan klaim isolasi akses teknis. Laporan putaran lama serta penjelasan penulis dibaca sebagai konteks. Workspace sementara sempat dibersihkan otomatis di antara giliran; sumber dipulihkan dari commit Astra dan bukti diunduh ulang dari run yang sama, tanpa menjalankan ulang kasus.

## Hasil per kasus

**565 observasi kanonik, 565 ID unik, semuanya PASS menurut oracle masing-masing:** 263 Native, 90 race, 51 HTTP Auth nyata, 82 browser, 57 browser build Enteng, dan 22 DOM. Tidak ada kasus hilang, duplikat, skip, atau status tidak dikenal pada manifest yang dijalankan. Daftar ID dibandingkan, bukan hanya total. Untuk Enteng, harness memakai jadwal browser tanpa suffix lalu memberi label `_ENTENG`; ID hasil juga dicocokkan langsung dengan manifest eksternal yang sudah bersuffix sebelum run.

| Run | Kasus | Asal oracle |
|---|---:|---|
| [39184582331](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184582331), CP17 | **341 PASS**: 161 Native, 39 race, 27 HTTP, 57 browser, 57 Enteng | Paket oracle penulis beku, termasuk port reproduksi auditor lama; eksekusi Astra. |
| [39184678978](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184678978), risiko | **4 PASS** | Oracle Astra r3 tidak diubah. |
| [39184679037](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184679037), pagination | **1 PASS** | Jadwal tiga sesi Astra r3 tidak diubah. |
| [39184830778](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184830778), retained Native | **11 PASS** | Oracle Astra lama tidak diubah. |
| [39184830743](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184830743), guard | **3 PASS** | Oracle baru Astra, dideklarasikan sebelum run. |
| [39184830745](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184830745), DOM | **22 PASS** | 4 oracle Astra, 18 penulis. |
| [39184679009](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39184679009), P19, 12 job | **183 PASS** | Oracle penulis beku, eksekusi Astra; kegagalan unggahan kedua dijelaskan di bawah. |

**23 kasus memakai oracle Astra; 542 memakai oracle paket penulis.** Eksekusi independen atas oracle penulis tidak diklaim sebagai rancangan oracle independen. Fixture dasar banyak memakai helper penulis; expected arithmetic serta jadwal serangan Astra berdiri sendiri. Jumlah ini tidak mencampur predecessor checks, dua kontrol tambahan, run penulis, atau hasil r2/r3.

P19: transport 15, staged 14, report 20, plan 22, AI 9, reminder 16, history yield 20, scale 5, retention 10, cleanup 25, runner 17, proof runner 10. Angka di nama workflow bukan denominator. Semua report runtime membuktikan pemulihan CP6 dan advisor gate. Hash bundle lengkap CP17/Astra `f883ec3fbe1c4cdde4a9249b1ed83afd2e62cfedceec2e6277a25ec0f2609318`; P19 menggunakan susunan bundle berbeda, sehingga hash-nya dicatat per suite dan tidak disamakan dengan CP17.

`CASE_LEDGER.json.gz` menyimpan setiap ID, observed lengkap, status asli/protokol, asal oracle/fixture, run/job/attempt, dan artifact. `CASE_SUMMARY.json` menyimpan kecocokan himpunan ID. `RUNTIME_EVIDENCE.tar.xz` mempertahankan 212 JSON asli beserta indeks SHA-256; termasuk laporan utama, witness skala, pemasangan, clone, serta restore. `RAW_LOGS.tar.xz` memuat 18 log Astra. Arsip CI asli, digest ZIP dan masa simpannya tercatat dalam `RUN_REGISTER.json`.

## Penutupan empat temuan Astra

### ASTRA-R3-01 — S1 — jalur publik pool HPP: DITUTUP

**NATIVE_QUALIFIED; INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** Dua probe HTTP lama Astra dijalankan tanpa perubahan oracle. Periode pool ditutup sampai 16 Oktober: facade CP7 menolak HTTP400 `CP7_HPP_POOL_PERIOD_CLOSED`; jalur publik lama sekarang menolak HTTP403/42501 `CP7_PUBLIC_ROUTE_CLOSED`, tanpa efek pada boundary. Sesudah hak `finance.hpp.manage` dicabut, facade CP7 menolak HTTP403 `CP7_HPP_POOL_DENIED` dan jalur lama juga HTTP403; tidak ada pool DRAFT yang tercipta. Probe memakai Auth nyata, tanpa grant skema privat khusus tes.

Kontrol CP17 menembak **seluruh 25 rute yang ditutup** melalui Data API: semuanya HTTP403 dan tanpa penulisan. Rute aplikasi yang diuji tetap HTTP200; lifecycle pool create→activate→cancel→replacement, hak/periode, replay dan race tetap lulus. Sensus menguji 69 rute legacy yang executable oleh peran browser: 25 ditutup, 40 rute aplikasi dipertahankan, 4 reminder dipertahankan; rute baru, anon-only, serta rute tertutup yang dibuat ulang tanpa guard ditolak oleh pemeriksaan instalasi.

Lokasi: `scripts/cp7_public_routes_bundle.py`, pemasang `cp7_f03_bundle.py`/`cp7_note_report_bundle.py`, penjagaan wrapper dalam `cp7_hpp_pool_bundle.py`. Guard `session_user='authenticator'` berada sebelum isi lama. Sesi SQL langsung sengaja tidak berubah; kontrol Native membuktikan perilaku itu. Penutupan ini tidak mencabut 82 fungsi privat yang ditunda D14-9 dan tidak memberi izin mengekspos skema privat. INV-T02/A01/POL03; keluarga writer alternatif diperiksa. Bukti gagal r3 tetap ada pada lock741ffdf3; bukti lulus r4: risk job117844478259 dan CP17 job117844186935.

### ASTRA-R2-01 — S1 — inverse penambahan FG menghalangi buka ulang: DITUTUP

**NATIVE_QUALIFIED; INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** Oracle positif Astra: PO FINISHED, stok10, HPP120/basis10; penyesuaian+2 membuat12, pembalik−2 menunjuk transaksi+2 dan mengembalikan10. Kini blocker kosong, REOPEN berhasil keQC, stok10 dan HPP120/basis10 tetap. Dua probe terdahulu—penyesuaian negatif yang dibalik serta draf penjualan dibatalkan—juga lulus lagi.

Kontrol penulis membuktikan pemakaian aktif2PCS masih menghalangi; setelah draf dibatalkan baru eligible. Reopen→finish kembali mempertahankan stok10, HPP120 dan WIP0. Dua tab menghasilkan satu keberhasilan dan satu `CP7_PO_REOPEN_STALE_REVIEW`, satu riwayat buka ulang. Lokasi `scripts/cp7-src/cutting-correction/po-reopen.sql`: outflow yang merupakan inverse inflow positif tidak dianggap konsumsi produksi; inflow lain tidak dipakai menghapus konsumsi yang tidak terkait. INV-K06/U03, SKN-12/27. Bukti r4: risk job117844478259, retained job117844937943, CP17 job117844186935.

### ASTRA-R3-02 — S2 — transaksi terlambat terlewat pada Audit Trail: DITUTUP

**NATIVE_QUALIFIED; INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** Jadwal Astra tetap: ID231 tertahan `idle in transaction`, ID232 sudah commit, halaman pertama berisi232/230/229 dengan total8;231 baru commit sesudahnya. Cursor lama memang tidak mengunjungi231, tetapi sekarang **`newer=true`** memberi perintah membaca ulang; pembacaan baru berisi kesembilan ID. Tidak diklaim sebagai snapshot transaksi yang membekukan seluruh dataset.

Kontrol CP17 menunjukkan `changed=true` pada kelanjutan daftar yang berubah, muat ulang memuat9 tepat sekali, urutan commit biasa tetap7 tanpa changed, dan baris di luar filter tidak mengubah mark. Tes DOM menolak jawaban yang tidak cocok dan mengunci navigasi ketika daftar berubah. Lokasi `scripts/cp7-src/audit/audit.sql`, `src/auditTrailContract.ts`, `src/ConnectedAuditTrailPage.tsx`: mark jumlah/sumID dari himpunan append-only dibawa dalam snapshot/cursor; UI meminta Muat ulang. INV-T04/L02, SKN-18/26. Bukti r4: paging job117844478495, CP17 job117844186935, DOM job117844937444.

### ASTRA-R3-03 — S2 — angka WIP terlalu pucat: DITUTUP

**INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW**, ditambah inspeksi visual screenshot asli run Astra. Pada desktop dan390px, kuantitas10PCS, efektif10PCS, selesai dijahit4PCS, sisa final10PCS, nama model, serta pilihan tarif kini terbaca gelap pada kartu putih. Empat screenshot asli yang dipakai disimpan di `screenshots/`; screenshot rate-choice diperiksa pada resolusi aslinya.

Sensus browser mengunjungi48 menu pada desktop/HP dan build Enteng; WIP mengukur145 teks dengan rasio minimum5,17, di atas ambang4,5 yang dideklarasikan. Total teks diukur 7.521/7.330 (desktop/HP biasa) dan7.517/7.326 (Enteng);374/371 teks tidak diukur sesuai batas harness. Ambang seluruh menu hanya2:1; ini **bukan** klaim seluruh aplikasi lolos WCAG AA. Screenshot dengan nama sama dari run browser berurutan tidak dianggap dua bukti visual independen; kedua hasil pengukuran tersimpan terpisah dalam report/ledger.

Lokasi `src/connected-wip-status.css`, `pattern-page.css`, `hpp-pool.css`, `connected-bs-resolution.css`, `master-connected.css`. Foreground ditetapkan pada panel terang. Kontrol nominal dan tindakan tetap lulus; tidak ada expected uang yang diubah untuk menutup masalah warna. INV-UI01/02/03. Bukti CP17 job117844186935/artifact12158561747.

## Perubahan tambahan dan integrasi

**R4-05, guard internal: diterima untuk kesetaraan perilaku yang diuji; target waktu tetap OPEN.** Astra menambahkan tiga oracle sebelum run: matriks OWNER/ADMIN/STAFF/GUDANG/disabled/unknown/tanpa-user/custom read-only/anon/service-role; konteks transaksi, aktor dan PID; serta koneksi yang belum memperoleh XID dan konteks yang sedang ditahan backend lain. OWNER/ADMIN/STAFF aktif diizinkan; peran lain yang tidak memenuhi syarat ditolak; service-role mempertahankan pengecualian terdahulu. Konteks valid tanpa hak tulis tetap `42501:CP7_SALES_WRITE_DENIED`; grant lalu revoke dalam transaksi yang sama tidak memakai keputusan cache. Konteks aktor/PID/transaksi lain tidak meminjamkan otoritas. Backend lain benar-benar teramati idle-in-transaction; setelah commit juga tetap tidak bisa dipinjam.

Probe guard membandingkan definisi kandidat dengan pembungkus pendahulu khusus tes yang hanya membuang blok R4-05, serta memakai expected eksplisit. Itu fixture Native privat pada disposable, bukan bukti keterjangkauan HTTP. STAFF diaktifkan secara eksplisit di fixture karena role seed tidak aktif. XID sebelum panggilan null benar-benar diamati; probe tidak mengklaim XID tetap null setelah wrapper tes berjalan. Dua kontrol CP17 menjaga daftar10tabel konteks dan urutan dispatch: tambahan cabang/statement atau probe hilang ditolak. Sumber `scripts/cp7_internal_guard_bundle.py` dibaca lengkap; jalur lama tetap dipakai bila konteks relevan ada.

**Kinerja belum memenuhi target secara umum.** Pada run Astra P19 skala, contoh100 target/1hari: klik operasional selesai sekitar1,75 detik, tetapi pembanding SQL direct dengan jalur lengkap sekitar4,65 detik;300 target/1hari klik operasional sekitar6,18 detik. Pembanding full direct300 target mencapai batas8 detik dan menolak dengan jujur. Skala1000/5000 juga mempunyai penolakan batas yang dicatat, sementara jalur bertahap diuji tersendiri. `PASS` suite skala berarti hasil lengkap atau penolakan batas yang benar menurut kontraknya, **bukan target3 detik tercapai**. Tidak ada sampling/truncation yang dipakai sebagai hasil lengkap. D17-2 mengizinkan audit paket sekarang dan pekerjaan kecepatan dilanjutkan penulis di cabang terpisah; keputusan itu tidak diminta ulang dan tidak ditafsirkan sebagai penerimaan target yang belum tercapai.

**R4-Q1, pembacaan akhir pg_cron: diterima sebagai perbaikan alat.** `wait_recorded` menunggu catatan run terminal setelah jadwal dilepas dan sesi selesai, maksimal60 detik; syarat caller tetap ada run dan semuanya succeeded. Tidak mengubah status running menjadi sukses. K4/K6 yang dijalankan Astra membuktikan penjadwal benar-benar menyelesaikan pekerjaan serta dibersihkan. Perubahan ini tidak mengidentifikasi penyebab A2/AZ lama. Kontrol drain dan comparator lulus terpisah dari565 kasus: urutan dibandingkan stabil, member/definition/owner/ACL tetap diperiksa, kontrol negatif tetap sensitif. Selisih representasi ACL sesudah undo tidak dihapus dari `ANCILLARY_CONTROLS.json`.

**Uang–stok–HPP:** oracle Astra upah2×4+3×6+1×4+4×6=54, nota54, bayar54 satu efek, bank/payable0, bahan100+upah54+laundry20=HPP174, WIP0; payroll component qty20 tidak disamakan dengan10PCS fisik. Retained exact cents menolak saldo−0,01, pengganti sah menyisakan11,04; cutover WIB tepat batas, revoke replay, kontrol detektor dua basis tanggal, wave urutan terbalik53 dan konservasi10PCS/HPP160 lulus lagi.

**Sambungan layar:** browser menguji impor awal→WIP→ganti merek→jual→bayar→buku; BS→rework→nota→payroll; jahit10PCS/upah40→nota→payroll→kas0→tutup/buka; dan jual2PCS/invoice30.000→bayar→piutang0. Fixture bank/modal serta bagian upstream yang tidak diklik tetap ditandai `fixture_only` dalam ledger. Laporan, plan, AI, reminder, retention dan cleanup P19 juga diuji setelah perubahan guard; bukan klaim semua variasi dunia nyata telah dicoba.

**Lusin penjualan yang diminta owner:** `CP17_BROWSER_D14_5_SERIES_DOZENS_{DESKTOP,MOBILE}` dan pasanganEnteng lulus. Satu ukuran→12PCS; tiga ukuran→4/4/4; manual3/5/4→1lusin;4/5/4→1lusin1potong;2lusin→8/8/8. Simpan dan baca ulang server mempertahankan ukuran27=12,31=3,32=5,33=4; stok reservasi sesuai, merek lain tidak ikut, satu request dan GL tidak berubah. Bukti ini menutup klaim lama bahwa helper tersebut belum pernah diuji browser; tidak boleh memakai status lama itu sebagai status kandidat r4.

## Hasil merah yang tidak diubah menjadi PASS

**Kesalahan alat Astra:** 12 job P19 berstatus FAILURE karena unggahan kedua memakai nama artifact yang sama dengan unggahan lengkap pertama. Semua langkah kualifikasi dan cleanup selesai;183 hasil per kasus ada di arsip pertama yang digestZIP-nya diverifikasi. Klasifikasi `AUDITOR_TOOL / ARTIFACT_NAME_COLLISION`. Status job FAILURE tetap disimpan. Tidak ada rerun sesudah kasus berjalan, tidak ada perubahan expected, dan workflow yang dieksekusi dipertahankan. Ini bukan klaim18 job hijau. Wrapper guard/paging juga masih memuat string scope/file warisan risk; label, manifest dan ID kanonik menunjukkan cakupan sebenarnya, dicatat di `TOOL_NOTES.md`.

**Penulis:** enumerasi API dua halaman tepat116 run/115workflow pada kandidat;94success,22failure;179 job,157success.22log akar kegagalan dibaca dan diarsipkan.9no-merge guard dan11 path-scope guard historis diklasifikasikan `GUARD_BY_DESIGN`, bukan bukti penerus penuh lulus.1AF gagal mengambil artifactAE expiredHTTP410 (`BLOCKED_BY_TOOLING`).1CP6 full scenario run39180053859/job117830699716 mempunyai166PASS dan4INCOMPLETE: duaREADINESS_BROWSER memakai stackCP6 tanpa RPC recost/poolCP7, dan duaSALES_MANUAL_13 memakai UI lama. Status asli tetap utuh; pengganti CP7 dinilai pada stackCP7 penuh. `WRITER_FAILURE_REVIEW.json` memetakan setiap run/job dan akar, dengan log asli dan170 kasus disimpan. Tidak menyebut semua CI kandidat hijau.

T2 r2 dipertahankan dengan disposisi mentah lengkap dalam `retained/RETAINED_R2_T2_DISPOSITION.json`: marker kebijakan, counterexample kalender/AS, dan INCOMPLETE adjustment/AO/AR tidak dicat hijau. A2 dua kegagalan asli tetap OPEN; diterima sebagai bukan penghalang pembekuan oleh D13-10, tanpa menebak akar masalah.

## Vonis tujuh checkpoint dan batas yang tetap terbuka

| Checkpoint | Disposisi r4 | Bukti dan batas |
|---|---|---|
| CP1 baseline | **LULUS DENGAN BATAS BUKTI** | Tujuh hash sejarah CP1/CP2 cocok, supabase tidak berubah, baseline aligned dibangun dalam CI. G01 r2 retained; bukan preflight hosted baru. |
| CP2 backup lama | **BELUM LULUS PENUH; CP7C HOLD** | Bukti restorePG16/stub tersedia dari putaran lama; engine/image asli, owner/ACL penuh dan Storage round-trip belum diverifikasi Astra. Drill disposable r4 berbeda klaim dari restore backup lama. |
| CP3/3.5 absensi–HPP–payroll | **LULUS UJI ULANG DALAM CAKUPAN** | Celah pool publik tertutup; angka54→174 dan kontrol tanggal/nota/payroll lulus. |
| CP4/4.5 HPP/akses/master | **LULUS UJI ULANG DALAM CAKUPAN** |25 rute legacy DataAPI ditutup, lifecycle CP7 tetap hidup;82 fungsi privat masih tugasCP7C bersyaratD14-9. |
| CP5 stok/laundry/BS | **LULUS UJI ULANG DALAM CAKUPAN** | InverseFG di kedua arah, aktif-use, reopen/refinish, konservasi fisik dan rework/payroll lulus. |
| CP6 baseline/regresi/saldo awal | **QUALIFIED, batas lama dipertahankan** | Paket/rollback/restore disposable dan alur lintasCP diuji; G01/T2 r2 retained.12 entrypoint legacy belum mempunyai penerus penuh yang diverifikasi. |
| CP7 aplikasi/integrasi | **LULUS UJI ULANG r4 DENGAN BATAS** | Empat temuan Astra tertutup; guard, browser dan183 kasus P19 lulus. Target3 detik dan gerbang produksi belum selesai. |

Inventaris12batas legacy beserta apa yang diuji dan penerus parsialnya tetap pada `retained/LEGACY_COVERAGE_BOUNDARIES.json`. Label historis di file itu tidak diganti menjadi kelulusan r4. CP2 bukan “tidak ada bukti sama sekali”, dan juga belum “restore penuh terbukti”.

## Matriks invarian

| Keluarga | Disposisi dan bukti |
|---|---|
| INV-U01/U02/U04/U05/U08, H01/H02, S06/S07 | PASS pada oracle uang/stok/HPP bernama:54→174, exact cents,160/10PCS,wave53. |
| INV-U03/K06, SKN-12/27 | PASS untuk keluarga reopen yang diuji, termasuk inversepositif dan kontrol aktif. |
| INV-T02/A01/POL03 | PASS pada boundary pool/DataAPI dan guard yang diuji; D14-9privat tetap terbatas. |
| INV-T04/L02, SKN-18/26 | PASS untuk pemberitahuan daftar berubah dan reload; tidak mengklaim snapshotisolation. |
| INV-T01/C01/C02/C04/C06 | Qualified pada tanggalWIB,UUID/token,atomicity,revoke,race,cleanup/boundary yang bernama. |
| INV-UI01/UI02/UI03 | PASS untuk angka/aksi/lusin dan penutupan keterbacaanWIP; seluruhWCAG tidak diverifikasi. |
| INV-UI04 | Desktop/HP diuji; iPad/perangkat lain INCOMPLETE. |
| INV-A04/A05/C06, M04/M05 | Qualified pada runtime disposable,advisor,rollback; hosted/preflight aktual INCOMPLETE. |
| INV-D01/D03 | Kontrol negatif dua detektor tanggal Astra PASS, bukan seluruh detektor sistem. |
| INV-D02/D04 dan semua variasi detektor | INCOMPLETE menyeluruh; tidak ditutup oleh hitungan565. |
| INV-POL04/POL05 | Disposisi historis dan keputusan owner dipertahankan; penerimaan risiko tidak menjadiPASS. |
| INV-U06/U07,S01–05,H03–06,P01–03,T03,L01/L03–07,K01–05/K07,A02/A03,M01–03,R01–09,N01–02 | Bukti keluarga terdahulu + retest terpetakan. P19 memiliki183 kasus baru dieksekusi, tetapi seluruh input/role/volume,model,WA dan arsip tidak diklaim selesai universal. |

## Yang belum diperiksa dan prasyarat pemasangan

- Hosted Enteng, deployment, Drive, backup offsite CP7C dan pencabutan82 fungsi: tetap menurut keputusan owner, belum dijalankan auditor.
- RestoreCP2 pada engine/image asli dengan owner/ACL dan Storage lengkap; tidak meminta atau memakai kunci lama.
- Shadow run data cutover asli minimal satu periode serta rekonsiliasi semua angka; preflight hosted terbaru dan pemasangan penuh non-superuser pada baseline hosted nyata sesuai ProMax§12.10.
- Dua belas entrypoint legacy tanpa penerus penuh; seluruh detektor dengan kontrol negatif per variasi; iPad dan semua cabang role/volume yang tidak dicakup manifest.
- Target waktu analisis penuh3 detik; laporan benchmark bukan penerimaan target. Akar kegagalan A2/AZ lama tetap belum diketahui.
- Pengiriman WA nyata dan seluruh mutu/model/holdout/AI di luar kasus beku yang dijalankan; transport/preview lokal tidak dinyatakan sebagai pengiriman live.

Tidak ada pertanyaan kebijakan baru yang perlu dijawab owner untuk menuntaskan audit r4. D17-2, D13-9a, D13-10 dan D14-9 tidak dibuka ulang. Sebelum pemasangan Enteng, daftar prasyarat di `FINDINGS.json` dan gerbangProMax§12 tetap wajib diselesaikan/disposisikan secara sah; penutupan empat bug tidak mengesahkan produksi.

## Label asal bukti dan handoff

| Klaim | Asal |
|---|---|
|565 kasus pada7 run Astra | `INDEPENDENT_NATIVE_RERUN` atau `INDEPENDENT_DOM_RERUN`; oracle23 Astra/542 paket penulis dibedakan. |
| Penyebab/perbaikan,hash,grants,routing | `INDEPENDENT_SOURCE_REVIEW` atas kandidat dan patch37 path. |
|116runpenulis dan22akar merah | `REUSED_WRITER_EVIDENCE` untuk hasil runtime; enumerasi/pembacaan log dilakukan Astra. |
|CP1/CP2/G01/T2 dan matriks282r3 | Bukti auditor terdahulu retained, hash diperiksa; bukan eksekusi ulang r4. |
| Keputusan owner | Kutipan register penulis; `UNVERIFIED_OWNER_DECISION` untuk ucapan yang tidak didengar langsung. D17-2 juga ditegaskan dalam pesan handoff owner pada sesi ini. |

Fokus risiko berikutnya: optimasi kecepatan tidak boleh melemahkan pemeriksaan sumber/aktor/hash, batas8 detik, atau kelengkapan angka; pemasangan CP7C perlu bukti baseline/backup/aksesnya sendiri. Laporan ini dikunci sebelum cross-check auditor lain. Seluruh18 job telah selesai, tidak ada uji Astra yang ditinggalkan berjalan. Ringkasan owner≤10 kalimat ada di `HANDOFF_OWNER.md`.
