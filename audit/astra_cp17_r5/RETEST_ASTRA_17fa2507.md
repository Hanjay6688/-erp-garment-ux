# AUDIT ASTRA — r5 — 19 Oktober 2026 WIB

**DRAFT — menunggu penyelesaian seluruh run terdaftar. Belum dikunci.**

Kandidat `17fa25075ba77f0853c3c16f504288ace03eec35`, tree `65f778479093d869a3354c0b9f19b4d9a541d98a`.
Cabang auditor `audit/astra-cp1-7-r5-17fa2507-20261019`.
Basis r4 `663f6faefcbb9c70f0f99bbc7e78164e03521329`; laporan Astra sebelumnya terkunci di `40238e36`.
Handoff yang diterima: `docs/cp7/audit-candidate/cp1-7-r5-20261019/HANDOFF_ASTRA.md` pada writer `2766a9092f51f240267b9cbe1201d49a836fb490`.
Aturan Pro Max SHA256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`, dihitung ulang; register keputusan sampai D17-2. Instruksi pemilik untuk melanjutkan audit diterima langsung dalam sesi ini; kutipan keputusan lama yang hanya dibaca dari repo tetap memiliki asal bukti dokumen.

## Ringkasan dan batas vonis

@@VERDICT@@

Audit ini memeriksa perubahan r5 dan dampaknya pada paket CP17 serta laporan P19. Ini bukan pengulangan penuh semua workflow CP1–7 atau pengesahan seluruh ERP. `feature_complete=false`, `audit_complete=false` untuk keseluruhan ERP, `production_go=false`, `owner_latency_acceptance=false`. Status selesai untuk penugasan retest r5 dicatat terpisah.

## Hasil runtime dan rekonsiliasi

@@CI_TABLE@@

Inventaris yang dibekukan mencakup **396 slot cakupan**: CP17 345, skala5, transport15, laporan20, kasus sendiri11. Satu ID browser yang dijalankan di build biasa dan build Enteng dihitung sebagai dua lapisan bukti, bukan dua oracle independen. Prosa rencana awal keliru memakai nama fase lama `p19-transport11 ` sebagai jumlah; manifest sebelum run sudah benar15. `PLAN_ERRATA.md` mempertahankan koreksi ini. Kualifikasi alat dua kasus adalah riwayat eksekusi tambahan, bukan dua cakupan produk baru.

`RECONCILIATION.json` mencocokkan himpunan `(suite, layer, ID)` dan multiplicity; `CASE_LEDGER.jsonl.gz` menyimpan observed dan status asli. Hasil kanonik dan hubungan kualifikasi ada di `CANONICAL_RESULTS.json`. Tidak ada status merah pertama yang ditulis ulang menjadi PASS.

## R5-01 / SOL-R4-001 — alarm salah pada Nota FG_REPAIR

**Bukti mandiri:** `ASTRA_R5_FG_HEALTHY_8000`, `ASTRA_R5_FG_DETECTOR_0_1_0`, `ASTRA_R5_FG_REVERSED_REUSE`; `INDEPENDENT_NATIVE_RERUN`, oracle angka dan perbandingan dirancang Astra.

Dua perbaikan barang jadi1 dan3PCS, tarif2000, menghasilkan dua baris hak upah berjumlah 8000 dan utang 8000, belum dibayar. POST ulang dengan UUID sama tidak menambah efek. Seluruh167 detektor bernilai 0 sebelum dan sesudah buku sehat. Salinan checker sebelum perubahan mengeluarkan tepat 2 alarm palsu. Perubahan hanya menambah resolusi mandor FG_REPAIR melalui primary ID/source_type; sumber PRODUCTION/REWORK tetap tersaring masing-masing.

UPDATE mandor pada fakta upah ditolak `P0001 / FG_UNSOURCED_REPAIR_WAGE_IMMUTABLE`. Dalam diagnostik savepoint dengan hanya trigger yang dituju dinonaktifkan, salah mandor dan sumber upah hilang masing-masing menaikkan `run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor` dari 0 ke 1; rollback mengembalikan 0 dan semua keluaran detektor dipertahankan. Pembatalan Nota menjadi REVERSED tetap dikecualikan; alokasi sah berikutnya hanya satu upah/utang aktif 8000, tanpa pengulangan stok, HPP, jurnal atau kas dari Nota.

Rantai: penerimaan AX → fakta upah FG → sumber Nota → payroll work line → checker → readiness/laporan. Review source: `scripts/cp7_payroll_checks_bundle.py`, `scripts/cp7_note_report_bundle.py`, `scripts/cp7_f03_bundle.py`; rincian dan inverse text check di `STATIC_REVIEW.md`/`STATIC_REWRITE_CHECKS.json`. Perusakan privat ini membuktikan sensitivitas detektor, bukan kemampuan pengguna aplikasi merusak tabel.

## R5-02 — jawaban laporan sesudah optimasi lookup akun

**Bukti:** `INDEPENDENT_SOURCE_REVIEW` untuk11 reader/69 literal lookup/17 core key dan komposisi; `INDEPENDENT_NATIVE_RERUN` untuk jawaban, mapping, keuangan dan pemulihan.

Semua11 reader dibandingkan dengan teks sebelum wrapping pada input terisi, kosong, NULL, dan periode kosong. Input terisi mencakup4 opening-credit,1 pocket-period,4 sale/return–PO,2 non-PO HPP,9 PO HPP,3 jendela laporan dan masing-masing checker. Fixture pembuka berasal dari builder writer yang dibekukan; pembandingan dan expected dikendalikan Astra. Semua pasangan yang diuji sama. Panggilan kosong bukan pengganti bukti input terisi.

WIP dipetakan ke akun alternatif sah bertipe sama: tujuh pengulangan semua reader tetap sama dengan teks lama, setidaknya satu jawaban benar-benar berubah, dan pengembalian mapping mengembalikan seluruh jawaban. Semua17 core key menolak delete dan rename dengan alasan mapping yang dituju:34 penolakan dan baris mapping tetap.

Oracle keuangan terpisah memakai fasad publik sebagai authenticated OWNER: pendapatan100.01/221.11, HPP66.67/97.03, laba33.34/124.08; pertumbuhan121.0879% dan perubahan margin22.7802poin cocok dengan Decimal independen. Pembacaan ulang tidak menambah fakta bisnis.

Kualifikasi Q2 membuktikan12 definisi/owner/ACL/volatility/config kembali persis setelah unpatch/reapply; core mapping hilang ditolak `CP7_R5_02_ACCOUNT_MAPPING_MISSING` dan literal tambahan ditolak `CP7_R5_02_READER_SOURCE_CHANGED`, tanpa perubahan parsial. Pada race, PID 229 teramati menunggu `PgSleep` pukul 10:52:28.092277Z; perubahan COGS commit pukul 10:52:28.186166Z. Delapan baris dalam statement yang sedang berjalan tetap sama (HPP 97.03); statement berikutnya melihat mapping baru (HPP 0). Confidence sebelum perubahan sudah BLOCKED dengan8blocker fixture; sesudahnya tetap BLOCKED dengan10blocker, termasuk dua tambahan `V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH` dan `V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH`. Ini bukan bukti transisi READY→BLOCKED. Kasus ini memakai mapping alternatif sah dalam database disposable, bukan command pengguna mengubah fakta privat.

Batas pembandingan: salinan setiap reader memanggil dependensi terpasang yang sama, sehingga ini bukan pengulangan seluruh graph r4 secara utuh. Oracle angka publik melengkapi perbandingan teks tersebut. Kasus unknown app actor berjalan sebagai pemilik database untuk diagnostik helper internal; tidak menemukan perbedaan pada input itu, tetapi tidak membuktikan penolakan seluruh aktor di HTTP. Bukti akses publik berasal dari kasus facade/HTTP/transport terpisah. Nilai checker dalam fixture diagnostik tidak digunakan untuk mengklaim seluruh buku produksi bersih.

Python `wrap()` dan SQL installer mempunyai pemeriksaan berbeda: wrapper Python memeriksa volatility/key/count/already-wrapped; SQL block memeriksa count/already-wrapped dan precondition mapping, sedangkan pemasang F03 penuh memeriksa exact expected definitions sebelum commit. Tidak mengklaim SQL block tunggal menutup semua drift.

## Temuan yang tetap terbuka — KNOWN-P19-DIRECT-LATENCY

**Keparahan S2; temuan lama, bukan penemuan baru Astra.** Kebutuhan D17-2 dan budget P19: jalur berat selesai dalam3 detik; pengecualian background/staged tidak mengubah arti target itu. Rantai: pembaca Native/HPP → capture analisis dengan angka keuangan → pengiriman/segmen → hasil dirender.

@@LATENCY@@

Suite skala boleh PASS saat batas resmi ditolak secara jujur. PASS tersebut tidak berarti semua volume selesai atau memenuhi3 detik. Batas8 detik adalah per statement, bukan batas seluruh perjalanan. Tidak ada limit dinaikkan, sumber dipotong, sampling, atau guard delivery dihapus dalam audit ini. Rekomendasi tetap tugas writer D17-2: lanjutkan optimasi dengan sumber/izin/snapshot yang setara, lalu ukur ulang angka keuangan penuh; keputusan ini sudah ada dan tidak ditanyakan ulang.

## Hasil merah yang bukan temuan produk

Run pertama `39238457513`, job `118013182781`, tetap **FAIL /9PASS+2INCOMPLETE**. Pemulihan CP6 tetap terbukti dan database race dihapus.

| Kasus | Status asli | Disposisi dan bukti |
|---|---|---|
| ASTRA_R5_INSTALL_ROUNDTRIP_REFUSALS | INCOMPLETE | AUDITOR_TOOL: probe mengirim blok SQL tanpa parameter sebagai `execute(sql, ())`; karakter `%` dibaca parser placeholder psycopg sebelum PostgreSQL menerima blok. Q2 mengirim `None` dan `prepare=False`, tanpa mengganti SQL/expected. |
| ASTRA_R5_MAPPING_COMMIT_SNAPSHOT | INCOMPLETE | AUDITOR_TOOL: Native JSONB97.03 terdecode sebagai float; `Decimal(float)` menghasilkan97.030000000000001136868377216160297393798828125, sehingga perbandingan exact gagal. Q2 hanya memakai `Decimal(str(value))`; observed tetap97.03→0.0, delapan baris coherent dan confidence BLOCKED. Tidak mengubah expected. |

`Q2_TOOL_DIFF.patch` dan `Q2_PREDECLARED.json` dibekukan sebelum kualifikasi `39239850748`. ID, expected bisnis, fixture, timeout dan peran tetap; sembilan kasus pertama yang sudah PASS tidak diulang. Ini kualifikasi alat baru menurut Pro Max§16.3, bukan rerun identik untuk mencari hijau. Kesalahan filter path Q2 diperbaiki sebelum ada run; tercatat di `PLAN_ERRATA.md`. Tidak ada rerun job.

## Matriks invarian — cakupan r5

@@INVARIANTS@@

Status di atas berlaku pada skenario dan lapisan yang disebut. Kolom INCOMPLETE untuk seluruh keluarga berarti tidak diverifikasi ulang menyeluruh pada sesi r5; status checkpoint terdahulu tetap mengikuti keputusan owner. `INVARIANT_MATRIX.json` memisahkan bukti r5 terpilih dari kelengkapan seluruh ERP. Tidak semua167 detektor mendapat kontrol negatif baru; kontrol0/+1/0 baru secara khusus menutup checker FG_REPAIR. Detector coverage universal tetap INCOMPLETE.

## CP1/CP2 dan bukti yang dipertahankan

`CP1_CP2_RECHECK.json` mencocokkan tujuh sumber/bukti lama terhadap r4: hash sama. Ini review invariansi, bukan restore baru. CP2 pernah mempunyai restore PG16/stub; engine/image asli, owner/ACL penuh dan round-trip Storage tidak diverifikasi baru oleh Astra. Jangan menulis “tidak ada bukti” atau “sudah restore penuh”.

Peta legacy yang dibaca adalah versi terkunci sebelum pembekuan:37 entri,12 `BOUNDARY_NO_SUCCESSOR`,11 `SUCCESSOR_MAPPED`,14 `PASSES_ON_CANDIDATE`; detail ada di `retained/LEGACY_COVERAGE_BOUNDARIES.json`. Label itu adalah disposisi historis, bukan hasil runtime r5. Tidak mengulang seluruh565 kasus Astra r4 dan tidak menambahkannya ke hitungan396.

A2 dua kegagalan supplier historis tetap belum diketahui akarnya, nonblocking bagi pembekuan sesuai keputusan terdahulu. FABLE-012/82hak EXECUTE privat tetap penundaan bersyarat menuju CP7C; tidak dinyatakan selesai. ASTRA-R3-01/R2-01/R3-02/R3-03 tetap merujuk penutupan r4, bukan penutupan baru yang diklaim dari pembacaan dokumen.

## Yang belum saya periksa

1. Seluruh workflow CP6/CP7, Build UX dan CodeQL pada r5 tidak semuanya dijalankan ulang oleh sesi ini. Receipt115 workflow/116 run writer tetap `REUSED_WRITER_EVIDENCE` dan tidak dijumlah sebagai tes mandiri.
2. Seluruh graph r4, semua kombinasi izin/key/missing mapping yang hanya dapat dibuat melalui korupsi privat, semua variasi input/volume dan semua detektor belum diuji ulang menyeluruh. Root perubahan dan skenario terdaftar dibatasi jelas di atas.
3. Dua belas jalur legacy tanpa successor penuh, keterbatasan CP2 dan A2 historis tidak ditutup oleh audit delta ini.
4. Preflight hosted aktual berumur<7hari dan pemasangan penuh menggunakan non-superuser dari baseline nyata belum dibuktikan di sini. Tidak ada SQL hosted dilakukan. Baseline CI direkonstruksi/di-align melalui sumber yang dipin; itu bukan pengukuran langsung kondisi hosted hari ini.
5. Shadow run data cutover nyata satu periode tutup buku, rekonsiliasi dokumen bisnis asli, monitoring/cutover dan persetujuan owner produksi tetap belum terpenuhi lengkap. Data uji di sini sintetis.
6. iPad nyata, semua unduhan/rekomendasi/reminder dan koneksi WA live tidak seluruhnya diuji. Tidak mengirim pesan nyata. Kasus browser desktop/mobile dan build Enteng loopback tidak berarti CP7 sudah dipasang di Enteng.
7. Seluruh hasil peserta r5 lain belum dibaca. Daftar “belum diperiksa siapa pun” harus digabungkan oleh penyatu sesudah seluruh laporan terkunci; Astra tidak dapat menyatakan daftar gabungan kosong.

## Pemasangan, pemulihan, lingkungan dan perintah

@@RESTORE@@

Runtime disposable Ubuntu24.04, Supabase image PostgreSQL17.6.1.165, CLI2.116.0, Python3.12.15, psycopg3.2.10, Node22.23.3; browser Chrome for Testing151.0.7922.34 (Playwright Chromium1234). Lockfile kandidat dipakai. Harness `c6b0e4fb119c4e91fecea66ebf2d789426b22c2b`; writer scaffold `ca7f09556397801c50a2277bdb65b1bf019f9a05`; predecessor `25fa4736329e5148dfdb3572bc169952cba23251`; base `1bdca3766f7c9800d68295ff5122798060b8a05d`. Workflow source dan SHA setiap run ada di `RUN_REGISTER.json`. `IDENTITY.json` mencatat tree produk dan perubahan scripts, bukan hanya src/supabase.

Perintah runtime persis disimpan dalam `.github/workflows/audit-astra-r5-{cp17,p19,own,own-q2}.yml`: pemasangan Supabase disposable, `cp6_t3_aligned_chain.py --stop-after-ab`, clone disposable, pemasangan T3/F03, probe CP17/P19 dan `own_runner*.py`, pemeriksaan diff produk, lalu `supabase stop --no-backup`. Review lokal: Git diff/object hash, ekstraksi definisi, Python compile/import, pemeriksaan transform dan `reconcile_evidence.py`; review lokal tidak dihitung kasus Native.

## Label asal bukti dan isolasi laporan

| Klaim | Asal | Referensi |
|---|---|---|
| Identitas Git, delta checker/readers dan komposisi | INDEPENDENT_SOURCE_REVIEW | IDENTITY.json, STATIC_REVIEW.md, STATIC_REWRITE_CHECKS.json |
| Eksekusi CP17/P19 dan hasil per kasus | INDEPENDENT_NATIVE_RERUN | Run/register/ledger; rancangan oracle berasal dari writer atau auditor terdahulu |
| Oracle8000, sensitivitas, mapping, angka Decimal, Q2 | INDEPENDENT_NATIVE_RERUN | OWN_PREDECLARED.json, source probe dan raw logs; fixture builder reused secara eksplisit |
| Hasil writer115 workflow/116 run dan diagnosis lama | REUSED_WRITER_EVIDENCE | Handoff/receipt frozen; tidak dipakai sendirian menutup runtime |
| Batas CP1/CP2, legacy, status penutupan r4 | REUSED_AUDITOR_LOG_READ + INDEPENDENT_SOURCE_REVIEW atas invariansi | Artefak r4 terkunci, retained/, CP1_CP2_RECHECK.json |
| Keputusan bisnis lama yang diteruskan dokumen | UNVERIFIED_OWNER_DECISION sebagai asal kutipan | Register sampaiD17-2; tidak ditanyakan ulang atau diubah |

Tidak ada laporan, log, artifact, PR atau komentar peserta lain dari putaran r5 dibuka sebelum laporan ini dikunci. Daftar metadata Actions hanya dipakai untuk menemukan run sendiri; ini disiplin sesi, bukan klaim isolasi akses teknis di repo bersama. Tidak ada subagent, perubahan produk, commit pada writer/main, merge, PR, deployment atau pesan kepada pihak lain.

## Pertanyaan untuk owner

Tidak ada pertanyaan bisnis baru. Keputusan terdahulu tetap berlaku. Vonis retest ini tidak meminta ataupun memberi izin pemasangan produksi.

## Ringkasan untuk owner

@@OWNER_SUMMARY@@

## Fokus lanjutan paling berisiko

Kecepatan analisis dengan angka keuangan harus diselesaikan tanpa mengurangi kebenaran/scope sumber, pengamanan izin atau pemeriksaan ulang saat hasil dikirim. Untuk produksi, bukti baseline aktual, non-superuser install, shadow run, pemulihan dan daftar batas gabungan tetap menentukan; jumlah PASS audit delta tidak menggantikannya.
