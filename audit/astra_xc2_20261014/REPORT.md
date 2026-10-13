# Astra — audit silang CP7 putaran 1 dan 2

**Putaran 2 LULUS dalam cakupan di bawah. R2-F05 DITUTUP; R2-A6 LENGKAP. A2 tetap OPEN dan bukan penghalang pembekuan menurut D13-10. `production_go:false`.**

Audit putaran 1 Astra diselesaikan pada kandidat putaran 2, pilihan yang secara eksplisit diberikan `HANDOFF_ASTRA.md` putaran 2. Ini melanjutkan audit penuh Astra `d0b9e9c2` (laporan terkunci `e800e016`) dan retest `7a0b4a90` (laporan terkunci `41dbd14d`). Hash produk tidak berubah; hasil lama yang dibawa maju dibedakan dari eksekusi baru. Tidak ada temuan produk baru dalam cakupan pemeriksaan ini.

## Identitas dan asal bukti

| Acuan | Nilai |
|---|---|
| Kandidat yang diuji | `0b7049d9203bac52b47a4c89f3e0d75646067a8f` |
| Tree kandidat | `ce6aed0a0af920e8aa80248f3cabcd293688df18` |
| Cabang audit baru | `audit/astra-cp7-xc2-0b7049d9-20261014` |
| Workflow regresi | `858f5b2321a70b73f0b1dc0da2791035906a29aa` |
| Workflow kontrol Astra | `90f6d7f3c0451ea41e77d2cd4a02d3b58f4e0bd7` |
| Waktu run | 13 Oktober 2026 17:02–17:15 UTC; 14 Oktober 00:02–00:15 WIB |
| Head writer terakhir diperiksa | `c2cdc290b3c93fdf4c243109d2cd89191ee7bd79`, paket dokumen putaran 2 dengan CI receipt writer masih pending |
| Lingkungan | GitHub Actions Ubuntu 24.04; Supabase CLI 2.116.0; image PostgreSQL 17.6.1.165; Python 3.12; psycopg 3.2.10; Node 22.23.3; Playwright 1.62.1, Chromium 151.0.7922.34 |
| Browser | Chromium sungguhan, desktop 1440×1000 dan emulasi HP 390×844, Auth/PostgREST pada loopback |

`SOURCE_RECEIPT.json` memuat hash direktori `src`, `supabase/release`, `supabase/migrations`, `supabase/dev`, dan `scripts/cp7-src`. Diff `7a0b4a90 → ae0214ad → 0b7049d9` untuk kode produk kosong. Checkout kandidat dan tree diperiksa sebelum eksekusi; `git diff --exit-code HEAD --` diperiksa lagi sesudahnya. Kandidat berbeda dari SHA workflow auditor, dan keduanya dicatat dalam setiap Original.

Audit dimulai atas perintah langsung owner meskipun paket writer masih bertanda draft. Penutupan memakai run Astra sendiri. Tidak ada SQL hosted, pemasangan produksi, atau tindakan Drive. Paket offsite/restore CP7C tetap ditahan menurut D13-9a. Baseline instalasi CI yang terarsip bukan bukti keadaan hosted terbaru.

Paparan: handoff writer, laporan Astra terdahulu, dan ringkasan Fable XC1 yang diberikan owner dipakai sebagai konteks. Tidak membaca laporan atau run Fable putaran 2. Metadata run writer kandidat dilihat untuk navigasi; hasil writer tidak menjadi bukti penutup. Bukti payroll writer putaran 1 dibaca dan diberi label terpisah di A4.

## Hasil eksekusi baru

Semua enam job selesai pada attempt pertama. **141 eksekusi kasus CI PASS, mencakup 139 ID unik**: 130 eksekusi regresi dengan oracle writer tidak diubah dan 11 kontrol Astra. Dua ID browser P11 muncul pada dua komposisi, sehingga tidak dihitung sebagai empat ID unik. Uji DOM tersendiri: satu kasus PASS yang memuat empat pemeriksaan simulasi lama. Kontrol diagnosis lokal dipisahkan dari hitungan CI.

| Run / job | Suite | Hasil dan asal oracle |
|---|---|---|
| [38435365859 / 115427812633](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38435365859/job/115427812633) | F03 P11 | 64/64 PASS; `INDEPENDENT_NATIVE_RERUN`, `WRITER_UNCHANGED` |
| [38435365859 / 115427813178](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38435365859/job/115427813178) | F03 prefreeze UI | 31/31 PASS; `INDEPENDENT_NATIVE_RERUN`, `WRITER_UNCHANGED` |
| [38435365859 / 115427813121](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38435365859/job/115427813121) | K3 cleanup | 25/25 PASS; `INDEPENDENT_NATIVE_RERUN`, `WRITER_UNCHANGED` |
| [38435365859 / 115427813220](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38435365859/job/115427813220) | Supplier Payment Create | 10/10 PASS; `INDEPENDENT_NATIVE_RERUN`, `WRITER_UNCHANGED` |
| [38435746105 / 115429126194](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38435746105/job/115429126194) | Astra backup | 11/11 PASS; `INDEPENDENT_NATIVE_CASE`, `ASTRA_CONTRACT`; lima oracle lama, lima skenario database tambahan, satu kontrol grammar tanda |
| [38435365859 / 115427812937](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38435365859/job/115427812937) | SalesPages dozen DOM | 1/1 PASS; eksekusi independen oracle writer, jsdom |

Pemulihan CP6/boundary, gate advisor yang berlaku, pembersihan Auth/database, dan seluruh gate paket T3 lulus. Tidak ada pengulangan karena pergantian hari. `CASE_RESULTS.json` memuat setiap ID/status dan pemeriksaan pemulihan; `CI_RECEIPT.json` mengikat run, job, SHA workflow, attempt, dan artifact.

Dua hasil `INCOMPLETE` pada diagnosis layar CP6 sebelum CP7 dipasang tetap disimpan utuh di Original prefreeze. Keduanya sejak awal berlabel `LEGACY_RUNTIME_OBSERVATION_ONLY`, mendapat nol kredit produk, dan bukan dua kasus P11 pengganti. Cleanup diagnosis itu juga lulus. Tidak ada hasil tersebut diganti namanya menjadi PASS.

## Disposisi putaran 1 dan 2

| Butir | Disposisi Astra | Bukti dan batas |
|---|---|---|
| A1 / ASR-OPS-01 | **DITUTUP** pada `0b7049d9` | `ASD-B01..B05` semuanya PASS di job 115429126194. B05 mempertahankan database pengganti dan canary, menolak verifikasi, serta tidak memangkas. Sumber tetap utuh. Situasi A–D juga PASS pada K3 job 115427813121. |
| R2-F05 / F-OPS-05 | **DITUTUP** | `AX2-B06-PLAIN_CONFIG`, `AX2-B07-PLAIN_PATTERN`, `AX2-M01-MARK-GRAMMAR`, dan `K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT` PASS. Database asing dengan tanda polos tetap memiliki OID, komentar, dan baris yang sama. |
| A2 | **MASIH TERBUKA — bukan penghalang pembekuan** | D13-10 berlaku. Diagnosis tidak mengubah persamaan pembanding. Run supplier baru 10/10 PASS dan `complete_boundary_restored:true`; ini tidak menjelaskan dua kegagalan lama. Kedua log gagal asli tetap tersimpan dan dicatat hash-nya. |
| A3 | **DITUTUP** | `K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL`: pasang, pasang ulang tanpa duplikasi, verifikasi cocok K3, lepas. `cron.job` 0→0, 559 tabel tetap, tidak ada job yang sempat berjalan. Hanya cluster disposable. |
| A4 | **TIDAK BERLAKU sebagai temuan produk aktif** | F-PAY-01 sudah ditarik Fable. Catatan cakupan run lama Astra tetap dipertahankan. Log writer run 38380339961/job 115238908371 benar memuat dua cabang zona aktif pada 10:06:19 UTC. Ini `REUSED_WRITER_EVIDENCE`, bukan PASS runtime independen baru untuk kedua cabang. |
| A6 / R2-A6 | **LENGKAP** untuk pensiun dua kasus dari komposisi CP7 | Dua browser P11 di dua komposisi PASS, ditambah empat pemeriksaan simulasi dalam satu kasus DOM. Kriteria D13-9c/D13-12 terpenuhi pada kandidat ini. Kasus CP6 asli tetap ada di suite CP6 beku. |
| A8 | **DITUTUP dalam cakupan delta alat** | Seluruh 12 berkas perubahan putaran 1 dibaca, ditambah delta putaran 2. Regresi memakai runner yang sama: supplier, K3, dan F03 P11. Bukti lama Astra pada kode produk yang identik dibawa maju; hitungannya tidak ditambahkan ke 141 eksekusi baru. |
| R2-D11 | **DIKONFIRMASI: izin belum dipakai** | Tidak ada pembanding penerimaan baru. `cp6_auditor_runner.py` dan `cp6_auditor_difference.py` identik antara `ae0214ad` dan `0b7049d9`. |
| R2-REG | **DICATAT** | Register kanonik kandidat memuat D13-10..D13-13 sesuai arahan owner yang diteruskan dalam sesi ini. |

PR44 tetap memakai penerimaan Fable yang sudah disampaikan owner; Astra tidak mengeluarkan persetujuan baru atas optimasi yang pernah ditulis Astra sendiri. A7 tidak dibuka ulang. A9 mengikuti penahanan paket backup/Drive sampai CP7C.

## A1 dan F-OPS-05 — bukti penutup dan batas operasional

Kelima oracle lama tersedia di `baseline/cases_delta_41dbd14d.py`, byte-identik dengan blob lama `a82064999c7492e668bf4c8dbe9d7fff4562182a`. Perubahan satu baris fixture berada di `LEGACY_FIXTURE_ADAPTATION.diff`: sisa yang memang dimiliki alat diberi token dan OID aktual sesuai API baru. Semua expected clause lama dipertahankan; pembungkus baru menambahkan pemeriksaan eksplisit isi sumber.

- B01/B02: database asing sejak awal atau yang muncul sesudah dump tetap utuh; backup ditolak dan tidak ada pruning.
- B03: dump/hash tetap satu snapshot berisi satu baris walaupun sumber telah menerima baris kedua. Baris asli sumber tidak berubah.
- B04: sisa milik alat sah dapat dibersihkan, backup terverifikasi, tidak meninggalkan scratch.
- B05: urutan temuan asli Astra sekarang mempertahankan `FOREIGN_REPLACEMENT`; sumber tetap satu baris asli, verifikasi false, pruning kosong.
- B06/B07: tanda polos disalin ke nama scratch dan nama berpola attempt. Yang pertama ditolak; yang kedua diabaikan sebagai sisa, sementara backup dengan attempt sendiri berhasil. Kedua database asing tetap sama.
- B08: setelah hash nyata selesai, database attempt dipindah dan namanya diisi database asing. Penghapusan akhir mengikuti OID milik attempt yang sudah berpindah; pengganti tetap utuh.
- B09: tanda attempt diganti menjadi tanda polos sebelum `finally`. Database tidak dihapus, hasil `NOT_OURS`, malam dibatalkan, dan file lama tetap tersimpan.
- B10: kegagalan sengaja sebelum penulisan mark membersihkan hanya OID yang baru dibuat oleh attempt, dengan malam tidak terverifikasi dan file lama tetap tersimpan.

**Ketepatan klaim kepemilikan:** tanda polos tidak memberi izin penghapusan. Implementasi tetap mempunyai jalur `created_here` untuk OID yang diketahui baru dibuat oleh attempt dan belum sempat ditandai; B10 menguji jalur itu. Ini bukan penggunaan tanda polos untuk mengklaim database asing. Penutupan F-OPS-05 tidak dimaksudkan sebagai klaim bahwa setiap pemanggilan `drop_owned` selalu membutuhkan komentar database.

**Batas operasional A1 tetap eksplisit.** Admin dapat mengganti database acak tepat antara pemeriksaan OID dan koneksi `pg_restore`; restore dapat menulis ke pengganti. Situasi B K3 membuktikan pengganti tidak dihapus dan malam tidak diverifikasi. OID guard bukan kunci eksklusif yang mencegah seluruh tindakan superuser bersamaan. D13-6/D13-8b memilih restore di database sementara pada mesin GitHub; penutupan ini tidak memberi izin memakai restore pada cluster produksi bersama. Kualifikasi offsite/restore CP7C tetap terpisah dan ditahan.

## A6 — bukti P11 yang benar-benar dipakai

`P11_DRAFT_BROWSER_DESKTOP` dan `P11_DRAFT_BROWSER_MOBILE_RECOVERY` PASS pada F03 P11 dan prefreeze UI. Kedua kasus menjalankan Auth, layar P11, API simpan, serta baca ulang server sesungguhnya pada database disposable.

1. Qty manual 13 tidak berubah selama helper kosong atau diisi tanpa menekan tombol.
2. Kosong, `1,1`, `1.1`, sisa PCS 12, dan 0+0 membuat tombol tidak aktif; qty tetap 13.
3. Menekan “Terapkan lusin baris 1” dengan 2 lusin + 1 menghasilkan 25; baris kedua tetap qty 2, harga 10,01, potongan 0,02, dan catatan yang sama. Total Rp520.
4. Helper 1 lusin + 1 mengembalikan qty ke 13, total Rp280. Nilai inilah yang disimpan.
5. Server mengembalikan qty `[2,13]` dan stok tersedia `[17,28]`; form edit membaca kembali 13. Alur edit/post dan pemulihan balasan CREATE hilang pada HP juga tetap lulus.
6. Pemeriksaan geometri menunjukkan tidak ada overflow horizontal. Screenshot desktop/HP diperiksa: helper, qty 25, baris kedua, dan total Rp520 tampak sesuai hasil.

Kelengkapan ini mengikuti ruang lingkup D13-12: helper P11 per baris pada mode tersambung. Distribusi 4/4/4 pada layar simulasi berbeda dan tetap diuji di jsdom; tidak diklaim sebagai browser simulasi baru. Bukti HP adalah emulasi Chromium, bukan perangkat fisik atau Safari.

## A2 — diagnosis dan bukti lama

Diff runner dibaca lengkap. `full_boundary_restored`, `public_schema_unchanged`, dan `complete_boundary_restored` tetap memakai equality asli. `state_difference` hanya menjelaskan kegagalan; tidak menulis ulang snapshot. Definisi fungsi, owner, dan ACL tetap diperiksa melalui `function_pins`. Kontrol lokal atas urutan, kehilangan duplikat, dan perubahan nilai anggota lulus; rincian ini tidak diberi kredit native ERP. Ringkasan `removed/added` memakai set sehingga tidak menampilkan selisih jumlah duplikat, tetapi klasifikasi tetap `CONTENT` dan equality tetap gagal.

Original 26 snapshot Astra lama dibaca ulang dari arsip `41dbd14d`, SHA-256 `f364d8d1046988784fdd0a0b2738910139977576cee3dbeee3645f9889d52aba`. Sepuluh pasangan yang dicatat dalam review lama tetap sama persis. Ini tidak dapat menjelaskan isi dua run lain yang gagal sebelum diagnosis tersedia. `A2_FIRST_FAILURES_RETAINED.json` mencatat kedua log asli yang masih berada dalam kandidat: run 38288829388/job 114943655473 dan run 38330557862/job 115079091992. Masing-masing memiliki 10 kasus PASS tetapi suite INCOMPLETE; bukti itu tidak ditimpa oleh run baru.

**AX2-T01, AUDITOR_TOOL lokal — selesai.** Pembaca awal salah mengira indeks observasi pada review lama mulai dari satu. Ia gagal assertion sebelum menulis hasil. Setelah memeriksa jenis observasi, indeks nol dipakai dan jenis tiap pasangan ikut divalidasi. Original tidak berubah; tidak ada transaksi ERP atau kasus CI yang diulang. Kegagalan pembaca pertama disimpan di `LOCAL_READER_FIRST_FAILURE.txt`; koreksi dan hasil ada di `recheck_prior_snapshots.py` serta `PRIOR_SNAPSHOT_RECHECK.json`.

## Paket bukti dan batas kesimpulan

`ORIGINALS.tar.xz` menyimpan seluruh JSON Original lima job native, JSON DOM, dan enam log job lengkap. Enam screenshot P11 asli disimpan terpisah di `evidence/screenshots/` agar dapat dibuka langsung. `ORIGINALS_ARCHIVE.json` serta `EVIDENCE_MANIFEST.json` mencatat SHA-256 arsip, tiap berkas, dan artifact ZIP unduhan yang cocok dengan digest GitHub. Arsip snapshot lama 85 MB tidak diduplikasi; lokasinya dan hash yang diverifikasi dicatat.

`SOURCE_REVIEW.json`, `DIAGNOSIS_DELTA.diff`, dan `ROUND2_RUNTIME_DELTA.diff` mengikat pemeriksaan statis. Workflow dan probe audit tersimpan pada cabang ini. `WRITER_HANDOFF.md` adalah ringkasan untuk diteruskan owner. Tidak mengirim pesan ke writer atau auditor lain.

**Dua syarat pembekuan pada D13-13 terpenuhi dari sisi audit Astra untuk kandidat yang disebut.** A2 tetap keterbatasan terbuka yang diterima owner. Penyatuan dengan jawaban Fable dan pembekuan kanonik tetap dikerjakan writer/owner. Hasil ini tidak merupakan pemasangan, kualifikasi hosted terbaru, atau izin produksi.
