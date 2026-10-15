# AUDIT SOL — CP1–CP7 — kandidat dfab13bf — 16 Oktober 2026 WIB

**Putusan: HOLD. Pekerjaan pemeriksaan putaran ini selesai; fitur dan gerbang penerimaan penuh belum selesai.**
`audit_round_work_finished=true`, `feature_complete=false`, `audit_complete=false`, `production_go=false`.
Semua pekerjaan auditor yang didispatch sudah terminal; tidak ada hasil CI yang masih ditunggu.

## Identitas, lingkungan, dan independensi

- Produk: `dfab13bf62398a69a02bf6221c06d29075e5e40b`, tree `886f83312958b53781a450a4ea2a8fb2147b3be3`.
- Cabang auditor: `audit/sol-cp1-7-combined-dfab13bf-20261016`. SHA workflow berbeda dari SHA produk dan dicatat per run di `RUN_REGISTER.json`.
- Handoff writer dibaca pada `6562833695f76007b079316d1bef6b1aa8206223`; perubahan setelah kandidat pada input itu hanya dokumen. Kandidat lama `66baa8e8` tidak dipakai sebagai kandidat penerimaan.
- Panduan Pro Max SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`; register owner SHA-256 `c8b5e5065d2fec088b26adb5c3b696afb409f3542ca3762d4097331c53afa3a8`.
- Ubuntu 24.04, Supabase CLI 2.116.0, PostgreSQL image 17.6.1.165, Python 3.12/psycopg 3.2.10, Node 22 dan Chromium CI. Uji diagnostik kecil memakai PostgreSQL 17.6 biasa; klaimnya hanya penyimpanan error, bukan keseluruhan ERP/Supabase.
- Native memakai database sekali pakai. Real Auth/PostgREST/browser hanya pada kelompok yang menyatakannya. Inventory 48 menu memakai **Auth/access tiruan dan semua RPC bisnis 403**; tidak pernah menyentuh hosted.
- Tidak membaca laporan, cabang, run, artifact atau komentar auditor lain dari putaran ini. Input writer dan laporan Sol lama yang sudah dikunci dibaca sebagai acuan, dengan label asal. Tidak mengklaim isolasi akses teknis dari repo bersama.
- Tidak menulis produk, writer, main, deployment, atau Supabase hosted. `src`, `supabase`, `scripts`, `tests`, package files tetap sama dengan kandidat. Perubahan auditor hanya probe/laporan sendiri dan workflow `audit-sol-*`; bukti tree ada di `IDENTITY_END.json`.

Perintah utama: own workflows pada `RUN_REGISTER.json`; `retest_probe.py`, `independent_cases.py`, `correction_qualification_probe.py`, `correction_http.py`, `owner_baseline_qualification.py`, `diagnostic_probe.py`, `menu_inventory.mjs`; inspeksi `git diff`, `rg`, hash sumber dan pemeriksaan outcome/artifact. Script `build_evidence.py`, `build_matrices.py`, `build_review_registers.py` hanya menyusun laporan dari bukti asli, tidak menjalankan ulang kasus bisnis.

## Ringkasan temuan

| Asal | S0 | S1 | S2 | S3 |
|---|---:|---:|---:|---:|
| Baru dari Sol | 0 | 2 | 2 | 1 |
| Sudah diungkap writer, diverifikasi Sol | 1 | 2 | 0 | 0 |

S0 yang sudah diketahui adalah **angka contoh keuangan yang ditampilkan sebagai saldo buku di mode Enteng**; bukan klaim bahwa database Native/hosted diam-diam berubah. Badge global berbunyi “UAT · MODUL TERPILIH LIVE”, tetapi dua halaman uang tersebut tidak memberi label simulasi lokal. Dua S1 baru: koreksi pembayaran sah tertahan dan jalur PO harian baru tidak tersedia. S3 baru berada pada alat baseline, bukan mesin transaksi ERP.

## Vonis CP1–CP7

| CP | Disposisi | Bukti dan batas |
|---|---|---|
| CP1 | Identitas/sumber/build dalam cakupan terverifikasi | Tree produk cocok, tiga mode benar-benar dibuild pada CI; bukti baseline lama dipertahankan dengan tanggalnya. Bukan fresh preflight hosted. |
| CP2 | Arsip lama terverifikasi; functional restore original tetap INCOMPLETE | Bukti arsip Sol lama tidak dihapus. Restore disposable T3 saat ini lulus, tetapi itu bukan restore backup asli CP2. Pekerjaan backup/kunci/cutover mengikuti penundaan CP7C owner. |
| CP3/3.5 | Core/regresi terikat bukti, tanpa klaim universal | Native `supabase/` byte-identik dari audit lama. Bukti lama dan disposisinya dipertahankan; F03/CP17 menguji jalur terdampak pada stack sekarang. |
| CP4/4.5 | Auth/identitas dalam cakupan teruji | F01/F02 lama terikat kandidat sebelumnya; current declaration/catalogue, real HTTP dan exposure gate diperiksa. Pencabutan 82 EXECUTE tetap pekerjaan CP7C sesuai D14-9. |
| CP5 | Core dan G1 dasar teruji; varian aplikasi belum lengkap | Upah per komponen, parsial, pembatalan, RWK01 dan rewash Native teruji. Wave BF SKU/ukuran masih ditolak G1; beberapa sambungan belum punya browser positif final-stack. |
| CP6 | Uji ulang tiga perbaikan Sol lulus dalam batasnya | BE 16/16 lengkap, pemasangan 58 berkas oleh owner non-superuser lulus, penyimpanan diagnostik teruji. Penyebab kegagalan AZ lama tetap tidak diketahui; tidak dibuka ulang sebagai kegagalan pemasangan baru. |
| CP7 | HOLD penerimaan penuh | Koreksi pemasukan sah gagal; PO harian baru tak punya jalur biasa; UAT contoh/master harian/wave BF tetap terbuka. |

## Hasil uji sendiri dan batas hitung

| Kelompok | Hasil per outcome | Batas klaim |
|---|---|---|
| F03 final stack, 8 bucket | 447 kasus retained + 3 smoke PASS, 122 eksekusi kelompok | Eksekusi independen Sol, rancangan provider/oracle lama. Bukan 450 oracle baru. |
| CP17 | 61/61 PASS: 41 Native, 4 race, 6 real Auth HTTP, 10 real browser | ID/count cocok, boundary/CP6 pulih dan advisor gate lulus. Kasus writer dijalankan sendiri, bukan dianggap oracle mandiri. |
| Oracle literal Sol | 6 PASS; 1 kasus koreksi berakhir FAIL setelah kualifikasi alat | INCOMPLETE awal karena token/timezone tetap tersimpan. Expected uang tidak berubah. |
| Tambahan real Auth HTTP Sol | 2 PASS, 2 COUNTEREXAMPLE → FAIL | Kontrol unspent lulus; amount/note-only setelah dana dipakai gagal; final negatif sungguhan ditolak. |
| BE | 16/16 PASS, artifact tepat 16 ID | CP6 BE T1; bukan bukti semua rantai konversi→jual→HPP final CP7. |
| Owner pemasang | 10/10 PASS; 58 berkas tepat | Owner dan akun kerja NOSUPERUSER, baseline v2.6.20 disposable yang dikualifikasi, sumber utama tak berubah. |
| Diagnostik | 3/3 PASS | Real PostgreSQL error, konteks, SHA, izin 0600 dan kegagalan penyimpanan eksplisit. Bukan reproduksi sebab AZ lama. |
| 48-menu inventory | 288/288 kunjungan selesai | 3 mode × 48 menu × desktop/phone; HTTP mock/refusal. Tidak diberi kredit keberhasilan transaksi Native. |
| Comparator / drain | Comparator stabil + lima kontrol sensitivitas; enam kontrol drain lulus | Bukti stdout asli dipertahankan. Akar dua A2 dan AZ historis tetap OPEN. |

**9 run / 18 job: 14 sukses, 4 gagal.** Dua kegagalan sebelum kasus adalah alat baseline dan CWD diagnostik; satu run pertama menyimpan 61 CP17 PASS tetapi oracle Sol INCOMPLETE; satu run kualifikasi menunjukkan bug bisnis nyata. Warna job tidak mengganti status kasus. `CASE_LEDGER.json` memisahkan konteks eksekusi, attempt alat dan hasil kanonik; tidak dipakai sebagai angka fitur selesai.

Klaim writer “80 uji” sebenarnya 80 run workflow/131 job: receipt berisi 79 workflow success, satu dibatalkan; 127 job success, empat job dibatalkan. Metadata 80 identitas diverifikasi, termasuk satu run CP6 T3 pada cabang writer lain dengan SHA kandidat sama. Itu **bukti metadata writer**, bukan 80 uji Native independen. CodeQL cancelled tidak direlabel PASS. Offsite attempt pertama tercatat gagal sebelum kasus; attempt kedua lulus menurut receipt, sedangkan dugaan penyebab bentrok port belum dibuktikan independen.

## Temuan dan reproduksi

Rincian lengkap lokasi, expected/observed, run/artifact, perbaikan dan uji wajib berada di `FINDINGS.json` dan `WRITER_HANDOFF.md`.

1. **SOL-R1-001 / S1 / NATIVE_QUALIFIED.** Income 30,01, pembayaran supplier 20, saldo 10,01. Koreksi income menjadi 25,01 mestinya selesai dengan saldo 5,01. Trigger `guard_cash_line` menolak pembalik sementara −20 sebelum pengganti dibuat; HTTP 400 `CP7_CASH_NEGATIVE`. Koreksi catatan saja juga gagal. Kontrol unspent berhasil dan kasus final −4,99 memang ditolak. Penolakan atomik; tidak ada bukti kerusakan fakta.
2. **SOL-R1-002 / S1 / STATIC.** Buat Potongan dan rencana Native memilih PO aktif yang sudah ada. Native cutting menolak tanpa PO aktif. Satu-satunya INSERT PO yang ditemukan adalah OPEN_PO melalui impor legacy/saldo awal; penjadwalan tidak membuat PO. Fixture membuat PO lewat SQL. Ini celah jalur PO harian, **bukan runtime FAIL** pada command potong dengan PO sah.
3. **SOL-R1-003 / S3 / alat bukti.** `pre_u.finished` dipanggil juga ketika chain sengaja berhenti sebelum U; helper menolak `PRE_U_INVENTORY_NOT_CAPTURED`. Adapter auditor hanya mengualifikasi stop tersebut; exact 58 SQL dan seluruh guard tetap sama dan lulus.
4. **SOL-R1-004 / S2 / browser.** Demo QC berukuran 669 px pada viewport 390 px; overflow halaman terukur.
5. **SOL-R1-005 / S2 / browser.** Demo HPP berukuran 627 px pada viewport 390 px. Kedua temuan tata letak dibatasi pada demo yang berisi data; halaman connected yang ditolak 403 bukan pembanding layout positif.

Tiga akar yang sudah diketahui writer tetap dibawa, **tidak dihitung penemuan baru**: `KNOWN-UI-MODE` (S0; 23 UAT contoh, angka uang tanpa label), `KNOWN-DAILY-MASTER` (S1; enam kelompok master harian), `KNOWN-BF-WAVE` (S1; tarif wave SKU/ukuran diblokir G1). D14-14 menyelesaikan G1/G2 dasar dan G3, tidak otomatis menutup tiga akar tersebut.

## Matriks kebutuhan dan sambungan

- `CHAIN_MATRIX.md/.json/.csv`: seluruh B1–B13 dan S1–S7 mempunyai disposisi, jalur public→Native, saksi dan batas. Status **tersambung** tidak sama dengan PASS; B11/B13 teruji dan FAIL. Jalur tanpa positive browser tidak dinaikkan karena inventory berhasil dibuka.
- `MENU_MATRIX.md/.json/.csv`: seluruh 48 menu, dua mode, perbandingan demo, isian/tombol, RPC, angka/label, viewport dan saksi browser positif. DISPOSABLE 35 tersambung/12 contoh/1 notice; UAT 23 tersambung/23 contoh/1 batas/1 notice.
- `INVARIANT_MATRIX.json/.csv`: 82 invarian; 69 PASS dalam batas bukti masing-masing, 4 FAIL, 9 INCOMPLETE. PASS historis diberi kandidat/seal asal dan tidak dihitung fresh runtime pada kandidat baru.
- `SCENARIO_MATRIX.json`: SKN-01..29; penundaan owner, pengujian historis, kegagalan koreksi dan cakupan tersisa dipertahankan.

## Yang belum diperiksa atau belum terbukti

Daftar lengkap berada di `OPEN_BOUNDARIES.json` serta kolom batas per chain/menu. Belum ada satu browser yang melakukan seluruh 13 tahap dan tujuh rantai samping berikut koreksi. Kekurangan khusus: POST potong/pickup/QC dari awal; konversi→jual→HPP pada final CP7; Nota Ambil→potongan payroll→kas; BS/rework/klaim/cuci ulang→QC parsial→Nota/bayar; impor WIP→produksi→jual→kas; hitung fisik/tutup periode di tengah rantai; real browser UAT dengan backend disposable sah; semua perangkat fisik; seluruh detektor 0→+1→0; semua batas nominal/page dan varian matcher→allocator→command.

Original CP2 restore, data cutover asli, install/SQL hosted, root AZ pertama, dua root A2 lama dan current hosted preflight tidak diganti dengan bukti sintetis. Keluarga P19/K2–K6/model/AI/WA memakai bukti independen Sol lama dan sumber yang tidak berubah, tidak dijalankan ulang diam-diam atau diklaim live. Runtime pengaruh akar SOL-R1-001 pada koreksi income lain/misc/note/cross-account baru trace risiko, belum dinyatakan jebol.

## Hasil merah yang bukan bug produk

`AUDITOR_TOOL_EVENTS.json` menyimpan semua disposisi. Token generic Asia/Jakarta vs writer UTC menyebabkan INCOMPLETE pertama; dedicated public correction workspace memperbaiki alat tanpa mengubah angka/oracle. Stop sebelum U menyebabkan penolakan baseline sebelum kasus; CWD salah menyebabkan import gagal sebelum kontrol diagnostik. Keduanya tetap direkam, lalu dikualifikasi sesuai §16.3. Native CE koreksi setelah kualifikasi tetap FAIL.

Metadata HTTP `original_posted_facts_immutable=false` setelah fixture spent **tidak dipakai sebagai bukti perubahan fakta**: JSON timestamp sebelum/akhir menggunakan zona berbeda. Snapshot seluruh batas bisnis/privat yang konsisten UTC membuktikan unchanged pada ketiga penolakan. Field false asli tidak dihapus. Label asal raw inventory terlalu luas (`INDEPENDENT_NATIVE_RERUN`), tetapi environment/auth/scope dan ledger final menandai seluruhnya **BROWSER_HTTP_MOCK tanpa kredit Native transaksi**. Metadata viewport inventory tertimpa angka `innerWidth`; nama desktop/phone tetap dari ID kasus. Unduhan browser lokal terpotong bukan bug ERP; browser CI berhasil.

## Label asal-bukti per klaim

| Klaim | Asal / tingkat | Bukti |
|---|---|---|
| Bug koreksi amount/note-only | Oracle literal Sol, fixture builder reused, eksekusi independen / NATIVE_QUALIFIED + real Auth HTTP | 38787925433, artifact 11998368969 |
| Empty bank/backdate/prefix/reversal/upah komponen | Oracle literal Sol / NATIVE_QUALIFIED | 38785656146, SOL_INDEPENDENT.json |
| CP17/F03/BE/owner retained oracle | Eksekusi Sol; rancangan provider/old Sol reused | RUN_REGISTER + CASE_LEDGER + original member |
| 48-menu mode/data/overflow | Source review Sol + real Chromium dengan mock HTTP | 38786177957, 3 original inventory JSON |
| Jalur PO harian / wave BF | Source trace / STATIC | SOURCE_REVIEW + kandidat pinned; tidak diberi Native FAIL palsu |
| 58-file install | Eksekusi Sol + oracle owner lama unchanged, tool qualification eksplisit / NATIVE_QUALIFIED | 38787131786, OWNER_CONTROLLER_QUALIFICATION.json |
| Diagnostik error PostgreSQL | Oracle literal Sol / Native engine only | 38790510239, SOL_DIAGNOSTIC_RETEST.json |
| Klaim 80 workflow writer | REUSED_WRITER_EVIDENCE, metadata saja | writer receipt + 80 SHA/run identities |
| CP2 / F01/F02 / P19 dan regresi lama | SOL_LOCKED_PRIOR_ROUND, kandidat lama disebut | seal 10bfe397; bukan hasil fresh kandidat ini |

## Pertanyaan owner dan keputusan yang berlaku

**Tidak ada pertanyaan baru yang perlu menghentikan pekerjaan.** D14-2..17 dipakai sebagaimana disahkan: tidak boleh kas/bank minus, lusin per seri, pembanding stabil, EXECUTE ditunda CP7C dengan exposure gate, retur kain atomic sesuai waktu simpan, upah rework bagian selesai boleh dibayar sekali, serta pengganti pre-U yang dibekukan. Pekerjaan backup/Drive/hosted dan nilai kebijakan yang masih pending tetap mengikuti register; tidak diminta ulang dan tidak ditebak. FABLE-011/cutover-floor adalah item register lama, bukan temuan baru Sol.

## Ringkasan owner — bahasa sehari-hari

Pemeriksaan putaran ini selesai, tetapi aplikasi belum boleh dinyatakan lolos penuh. Perbaikan bank kosong, paket bukti BE, penyimpanan pesan error, lusin per ukuran, jahit dasar dan HPP final dasar sudah terbukti. Ada bug baru: uang masuk yang sudah dipakai tidak bisa dikoreksi walau saldo akhirnya masih cukup, bahkan jika hanya mengganti catatan. PO produksi harian baru juga belum punya jalur biasa dari aplikasi. Mode Enteng masih menampilkan 23 menu contoh, termasuk angka keuangan yang terlihat seperti angka buku. Master harian dan jahit bertarif wave SKU/ukuran masih perlu disambungkan. Handoff mengurutkan perbaikan dan bukti yang dibutuhkan; tidak perlu mengulangi semua bagian yang sudah lulus. Tidak ada database asli atau aplikasi utama yang diubah.

## Fokus tambahan paling berisiko

Uji seluruh command compound yang membalik pemasukan lalu membuat pengganti terhadap guard kas baru, terutama misc income dan koreksi nota. Selesaikan ketersediaan jalur harian, kemudian buktikan alur benar-benar dapat dikerjakan operator tanpa SQL fixture. Setelah writer memperbaiki kandidat, lakukan retest terarah dengan kasus gagal yang sama, kontrol saldo negatif, race, tanggal, lineage dan satu rantai UI utuh yang sebelumnya putus; bukan sekadar menjadikan job hijau.
