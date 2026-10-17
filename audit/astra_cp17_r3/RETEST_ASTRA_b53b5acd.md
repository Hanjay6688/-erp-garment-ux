# Astra — uji ulang dan integrasi CP1–CP7, r3

**Audit r3 selesai; vonis kandidat: TAHAN.** Ada **0 S0, 2 S1, 2 S2, 0 S3** dalam empat akar temuan terbuka: empat kontra-contoh Astra membuktikan tiga akar, dan pembacaan screenshot CI membuktikan satu masalah keterbacaan tambahan. Nomor PO otomatis dan dua reproduksi buka ulang lama sudah lulus; buka ulang belum lengkap untuk inverse penambahan stok. Ada jalur publik pool HPP yang melewati pembatas periode dan hak kelola, serta celah penelusuran Audit Trail. `production_go=false`, `feature_complete=false`; pemasangan Enteng dan CP7C tetap HOLD.

Kandidat `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`, tree `32f54240a60e01ab8b1ffad7267d285a669be520`. Dokumen penulis dibaca pada `64339905cc19e497f9fdb3599ff4a21cbf7da8ff`; enam perubahan terhadap kandidat hanya dokumen. Cabang auditor `audit/astra-cp1-7-r3-b53b5acd-20261018`. Laporan r2 yang dipertahankan: commit `bfa007f6eeecdccc3d0dbb52a98d17545ccae519`. Tanggal CI 17 Oktober UTC / 18 Oktober 2026 WIB. Panduan Pro Max SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`.

## Lingkup, identitas, dan cara menjalankan

R3 dibaca sebagai kelanjutan audit tujuh checkpoint; bukti r1/r2 yang tidak berubah dipertahankan dengan sumbernya, bukan diklaim sebagai eksekusi baru. `supabase/` identik dengan r2. Perubahan r3 pada facade, UI, paket pemasang dan alat uji ditelusuri tersendiri; daftar path ada di `IDENTITY.json`. Tujuh berkas bukti CP1/CP2 diperiksa ulang hash dan ukurannya di `CP1_CP2_HASH_RECHECK.json`.

Seluruh uji baru memakai GitHub Actions Ubuntu24.04, Supabase lokal PostgreSQL17.6.1.165, CLI2.116.0, Python3.12/psycopg3.2.10, Node 22 (teramati22.23.3), serta Chrome for Testing 151.0.7922.34 / Playwright Chromium build1234 dari package-lock kandidat. Identitas persis runtime dan instalasi ada pada log mentah. Enam workflow auditor mem-pin checkout aplikasi ke SHA/tree kandidat dan menolak perubahan tracked source. Karena connector tidak menyediakan dispatch, perubahan workflow auditor pada cabang sendiri memicu run; tidak ada commit pemicu pada cabang penulis.

Perintah pokok, beserta lingkungan dan seluruh langkah lengkap, tersimpan pada `.github/workflows/audit-astra-r3-{cp17,own,ui,matrix,risk,paging}.yml`: `python ../auditor/scripts/cp7_cp17_fix_probe.py`; runner `retained_runner.py`, `matrix_probe.py`, `risk_runner.py`, `audit_paging_runner.py`; Vitest dua berkas DOM Astra; `cp6_readiness_owner_drain_test.py` dan `cp6_auditor_public_state_test.py`. Sumber oracle dideklarasikan sebelum run pada enam manifest. Kasus Native/DOM lama dipertahankan byte-nya. Tidak ada rerun sesudah kasus berjalan dan tidak ada perubahan expected demi kelulusan.

Tidak membaca laporan, cabang, komentar, atau run auditor lain dari r3 sebelum lock. Laporan auditor putaran lama dan handoff penulis dibaca sebagai konteks. Tidak ada akses SQL hosted, mutasi Enteng/legacy, Drive, deployment, main, atau cabang penulis. Browser berkonfigurasi Enteng memakai backend sekali pakai: host proyek dipaksa ke loopback dan permintaan dibatasi harness. Itu bukti build Enteng pada backend uji, bukan bukti pemasangan pada Enteng. Cabang penulis diperiksa lagi pada akhir audit: tetap64339905cc19e497f9fdb3599ff4a21cbf7da8ff, sehingga identitas paket tidak bergeser.

## Hasil eksekusi per kasus

| Run auditor | Hasil | Asal oracle dan batas |
|---|---|---|
| [39053018929](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39053018929) CP17 | **321/321 PASS**, ID persis manifest | 153 Native, 34 race, 24 Auth HTTP, 55 browser, 55 browser Enteng. Oracle penulis beku, dijalankan auditor. Comparator dan drain dihitung terpisah. |
| [39053104594](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39053104594) retained Native | **11 PASS** | Oracle Astra lama, termasuk999→1000, dua inverse lama, konservasi10 PCS, exact cents, WIB, akses, detektor dan wave. |
| [39053104536](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39053104536) DOM | **4 PASS** | Oracle Astra: merek seri, save selama lookup, total lusin manual, label simulasi. |
| [39053177754](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39053177754) matriks browser | **282 PASS**, tiga job |47 menu × desktop1440/HP390 × DEMO_SIMULATION/DISPOSABLE_TEST/UAT_AUTH_SIMULATION. Semua halaman dirender; ini pemeriksaan masuk/menu/layout/read, bukan282 perjalanan transaksi. |
| [39053360685](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39053360685) risiko tambahan | **1 PASS, 3 COUNTEREXAMPLE** | Dua Native dan dua AuthHTTP; empat kasus, walaupun nama job turunan masih menyebut11. Oracle/arithmetic Astra, fixture/transport penulis. |
| [39053620397](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39053620397) pagination | **1 COUNTEREXAMPLE** | Jadwal tiga sesi sungguhan; transaksi master normal, trigger audit Native, tanpa menyisipkan baris audit buatan. |

**Oracle Astra: 302 ID unik, 298 PASS dan 4 COUNTEREXAMPLE.** Tidak dijumlahkan dengan CP17, predecessor checks, ataupun hasil r2. Dua job counterexample berkesimpulan FAILURE; summary wrapper `INCOMPLETE` berarti syarat semua-kasus-PASS tidak tercapai, bukan kehilangan kasus atau error alat:4/4 dan 1/1 teramati, `error=null`, `cp6_restored=true`, `advisor_gate=true`, cleanup tuntas. Setiap status mentah dipertahankan.

`CP17_CASES.json.gz` menyimpan321hasil beserta asal oracle penulis; `CP7_CP17_FIXES.json.gz` memuat report runtime lengkap dan cleanup semua database/Auth. `INDEPENDENT_CASES.json.gz` menyimpan setiap observasi, ID, asal oracle, run/job dan nomor baris log. `RAW_LOGS.tar.xz`/`RAW_LOG_INDEX.json` menyimpan log utuh. `REPORT_LOCK.json` mencatat hash seluruh paket; artefak CI beserta hash/masa simpan berada pada register run.

## Temuan terbuka

### ASTRA-R3-01 — S1 — API publik lama pool HPP melewati pembatas periode dan hak kelola

**TERBUKTI, NATIVE_QUALIFIED, INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** Satu keluarga akar masalah dengan dua reproduksi. Keberadaan wrapper sudah diakui penulis; audit ini membuktikan dampaknya serta menguji apakah penundaan D14-9 benar-benar mencakupnya. Berhubungan dengan FABLE-012, tetapi tidak menganggap penerimaan atas82 fungsi privat otomatis menerima wrapper publik ini.

Lokasi: `scripts/cp7-src/hpp-pool/pool.sql` fungsi `access_now` dan pemeriksaan periode dalam `command`; `scripts/cp7_hpp_pool_bundle.py` daftar `CP4_WRAPPERS` dan verifikasi yang mempertahankan grants; `supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql:484–544` wrapper/grant lama; Native create/activate di migrasi `20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql`. Pembaca akhirnya adalah pool aktif, biaya PO dan jurnal `ATTENDANCE_HPP_POOL`.

1. `ASTRA_R3_POOL_PUBLIC_CLOSED_PERIOD`, job117456272451: pool absensi1000 / 10 PCS, periode15 Oktober, buku ditutup sampai15 Oktober. OWNER dengan Auth nyata memanggil facade CP7:HTTP400 `CP7_HPP_POOL_PERIOD_CLOSED`, boundary tetap. Melalui `public.erp_create_attendance_hpp_pool_v1` kemudian `public.erp_activate_attendance_hpp_pool_v1`, keduanya **HTTP200**:DRAFT→ACTIVE, biaya aktif PO1000, jurnalPOSTED bertanggal ekonomi15 Oktober dan tanggal buku18 Oktober. Tidak ada grant skema khusus untuk tes. Kedua wrapper executable oleh `authenticated` dan terbukti tersedia melalui Data API.
2. `ASTRA_R3_POOL_PUBLIC_REVOKED_MANAGE`, job yang sama: ADMIN memiliki hak lihat; hak `finance.hpp.manage` dicabut setelah preview. Facade CP7 menolakHTTP403 `CP7_HPP_POOL_DENIED` tanpa efek. Wrapper create lama tetapHTTP200 dan benar-benar menambah DRAFT1000 / 10 PCS pada tabel Native. Kasus kedua tidak mengklaim aktivasi berhasil karena hanya create yang diuji.

Ini bukan serangan tanpa login atau bukti hosted telah rusak. Dampak yang terukur adalah aplikasi menerima penulisan yang kontrak CP7-nya melarang: biaya/jurnal periode tertutup bisa ditambahkan lewat jalur alternatif, dan pencabutan hak kelola tidak berlaku pada seluruh jalur. S1: boundary penting atas penulisan keuangan dan izin dapat dilewati. Native tetap memindahkan tanggal buku ke periode terbuka sesuai desainnya; audit ini tidak menunjukkan nominal salah atau arsip penutupan berubah, sehingga tidak membuat klaim S0. Yang gagal adalah aturan CP7 yang mewajibkan semua aksi pool periode tersebut ditolak, serta hak kelola yang dicabut. Seluruh laporan historis dan seluruh detektor tidak diklaim telah diukur. INV-T02, INV-A01, INV-POL03; POLA pemeriksaan semua writer (§4.2).

D14-9 secara verbatim mengizinkan penundaan **“berdasarkan bukti auditor bahwa jalur tersebut tidak dapat dijangkau dari internet”** dan menetapkan pencabutan sebagai prasyarat jika jalurnya menjadi terjangkau. Gate `cp7_access_inventory.exposure_gate` memeriksa apakah skema `erp` diekspos; kelulusan gate itu tidak menyatakan wrapper `public` telah aman. Ini otorisasi bersyarat, sedangkan wrapper berada di `public` dan probe membuktikan keterjangkauannya melalui API biasa. Klaim README r3 bahwa wrapper tersebut ikut ditunda ke CP7C berdasarkan D14-9 **tidak cukup didukung keputusan itu**. Keputusan lama atas82 fungsi `erp` tidak dibuka ulang; pengecualian tersebut tidak diperluas oleh auditor atau penulis.

Usulan: tutup seluruh writer publik alternatif (create/activate/cancel dan akses legacy lain yang satu keluarga) atau terapkan boundary hak/periode/review yang sama pada lapisan Native bersama, dengan admission/rollback terdaftar. Jangan hanya menyembunyikan tombol. Jalankan dua probe ini tanpa perubahan oracle, tambah aktivasi/pembatalan/replay setelah hak/periode berubah serta kontrol sah CP7 create→activate→cancel→replacement. Penolakan harus atomik, jalur sah dan jurnal inversenya tetap tepat.

### ASTRA-R2-01 — S1 — Buka ulang PO belum menerima inverse penambahan stoknya sendiri

**MASIH TERBUKA, reproduksi baru NATIVE_QUALIFIED, INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** Dua reproduksi r2 asli sudah PASS pada r3; keluarga perbaikannya belum lengkap.

`ASTRA_R3_REOPEN_POSITIVE_ADJUSTMENT_INVERSE`, run39053360685/job117456272451: PO FINISHED dengan10 PCS, HPP120/basis10. Penyesuaian **+2** menghasilkan12 PCS; REVERSE sah membuat **−2 yang menunjuk ID +2 tadi **, saldo kembali10 dan HPP tetap120/basis10. Workspace masih `eligible=false`, `FG_USED qty2`; command publik baru ditolak `CP7_PO_REOPEN_BLOCKED`, tanpa efek parsial. Tidak ada pemakaian hilir aktif yang ditambahkan oleh skenario.

Lokasi `scripts/cp7-src/cutting-correction/po-reopen.sql:46–51`, `reopen_po_snapshot`: setiap mutasi negatif dianggap pemakaian, dikurangi inverse miliknya. Ini memperbaiki negatif→inversepositif, tetapi negatif yang **merupakan inverse dari penambahan positif** masih dihitung. Command memakai snapshot yang sama. INV-K06/SKN-12/SKN-27 dan D15-4/R3-02: koreksi sah macet, bukan stok hilang. S1 menurut aturan alur koreksi penting yang tertahan.

Usulan: hitung provenance pemakaian aktif beserta pasangan inversenya di kedua arah. Jangan menetralkan outflow aktif memakai inflow yang tidak terkait. Pertahankan dua kasus r2, probe positif ini, kontrol pemakaian aktif/parsial, dua draft, concurrency, periode, token, dan reopen→finish dengan stok/HPP/GL yang tepat. Kualifikasi oracle gross income/expense dari r2 tetap tercatat; audit ini tidak memberi persetujuan kebijakan keuangan baru atas klasifikasi tersebut.

### ASTRA-R3-02 — S2 — Audit Trail melewatkan commit terlambat di antara halaman tanpa pemberitahuan

**TERBUKTI, NATIVE_QUALIFIED, INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** `ASTRA_R3_AUDIT_LOWER_ID_LATE_COMMIT`, run39053620397/job117457024810. Semua penulisan lewat facade master normal dan trigger audit Native, bukan insert ke audit table.

Jadwal yang diamati: tujuh seed sudah commit; transaksiA memperoleh auditID 231 lalu ditahan (`idle in transaction`); transaksiB memperolehID 232 lalu commit. SesiC membaca halaman pertama dengan cutoff 232:ID[232,230,229], total 8, sementara231 benar-benar tidak terlihat. A kemudian commit. Melanjutkan cursor sampai akhir menghasilkan[228,227,226] lalu[225,224]. Total menjadi9, tetapi **231 tidak pernah dikunjungi**, dan `snapshot.newer=false` pada seluruh halaman berikut. Pembacaan ulang dengan cutoff yang sama serta SQL Native memuat kesembilan ID, termasuk231.

Akar `scripts/cp7-src/audit/audit.sql:107–145`: cutoff memakai `max(id)` yang terlihat, cursor `(changed_at,id)`, indikator baru hanya mencari `id>cutoff`. Sequence ID bukan urutan commit; row lebih kecil yang terlambat commit jatuh di belakang posisi yang sudah dilalui tanpa memenuhi indikator baru. UI `src/ConnectedAuditTrailPage.tsx` mengandalkan snapshot/cursor ini. SKN-18/SKN-26; kontrak daftar stabil dan pemberitahuan data baru gagal. Bukan penghapusan audit Native, bukan bukti seluruh ekspor salah.

Usulan: pakai snapshot/paging yang benar-benar mempertahankan himpunan atau deteksi perubahan himpunan yang mewajibkan reload; pilihan teknis harus menjaga batas akses dan read-only. Uji jadwal ini apa adanya, commit urutan biasa sebagai kontrol, duplicate/omission sampai halaman terakhir, indikator reload, filter dan revoke. Jangan sekadar mengubah ekspektasi jumlah supaya8 dianggap lengkap setelah source sudah9.

### ASTRA-R3-03 — S2 — Angka WIP dan progres jahit terlalu pucat pada panel putih

**TERBUKTI secara visual pada browser CI, INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW.** Bukti run39053018929/job117455268044/artifact12109092575, screenshot asli `screenshots/CP17_BROWSER_R3_09_RATE_CHOICE_MOBILE_CHOICE.png` dan crop `screenshots/WIP_LIGHT_TEXT_CROP.png`. Pada390px, angka KUANTITAS10pcs, EFEKTIF10pcs, SELESAI DIJAHIT4pcs, FINAL SKU TERSISA10pcs, nama/model dan beberapa judul panel nyaris menyatu dengan latar putih. Ini kesulitan membaca angka yang benar, bukan salah perhitungan.

Sumber `src/ConnectedWipStatusPage.tsx:277,285–289`; `.cwip-kpis article` dan `.cwip-list>article` pada `src/connected-wip-status.css` memakai `background:#fff`, sedangkan `strong`/teks fakta tidak menetapkan warna gelap dan mewarisi foreground terang `#f4f6fb` dari `src/styles.css`. Screenshot membuktikan hasil kombinasi tersebut pada build sebenarnya. Tidak mengklaim menghitung rasio kontras atau kelulusan standar aksesibilitas, dan tidak mengklaim cacat baru diperkenalkan oleh r3.

Kasus otomatis rate-choice tetap **PASS** karena nominal, request, dan state Native memang benar; assertion itu tidak memeriksa keterbacaan warna. Temuan manual ini **tidak menambah jumlah ID atau kontra-contoh otomatis**. Perbaiki token foreground/background halaman WIP secara konsisten, lalu periksa ulang KPI, nama, fakta potong/jahit, dan panel pilihan tarif di desktop serta HP. Tidak perlu mengubah oracle nominal.

## Penutupan temuan lama dan keputusan owner

| Butir | Disposisi r3 | Dasar dan batas |
|---|---|---|
| ASTRA-R2-02 / R3-01 nomor PO | **DITUTUP** | Oracle lama998→999→1000 selesai, stok10→8→6; formatter tidak memotong digit. Kasus r3 tambahan menguji batas dan concurrency. |
| ASTRA-R2-01 / R3-02 reopen | **DITUTUP SEBAGIAN** | Dua kasus asli PASS; inverse +2→−2 masih gagal sesuai temuan di atas. |
| ASTRA-C17-01/02 lusin, merek, pending save | **TETAP TERTUTUP** | DOM Astra asli PASS; retest browser CP17 memeriksa hasil server. |
| ASTRA-C17-03 angka contoh / D16-1 | **Kontrak aktivasi r3 terverifikasi pada uji** |46 menu connected dan DashboardNOTICE; tidak ada17 menu lama yang disembunyikan. Dashboard masih pemberitahuan, bukan ringkasan angka ERP lengkap. |
| ASTRA-C17-04 master / C17-05 FINISH | **TETAP TERTUTUP pada kasusnya** | Retained Native dan retest CP17. Keluarga reopen dicatat terpisah. |
| ASTRA-C17-07 / R3-04 pool UI | **DITUTUP untuk kekurangan layar dan perjalanan yang dinyatakan** | Desktop dan HP pada kedua build PASS: create→activate→cancel→koreksi kebijakan mandor lewat master→replacement, 1000/10 menjadi1000/20 dengan500/500, lineage/correction_of tepat, lima UUID berbeda, role KEUANGAN tanpa panel, tanpa overflow. Jalur API alternatif tetap temuan tersendiri. |
| R3-03 sambungan dan menu baru | **LULUS pada perjalanan yang diuji; Audit Trail masih terbuka** | Dua rantai dan kontrol penolakan CP17 PASS pada kedua build, ditambah 282 pemeriksaan masuk. Detail fixture dan angka di bawah; pagination commit terlambat gagal pada probe Astra. |
| R3-05 QC Final SKU / Nota aksesori | **DITUTUP pada cakupan kasus** | QC desktop/HP:10FG, HPP120, satu jurnal; lost answer nyata pada desktop dan replay UUID tanpa efek kedua. Nota aksesori2100 memotong upah6000 sehingga dibayar3900; nota1500 yang dibalik tidak ikut; bank dan piutang mandor0. |
| R3-06 alat browser laundry | **Perubahan alat ditelaah** | Helper diperbaiki; assertion bisnis tetap, bukan pelonggaran oracle untuk mengubah merah menjadi hijau. |
| R3-07 receipt | **DITUTUP untuk kelengkapan enumerasi API** | Dua halaman API dibaca sendiri:117 run/115 workflow/95 success/22 failure pada b53b5acd. |
| R3-08 penerus workflow lama | **Pemetaan tersedia; regresi arsip belum penuh** |37 entry:14 PASS,11 SUCCESSOR_MAPPED,12 BOUNDARY_NO_SUCCESSOR. Pemetaan memakai receipt r2 dan mengaku tidak menjalankan ulang; tidak disamakan dengan37 kelulusan r3. |
| D16-2/3/4 tarif lama/baru | **LULUS pada kasus backend dan layar** |2×4+3×6+1×4+4×6=54, Nota54, qtykomponen20 vsfisik10, PAY54sekali, bank0, utangmandor0, material100+upah54+laundry20=HPP174, WIP0; tarif historis tidak berubah. |
| D16-5 tab Tutup Buku | **LULUS pada kasus** | Desktop/HP dan kedua build PASS; legacy route, hak view/manage, tutup/buka, history dan arsip diuji. Tampilan HP juga dibaca visual. |

Lusin yang diminta owner bukan lagi sekadar rencana: bukti r2 terkunci sudah memperagakan3 ukuran→4/4/4, manual3/5/4→1 lusin,4/5/4→1 lusin 1 potong,2 lusin→8/8/8, dan satu ukuran→12 PCS, lalu simpan/baca ulang. R3 mempertahankan DOM total manual dan pemisahan merek. Field helper sementara dapat tetap2 sementara total manual terbaca1 lusin; yang mengikuti qty manual adalah total seri. Seluruh kasus lusin tersebut dijalankan lagi pada r3: desktop/HP dan kedua build PASS, termasuk Qty tersimpan {27:12,31:3,32:5,33:4}, merek lain tetap5, satu request dan GL tidak berubah. Bukti pengganti ini memenuhi cakupan pensiun SALES_MANUAL_13 yang bersyarat; hasil INCOMPLETE selector historis tetap disimpan.

Rantai layar r3 yang benar-benar dijalankan: (1) jahit10 ×4 =upah40 → Nota → payroll hitung/setujui/bayar40 → bank0 → laporan → tutup/buka; cutting/pickup/BOM/rate serta modal tepat40 disiapkan fixture, bukan layar dalam rantai ini. (2) FG2 → invoice30000 → pembayaran30000 → bank30000 dan AR debit30000/kredit30000/saldo0 pada HP; FG hasil opname dan master pelanggan/bank adalah fixture. Nota aksesori menelusuri post→reverse→post→payroll sampai pengurang2100 dan pembayaran3900. Keberhasilan itu tidak berarti seluruh master/stock awal dibuat lewat UI atau seluruh cabang bisnis telah menjadi satu perjalanan.

Kontrol tambahan pada run CP17 juga PASS: comparator `CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER` memisahkan order-only/content dan tetap peka pada definition, member, owner serta ACL; drain wait/retry/refusal berhenti pada kondisi yang dideklarasikan. Ini terpisah dari321kasus. `ANCILLARY_CONTROLS.json` mempertahankan hasil lengkap, termasuk beda representasi ACL setelah undo; tidak disederhanakan menjadi katalog mentah identik. A2 tetap belum diketahui akar kegagalan aslinya.

321 kasus penulis yang PASS tidak membantah empat kontra-contoh Astra: skenario positif→inverse berbeda dari dua skenario negatif/reservasi lama; writer facade pool tidak menelusuri wrapper alternatif; race audit penulis tidak menyertakan commit ID lebih tinggi sebelum halaman pertama saat ID lebih rendah masih tertahan. Tidak ada oracle yang diubah setelah hasilnya terlihat.

## Receipt penulis dan merah yang tidak diubah menjadi PASS

API kandidat dipaginasi sendiri;117 run mencakup115 workflow.95 success dan22 failure. Angka81kelompok utama penulis tidak berarti semua run hijau.22 log job penyebab failure dibaca dan diarsipkan sebagai `WRITER_RAW_LOGS.tar.xz` (tidak mengklaim seluruh job pendamping setiap run sudah dibaca).

- 20 job berhenti pada guard scope historis:9 aturan no-merge dan11 daftar path. Klasifikasi `GUARD_BY_DESIGN` atas entrypoint sejarah; bukan bukti seluruh fungsi penerus telah lulus. Hasil predecessor yang sempat berjalan tetap tercatat.
- 1 `CP6 AF Posted Child Family` gagal mengunduh artifactAE yang expired,HTTP410: `BLOCKED_BY_TOOLING / LEGACY_ARTIFACT_UNAVAILABLE`, bukan penemuan produk. Ini tetap salah satu coverage boundary.
- 1 run penuh `CP6 Auditor Scenario`,39044984302/job117431817166: **166 PASS,4 INCOMPLETE**. Dua `READINESS_BROWSER:*_NATIVE_POLICY_STATES_FINANCE_NOTE` memakai stackCP6 tanpa RPC recost/poolCP7; dua `BF_BROWSER:SALES_MANUAL_13_*` memakai selector lama. Klasifikasi `AUDITOR_TOOL / SUPERSEDED_UI_PATH`; empat status asli tetap utuh. Kandidat CP7 harus dinilai dengan kasus pengganti pada stack yang lengkap, bukan sample 5atau warna job.

T2 yang sudah dieksekusi sendiri pada r2 tidak dijalankan ulang tanpa perubahan pada sumbernya. `RETAINED_R2_T2_DISPOSITION.json` mempertahankan seluruh hasil mentah dan rujukan keputusan:12 DATE_POLICY_REVIEW_REQUIRED,8 AS COUNTEREXAMPLE,12 kalender COUNTEREXAMPLE,1 adjustment INCOMPLETE,4 AO INCOMPLETE,1 AR INCOMPLETE; oracleC0/ARreplacement dipetakan tanpa mengganti hasil lama. Bukti ini berlabel **bukti auditor terdahulu yang dipertahankan**, bukan run baru pada b53b5acd. A2 dua log gagal asli tetap OPEN dan bukan penghalang berdasarkan D13-10; akar sebab belum diketahui. Mitigasi drain tidak dianggap penemuan penyebab kegagalan AZ lama.

## Vonis CP1 sampai CP7

| Checkpoint | Vonis putaran r3 | Bukti dan batas |
|---|---|---|
| CP1 baseline | **LULUS DENGAN BATAS BUKTI** | Tujuh hash sejarah sama; supabase tidak berubah; setiap runtime dibangun dari aligned baseline tersimpan. G01 r2 dipertahankan; bukan pembacaan hosted terbaru. |
| CP2 backup lama | **BELUM LULUS PENUH; CP7C HOLD** | Laporan restorePG16/stub lama tersedia, bukan nihil bukti. Engine/image asli, owner/ACL lengkap dan Storage round-trip masih belum diverifikasi Astra. Tidak meminta/memakai kunci lama. |
| CP3/3.5 absensi–HPP–payroll | **TAHAN pada integrasi pool** | Upah campuran→nota→bayar→HPP 174 lulus tepat; jalur publik pool melewati boundary periode/hak. |
| CP4/4.5 HPP/akses/master | **TAHAN pada writer pool publik** | Izin facadeCP7 lulus kontrol, tetapi wrapperCP4 bisa melewatinya. Penundaan82 fungsi privat D14-9 tidak menutup bukti ini. |
| CP5 stok/laundry/BS | **Perbaikan lama lulus; koreksi reopen belum lengkap** | Konservasi fisik, dua kontrol sisa6, laundry/HPP dan wave lulus. Inverse penambahanFG masih mengunci reopen. |
| CP6 baseline/regresi/saldo awal | **QUALIFIED dalam cakupan yang dipetakan** | Baseline/paket/rollback dan jalur lintasCP dipakai pada CI; bukti G01/T2 r2 dipertahankan.12 entrypoint legacy masih tanpa penerus penuh; tidak diberiPASS. |
| CP7 aplikasi/integrasi | **TAHAN** | Empat akar temuan; bukti render/fitur yang lulus tidak berarti seluruh fitur atau produksi siap. |

## Matriks invarian dan batas pemeriksaan

Status PASS berikut berarti kasus bernama yang diuji, bukan pembuktian semua input/peran/volume. Detail hasil setiap kasus ada di ledger. Gerbang global Pro Max §12 tetap belum terpenuhi.

| Invarian | Status | Bukti / batas |
|---|---|---|
| INV-U01/U02/U04/U05/U08, H01/H02, S06/S07 | PASS pada oracle Astra | Upah 54, satu PAY, bank/payable 0, HPP 174/WIP 0; retained10 PCS/HPP 160, exactcents, wave 53. |
| INV-U03/K06, SKN-12/27 | **FAIL pada kelengkapan alur koreksi** | Efek stok/HPP inverse pulih, tetapi reopen setelah inversepositif ditolak. |
| INV-T01/C01/C02/C04/C06 | PASS pada kasus terkait | WIB, duplicateUUID, token/atomicity, session/boundary/restore. Tidak menggeneralisasi ke seluruh writer. |
| INV-T02/A01/POL03 | **FAIL** | Dua probe wrapper pool publik; facadeCP7 menolak dengan benar. |
| INV-T04/L02, SKN-18/26 | **FAIL untuk daftar audit stabil** | ID 231terlewat tanpa newer; bukan klaim kerusakan arsip keuangan. |
| INV-UI01/UI02/UI03 | Qualified menurut angka/aksi; **keterbacaan WIP FAIL** | DOM identitas/lusin/pending dan lifecycle PASS; screenshot WIP membuktikan teks terlalu pucat. Render/angka benar tidak menjamin mudah dibaca. |
| INV-UI04 | **INCOMPLETE untuk iPad** | Desktop 1440 dan HP 390 diuji; tidak ada klaim semua perangkat. |
| INV-A04/A05/C06 | Qualified dalam runtime audit | Advisor gate/boundary/restore diperiksa; grant pool publik justru masalah yang terbukti.82 pencabutan aktual belum dilakukan. |
| INV-D01/D03 | PASS terbatas | Kontrol negatif dua basis tanggal Astra; bukan seluruh detektor sistem. |
| INV-D02/D04 dan seluruh variasi detector | **INCOMPLETE secara menyeluruh** | Tidak mengklaim semua detektor diuji pada seluruh skenario. |
| INV-M04/M05 | Qualified rekonstruksi CI; hosted **INCOMPLETE** | Baseline snapshot tersimpan dan disposal; tidak ada preflight hosted terbaru atau maintenance nyata. |
| INV-POL04/POL05 | Status historis dipertahankan | T2 disposition tidak menyulap non-PASS menjadi PASS; D14-9 dibaca sesuai syaratnya. |
| INV-U06/U07, S01–05, H03–06, P01–03, T03, L01/L03–07, K01–05/K07, A02/A03, M01–03, R01–09, N01–02 | Bukti keluarga lama + retest terpetakan; **bukan kelulusan universal r3** | CP17/retained dan laporan r2 menutup kasusnya saja. Backup,model/AI,notifikasi serta seluruh arsip regresi yang tidak berubah tidak semuanya dieksekusi ulang. |

Yang belum diperiksa di r3: hosted/Drive/deployment/CP7C; restore CP2 engine asli dan Storage; shadow run data cutover asli satu periode; semua cabang transaksi/role/volume dan iPad; seluruh 12 penerus arsip yang belum tersedia; seluruh detektor/kasus rekomendasi/AI/WA; akar kegagalan A2/AZ; revoke82 fungsi privat aktual. Limit tampilan/picker dan runtime fixture yang dijelaskan modul tidak diberi klaim penuh atas volume tak terbatas. Dashboard tetap NOTICE. Ini daftar batas bukti, bukan izin penundaan baru.

## Asal bukti, tindak lanjut, dan owner

| Klaim | Label asal bukti | Rujukan |
|---|---|---|
| Hasil enam run milik Astra | `INDEPENDENT_NATIVE_RERUN` | Run di tabel; oracle penulis dan Astra dipisahkan. |
| Penyebab source, routing, grants, hash | `INDEPENDENT_SOURCE_REVIEW` | Kandidatb53b5acd, IDENTITY, lokasi temuan. |
| Enumerasi dan22 failurepenulis | `REUSED_WRITER_EVIDENCE` untuk hasil runtimenya; pembacaanAPI independen |117 run,22 log, dua API page. Bukan penutup gate runtime. |
| CP1/CP2/G01/T2 r2 | Bukti Astra terdahulu dipertahankan, bukan rerunr3 | Lockbfa007f6 dan hashrecheck. |
| Keputusan owner di register | Kutipan register penulis; `UNVERIFIED_OWNER_DECISION` untuk ucapan yang tidak didengar langsung di sesi ini | Hash register di IDENTITY; tidak diubah, tidak diminta ulang. |

Satu temuan visual tambahan dicatat terpisah dari302kasus otomatis Astra. Enam run dan delapan job auditor sudah selesai; tidak ada uji tersisa berjalan. Tidak ada pertanyaan kebijakan baru yang perlu menghentikan audit. Rekomendasi: perbaiki empat akar temuan dan jalankan ulang kasus yang tersimpan, lalu audit kandidat baru. Penundaan hosted/backup/82 fungsi tetap menurut keputusan yang ada; perbaikan wrapper publik tidak memerlukan owner mengulangi keputusan yang telah bersyarat itu. Fokus tambahan paling berisiko adalah kesenjangan boundary antara facade CP7 baru dan writer publik lama, provenance inverse koreksi, serta urutan commit yang berbeda dari urutan sequence.

Ringkasan owner ≤10 kalimat ada pada `HANDOFF_OWNER.md`. Tidak ada job audit yang dibiarkan berjalan.
