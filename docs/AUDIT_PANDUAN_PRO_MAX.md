# Panduan Audit Pro Max ERP Garment

> **VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.**

Dokumen ini dibaca oleh setiap auditor independen (Fable, Opus, Astra) sebelum mulai, dan oleh penyatu temuan sesudahnya. Satu tujuannya: **owner tidak boleh rugi atau bangkrut karena ERP memberi angka, laporan, atau rekomendasi produksi yang salah.**

Nol bug tidak bisa dijamin oleh siapa pun. Target yang bisa dicapai dan wajib dikejar:

1. **Nol bug yang diketahui** di bagian yang diaudit. Setiap temuan diperbaiki dengan bukti, atau dicatat terbuka dan diputuskan owner.
2. **Tidak ada jalur yang bisa diam-diam menghasilkan angka salah** untuk uang, stok, HPP, laporan, atau rekomendasi. Kalau datanya salah atau tidak lengkap, sistem harus menolak atau menandai "belum pasti", bukan menampilkan angka yang terlihat benar.
3. **Kesalahan yang lolos ketahuan cepat** lewat cek integritas dan rekonsiliasi, dan bisa dibetulkan tanpa merusak riwayat.

Status tetap: `production_go=false`, CP6 HOLD, `audit_complete=false`, sampai owner sendiri yang memutuskan.

---

## 0. Cara memakai dokumen ini

### 0.1 Urutan otoritas

Dokumen ini **menyatukan** aturan yang sudah ada. Ia tidak menggantikannya. Kalau isinya berbeda, urutan yang berlaku:

1. Instruksi owner paling baru, tertulis.
2. Addendum keputusan owner yang sudah disahkan (`docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`) dan errata-nya.
3. Kontrak CP7 (`docs/cp7/framework-v2/01_KONTRAK_DAN_INTEGRASI.md`, `06_RUSUK_KEBUTUHAN_OWNER.md`, `04_BUKTI_DAN_ORACLE.md`).
4. Protokol audit yang sudah ada: `docs/cp6-competition-mode-audit-protocol.md` (tingkat bukti dan kosakata hasil) dan `docs/cp6-efficient-audit-rule.md` (audit satu keluarga sekaligus).
5. Dokumen ini.

Kalau dua aturan bertentangan, catat sebagai temuan (§9) dan bawa ke owner. Sampai owner memutuskan, **aturan yang lebih ketat dipakai untuk vonis audit**: kandidat tidak dinyatakan lulus berdasarkan aturan yang lebih longgar.

### 0.2 Aturan menyunting dokumen ini (untuk Fable, Astra, Claude, dan siapa pun)

- Aturan **boleh ditambah atau dipertajam**. Aturan **tidak boleh dihapus atau dilonggarkan** tanpa instruksi tertulis owner.
- ID aturan (`INV-…`, `POLA-…`, `SKN-…`) tidak boleh diganti nomornya. Aturan baru memakai nomor berikutnya. Aturan yang sudah tidak berlaku ditandai `DICABUT (alasan, tanggal, izin owner)`; jangan dihapus.
- Setiap suntingan dicatat di §15 (Log revisi): siapa, tanggal, bagian, dan ringkasan.
- Kalimat harus bisa diuji. Tulis "jumlah debit = jumlah kredit per jurnal", bukan "jurnal harus benar".

---

## 1. Batas keamanan (tidak bisa ditawar)

1. **Tidak boleh dimutasi:** `main`, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, hanya baca), dan production.
2. **Tidak ada SQL ke database hosted.** Audit memakai database lokal sekali pakai, atau CI dengan Supabase lokal di dalam runner.
3. **Tidak mengirim pesan atau notifikasi ke orang lain.** Tidak meminta password, token, atau kunci di chat.
4. **Oracle tidak boleh dilonggarkan dan expected tidak boleh diubah supaya hijau.** Log yang gagal dan fixture yang salah disimpan. Run yang gagal tetap tercatat FAIL.
5. **Hasil lokal bukan bukti.** Beri label `LOCAL_PG16_DEV` atau `LOCAL_QUALIFIED`. Bukti penerimaan hanya dari run CI pada commit yang dipin (lihat tingkat bukti di protokol CP6).
6. **Selama audit tidak ada perbaikan.** Auditor hanya membaca, menjalankan, dan menulis laporan. Perbaikan dikerjakan sesudah penyatuan, oleh satu penulis aktif pada satu waktu.
7. **Dispatch CI hanya lewat API dengan `ref` = cabang kandidat dan `head_sha` dicatat.** Auditor tidak membuat commit di cabang kandidat, juga tidak untuk "memicu workflow". Workflow milik auditor hidup di cabang audit dan memasang kandidat lewat `ref:` sha yang dipin, bukan lewat salinan berkas.
8. **Akses baca ke proyek hosted hanya lewat SQL `read only` yang berkasnya tersimpan di repo** dan receipt-nya dicatat (tanggal, proyek, jumlah sesi lain). Siapa yang tidak punya akses baca menulis `TIDAK DAPAT DIVERIFIKASI DARI SESI INI`, bukan menyalin angka orang lain sebagai fakta.
9. **Rerun job paling banyak satu kali**, dan hanya bila job mati **sebelum satu kasus pun berjalan** (checkout, instalasi, prasyarat pemasangan seperti `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE`). Gagal kedua = nyata. Rerun dicatat beserta alasannya. Job yang sudah menjalankan kasus tidak pernah di-rerun untuk "mencoba lagi".

---

## 2. Aturan main audit independen

1. **Satu commit beku.** Owner menetapkan satu commit dan tree, misalnya `cp7/integration` di SHA tertentu. Semua auditor memakai commit yang persis sama, dan tidak ada yang menulis ke cabang itu selama audit.
2. **Tanpa saling intip.** Selama putaran audit, auditor tidak membaca laporan, catatan, cabang, atau komentar auditor lain dari putaran yang sama. Dokumen yang sudah ada sebelum putaran dimulai (handoff, kontrak, laporan lama) boleh dan wajib dibaca.
3. **Setiap auditor mengaudit penuh**, bukan dibagi per bagian. Perbedaan sudut pandang justru yang dicari. Sesudah audit penuh, setiap auditor menulis "fokus tambahan" yang menurutnya paling berisiko.
4. **Laporan per auditor** ditulis ke berkasnya sendiri dengan format §9, misalnya `AUDIT_<AUDITOR>_<SHA8>.md`. Lokasinya ditentukan owner; jangan ke berkas bersama.
5. **Identitas laporan:** commit, tree, tanggal, nama auditor, lingkungan uji (versi PostgreSQL, Node, browser), dan daftar perintah yang dijalankan.
6. **Kosakata hasil** mengikuti protokol CP6: `PASS`, `FAIL`, `INCOMPLETE`, `BLOCKED_BY_TOOLING`. Yang tidak selesai tidak boleh dihitung PASS.
7. **Tingkat bukti** mengikuti protokol CP6: `STATIC_QUALIFIED` < `LOCAL_QUALIFIED` < `NATIVE_QUALIFIED` < `NATIVE_ACCEPTED`. Setiap temuan menyebut tingkat buktinya.
8. **Identitas produk, bukan hanya commit.** Selain sha commit, auditor mencatat tree hash direktori produk (`src`, `supabase/release`, `supabase/migrations`, `scripts/cp7-src`, `supabase/dev`). Commit dokumen saja tidak membatalkan run; perubahan tree produk selama audit membatalkan semua run yang menyentuh bagian itu dan wajib diulang. Alat dispatch auditor **menolak** bila head cabang bergeser dari yang dipin (`BRANCH_MOVED`) sampai identitas produk diperiksa ulang.
9. **Label asal-bukti wajib pada setiap klaim** (bukan hanya tingkat bukti): `INDEPENDENT_NATIVE_RERUN` (auditor mendispatch dan membaca per kasus), `INDEPENDENT_SOURCE_REVIEW` (auditor membaca kode), `REUSED_WRITER_EVIDENCE` (run atau receipt penulis), `REUSED_AUDITOR_LOG_READ` (log auditor lain), `OWNER_CONFIRMED_TO_AUDITOR` (owner berkata langsung kepada auditor itu), `UNVERIFIED_OWNER_DECISION` (keputusan owner yang dikutip pihak lain), `SUPERSEDED_BY_OWNER_RULE` (skenario atau oracle yang bertentangan dengan keputusan owner yang lebih baru). **Gerbang §12 hanya boleh ditutup oleh bukti berlabel `INDEPENDENT_*`.** Run penulis boleh dipakai sebagai petunjuk, tidak pernah sebagai penutup.
10. **Job hijau bukan hasil.** Runner ketat hanya memerahkan job pada `FAIL`/`INCOMPLETE`; `COUNTEREXAMPLE` dan `NO_ROUTE` tetap hijau. Auditor wajib membaca status **per kasus** dari log (baris JSON), dan menulis hitungannya per status. "Workflow hijau" tanpa hitungan per kasus tidak diterima sebagai bukti.
11. **Setiap kasus menyatakan perannya.** Kasus menyebut peran sesi yang dipakai (owner/admin/gudang/operator) dan memanggil pembaca lewat fasad publik dengan peran itu. `permission denied for schema erp` di dalam kasus auditor adalah cacat alat auditor, dicatat `INCOMPLETE (AUDITOR_TOOL)`, bukan `PASS` dan bukan temuan produk.
12. **Register keputusan owner dibaca dulu sebelum menulis "terbuka".** Sebelum menulis pertanyaan owner, auditor mencari di register keputusan (`OWNER_DECISIONS_*`, `docs/cp6-d11-kebijakan-dan-gbd03.md`, handoff §"keputusan owner") dan di log auditor lain. Pertanyaan yang sudah dijawab owner dan ditulis ulang sebagai terbuka adalah temuan S3 atas auditornya sendiri.

**Penegasan §2.2/§2.12 (klarifikasi Fable, disampaikan owner 3 Oktober 2026):** "log auditor lain" hanya berarti dokumen yang sudah ada sebelum commit beku ditetapkan. Versi dokumen itu dicatat dengan commit/hash; perubahan dan laporan peserta dari putaran yang sedang berjalan tidak boleh dibaca sebelum seluruh laporan dikunci untuk penyatuan.

**Penegasan §2.9/§12.8 (klarifikasi Fable):** `INDEPENDENT_SOURCE_REVIEW` hanya menutup klaim statis, misalnya pola regex, deklarasi grant, hash, atau isi berkas. Keberhasilan akses, penolakan transaksi, perhitungan, race, browser, dan pemulihan adalah klaim runtime dan wajib run independen pada lapisan yang diklaim. Membaca deklarasi grant tidak membuktikan penegakan izin saat runtime. Tanda tangan/keputusan owner adalah otorisasi, bukan sesuatu yang diganti oleh run auditor.

---

## 3. Peta sistem (titik masuk membaca)

| Bagian | Isi | Mulai baca dari |
|---|---|---|
| Fondasi CP3–CP5 | Identitas, RBAC, pola, potong, pickup, BS | `docs/cp3-5-code-ownership.md`, `supabase/migrations/` |
| CP6 (keluarga AC..BF) | Saldo awal, uang muka, tutup buku per tanggal (AW), HPP bertanggal (AY/AZ), aksesori (BC), laundry (BD), kantong/celup/konversi (BE/BF), paket rilis T3 + rollback | `docs/cp6-au-r1-handoff.md` (§1–§34.9), `supabase/release/cp6-t3/` (+ `MANIFEST.json`), `scripts/cp6_layers.py` |
| CP7 kontrak | Lingkup A–G, BR, Reminder, Integrasi | `docs/cp7/framework-v2/00_MULAI_DI_SINI.md` → `01`, `04`, `06` |
| CP7 P00–P18 | Basis, facade, identitas, WIP, pembelian (P09), barang jadi (P10), penjualan (P11), nota/payroll (P12), keuangan/periode/recost (P13), jembatan E01 (P18) | `docs/cp7/P*_HANDOFF.md`, `scripts/cp7-src/*` |
| CP7 F03 / F04 / F05 | Komposisi lintas modul; perencanaan potong dan model adaptif; laporan, reminder, dan perhatian | `docs/cp7/F03_*.md`, `docs/cp7/f04/`, `docs/cp7/f05/` |
| Koreksi transaksi | Benerin nota (GPT, `cp7_note`), Benerin penerimaan dan nama/kode bahan (Claude, `cp7_receipt_fix`) | `docs/cp7/NOTE_CORRECTION_*.md`, `docs/cp7/RECEIPT_CORRECTION.md` |
| Status terbaru | Keadaan, bukti, temuan terbuka | `docs/cp7/CURRENT_STATE.json`, `docs/cp7/ACTIVE_CONTINUATION.md`, `docs/HANDOFF_CLAUDE_UNTUK_GPT_MERGE.md` (§8) |
| UI | 30 halaman `src/Connected*Page.tsx`, hook `src/useProductionMutation.ts`, pesan `src/lib/clientError.ts`, waktu WIB `src/cp6BusinessTime.ts` | `src/App.tsx` |
| Pengaman bawaan | `erp.run_v259_integrity_checks`, `erp.run_v263a_payroll_integrity_checks`, `erp.run_v267_financial_truth_checks`, `erp.run_v268_financial_report_checks`, kode cek `V2620*` | `supabase/migrations/`, `scripts/` |
| Uji | 106 workflow di `.github/workflows/`, `npm run test:security`, `check:*`, vitest, Playwright (`playwright*.config.ts`) | `package.json` |

---

## 4. Metode "baca 1-1 sampai paham"

### 4.1 Untuk setiap berkas

1. **Tujuan bisnis:** keputusan owner atau kontrak mana yang dilayani. Kalau tidak ketemu, itu temuan.
2. **Masukan dan keluaran:** tabel yang dibaca dan ditulis, fungsi yang dipanggil, dan apa yang dikembalikan.
3. **Invarian yang harus dijaga** (§5), dan baris kode mana yang menjaganya.
4. **Jalur gagal:** apa yang terjadi kalau masukan kosong, `null`, nol, negatif, sangat besar, duplikat, kedaluwarsa, tanpa izin, atau terlambat datang.
5. **Uji yang ada:** apakah uji itu benar-benar gagal kalau kodenya salah? Uji yang hanya memanggil fungsi yang sama untuk menghitung expected tidak membuktikan apa-apa (POLA-12).

### 4.2 Telusur dampak (wajib untuk setiap tabel atau fungsi yang berubah)

1. Semua penulis tabel itu: `git grep -nE "(insert into|update|delete from)\s+erp\.<tabel>"`, termasuk trigger dan fungsi `security definer`.
2. Semua pembaca: `git grep -n "erp\.<tabel>"` di `scripts/cp7-src`, `supabase/`, dan `src/`.
3. Semua pemanggil fungsi: `git grep -n "<fungsi>("`.
4. Ikuti rantainya sampai ujung:
   **dokumen → stok/roll → biaya/HPP → jurnal → utang/piutang/kas → laporan (per tanggal dan per periode) → rekomendasi/reminder → layar.**
5. Tulis setiap jalur sebagai `TERDAMPAK`, `TIDAK TERDAMPAK (alasan dari kode)`, atau `BELUM TERBUKTI`. Pencarian kata saja tidak cukup untuk menyatakan "tidak terdampak".
6. **Badan yang diuji = badan yang dipasang.** Bila probe memasang berkas dev (`supabase/dev/*.sql`) sedangkan paket rilis memakai berkas lain, auditor membuktikan dengan perbandingan byte bahwa badan dev termuat utuh di berkas rilis (hanya pembungkus guard dan baris deskripsi ledger yang boleh berbeda, dan perbedaannya disebut). Tanpa bukti itu, hasil probe berlabel `BELUM TERBUKTI` untuk paket rilis.

### 4.3 Untuk SQL

- Fungsi `security definer` wajib `set search_path`. Hak eksekusi (grant) persis seperti yang dideklarasikan. Skema privat tidak bisa dipanggil langsung.
- Urutan kunci: periode → bahan (urut id) → dokumen. Perhatikan `for update` / `for share` dan potensi deadlock.
- Setiap `limit 1` harus punya `order by` yang menentukan **dan** bukti bahwa hanya satu baris yang mungkin. Pencocokan lewat atribut yang bisa kembar (bahan, jumlah, harga) adalah bug (POLA-01).
- Setiap `coalesce(x, 0)` pada angka uang atau stok perlu dicek: apakah "tidak ada" memang berarti nol, atau sebenarnya "tidak diketahui" (INV-L03)?
- Filter status: dokumen yang dibalik (`REVERSED`), dibatalkan, atau masih draft tidak boleh ikut dihitung, kecuali memang dimaksudkan.
- Penulisan langsung ke tabel Native di luar writer Native harus terdaftar dan punya lineage (INV-K04).

### 4.4 Untuk TypeScript/UI

- Kontrak tertutup: kunci yang tidak dikenal ditolak, bukan dirender.
- Angka uang dan stok berupa string desimal, bukan `number` float. Pembulatan dan sen mengikuti kontrak.
- Aksi tulis lewat `useProductionMutation` (UUID permintaan tetap, reconcile, writer terkunci saat status tidak pasti).
- Fakta disembunyikan saat `workspaceStale` atau sesudah 403 / balasan hilang.
- Waktu dikirim sebagai jam dinding WIB lewat helper `cp6BusinessTime`.

---

## 5. Katalog invarian (hukum yang tidak boleh dilanggar)

Setiap invarian wajib diuji dari dua arah: kasus yang harus lolos dan kasus yang harus ditolak. Auditor menandai setiap invarian `PASS / FAIL / INCOMPLETE` beserta buktinya.

### 5.U Uang dan jurnal

- **INV-U01** Setiap jurnal seimbang: jumlah debit = jumlah kredit, per jurnal dan per tanggal ekonomi.
- **INV-U02** Satu kejadian bisnis menghasilkan tepat satu efek. Mengulang permintaan yang sama tidak menambah efek (INV-C01).
- **INV-U03** Pembalikan adalah kebalikan persis aslinya per akun dan dimensi (pelanggan, vendor, mandor, PO, produk). Tanggal pembalikan mengikuti aturan tanggal bisnis.
- **INV-U04** Saldo buku besar akun kontrol = jumlah subledger (utang supplier, piutang pelanggan, utang upah, uang muka, GRNI).
- **INV-U05** Saldo kas/bank = jumlah semua mutasi kas yang diposting. Tidak boleh negatif kecuali kebijakan yang disahkan mengizinkan.
- **INV-U06** Tidak ada aritmetika float untuk uang. Pembulatan sen dilakukan sekali, pada titik yang ditentukan kontrak (per baris atau per dokumen, konsisten). Selisih sen dialokasikan secara deterministik.
- **INV-U07** Pembayaran tidak boleh melebihi tagihan. Kelebihan bayar menjadi kredit atau uang muka yang tercatat, tidak hilang.
- **INV-U08** Mengubah pembayaran tidak menciptakan hak kerja atau HPP baru (pemisahan keuangan).

### 5.S Stok

- **INV-S01** Saldo stok = jumlah semua mutasi, per bahan, roll, lokasi, dan SKU/lot.
- **INV-S02** Tidak ada stok negatif pada urutan kronologis, termasuk saat pencatatan mundur (backdate) kecuali ada izin pengganti eksplisit, dan izin itu harus tercatat.
- **INV-S03** Transfer antar gudang berjumlah nol untuk total, dan nilainya ikut pindah.
- **INV-S04** Identitas roll fisik tetap. Pemakaian, transfer, dan riwayat menunjuk roll yang sama, termasuk sesudah koreksi.
- **INV-S05** Konversi satuan memakai snapshot faktor yang berlaku saat transaksi.
- **INV-S06** WIP terkonservasi: masuk = keluar + susut/BS + sisa. Satu PCS dihitung sekali.
- **INV-S07** Barang jadi per SKU/ukuran/lot terkonservasi dari QC sampai penjualan dan retur.

### 5.H HPP dan biaya

- **INV-H01** Nilai persediaan = Σ(jumlah × biaya satuan) dan cocok dengan saldo akun persediaan.
- **INV-H02** Biaya mengalir dan terkonservasi: bahan → WIP → barang jadi → HPP penjualan. Tidak ada biaya yang muncul atau hilang tanpa sumber.
- **INV-H03** Recost bersifat kronologis dan bertanggal dari barang dan pergerakannya (keluarga AY/AZ), bukan dari tanggal koreksi.
- **INV-H04** Harga perkiraan vs final: GRNI harus nol sesudah semua invoice final. Invoice terlambat mengoreksi GRNI, utang, dan HPP pada tanggal ekonominya, tanpa menciptakan stok.
- **INV-H05** Koreksi biaya merambat ke semua posisi barang: sisa bahan, WIP, barang jadi, terjual, dan diretur. Masing-masing pada tanggalnya sendiri.
- **INV-H06** HPP yang belum pasti, misalnya harga laundry belum diketahui, ditandai belum pasti dan memblokir aksi yang bergantung padanya (contoh: LAU-DEC04 memblokir penjualan).

### 5.P Utang, piutang, dan kas

- **INV-P01** Sisa utang/piutang per dokumen = total − pembayaran − retur/kredit yang dialokasikan. Tidak boleh negatif tanpa dokumen kredit.
- **INV-P02** Uang muka hanya dipakai sampai sisanya, untuk pihak yang sama, dan pada tanggal ≥ tanggal sumbernya.
- **INV-P03** Jatuh tempo dan aging dihitung dari dokumen yang aktif. Dokumen yang dibalik tidak ikut terhitung.

### 5.T Tanggal dan periode

- **INV-T01** Tanggal bisnis memakai WIB (`erp._cp3_business_date`). Transaksi sekitar tengah malam WIB tidak boleh pindah hari karena UTC.
- **INV-T02** Periode tertutup tidak berubah diam-diam. Koreksi masuk dengan tanggal ekonomi asal dan tanggal pengakuan di periode terbuka, sesuai aturan Native dan `cp7_period`.
- **INV-T03** Tidak ada kejadian fisik di masa depan. Tanggal datang tidak boleh sesudah pemakaian pertama.
- **INV-T04** Non-kebocoran waktu: menambah fakta yang baru diketahui sesudah cutoff tidak mengubah hasil "as-known" yang lama. Restatement mendapat revisi baru.

### 5.L Laporan

- **INV-L01** Setiap angka laporan berasal dari sumber kebenaran yang sama dengan buku besar dan stok, dan cocok dengan jumlahnya.
- **INV-L02** Laporan per tanggal bisa direproduksi. Laporan lama immutable; revisi menjadi dokumen baru yang tertaut.
- **INV-L03** **"Tidak diketahui" bukan nol.** Data yang tidak terbaca atau belum lengkap tampil sebagai "belum diketahui", tidak pernah 0 atau kosong yang terlihat seperti 0.
- **INV-L04** Laporan keuangan tidak boleh berstatus READY palsu. Kalau ada komponen yang belum pasti (HPP, invoice, saldo awal), statusnya ikut belum pasti.
- **INV-L05** Perbandingan periode harus sebanding (hari penuh vs hari penuh), atau diberi label yang jelas.
- **INV-L06** Membaca laporan tidak mengubah data bisnis apa pun. Bandingkan seluruh tabel operasional dan sequence sebelum dan sesudah.
- **INV-L07** Data di luar izin pengguna tidak muncul di angka, total, alasan, cache, atau prompt AI.

### 5.R Rekomendasi produksi, perencanaan, model, dan AI

- **INV-R01** Rekomendasi hanya dari data yang berlaku dan lengkap. Kalau masukan basi, sebagian, atau tidak diketahui, rekomendasinya ditandai "perlu cek data", bukan dihitung dengan angka karangan.
- **INV-R02** Setiap kartu tindakan menjawab: kerjakan apa, SKU/ukuran, berapa PCS, paling lambat kapan, kenapa sekarang, sumber apa, dan apa yang belum pasti (`06_RUSUK_KEBUTUHAN_OWNER.md` §5).
- **INV-R03** Urutan prioritas bisa dijelaskan: gap sebelum pasokan siap → deadline nyata → aksi yang lebih cepat menutup gap → ukuran yang kurang → ID stabil. Laba tidak boleh menyembunyikan gap mendesak.
- **INV-R04** Netting tidak menghitung dua kali. Draf penjualan sudah mengurangi stok barang jadi, jadi forecast sisa tidak menghitung penjualan itu lagi. Kelebihan ukuran lain tidak menutup kekurangan ukuran yang tidak bisa dikonversi.
- **INV-R05** Pasokan yang mundur tidak memperbaiki gap sebelum tanggal datang yang baru.
- **INV-R06** Model adaptif hanya dipromosikan oleh selector yang lolos uji (M01–M08 dan positive promotion). Data tipis atau seri kembali ke baseline. Holdout luar tidak dipakai untuk tuning.
- **INV-R07** Tanya AI V1 hanya membaca proyeksi yang diizinkan. Prompt memuat asumsi, unknown, dan sumber. Tidak ada auto-send, auto-writeback, kunci API, atau data di URL.
- **INV-R08** Membaca atau menghitung rekomendasi tidak membuat reservasi atau efek bisnis. Menerapkan rencana hanya lewat command sah dengan validasi ulang.
- **INV-R09** Kebutuhan bahan = kebutuhan bersih dari model potong yang lolos uji. Kalau yield atau model belum terkualifikasi, tampilkan rentang atau "belum pasti", bukan satu angka yang terlihat pasti.

### 5.K Koreksi transaksi dan riwayat

- **INV-K01** Dokumen asal yang sudah diposting tidak diubah isinya. Koreksi = pembalik Native pada waktu sumber + pengganti yang persis + lineage privat.
- **INV-K02** Efek koreksi jatuh pada tanggal ekonomi aslinya. Selisih tidak dicatat sebagai keuntungan atau kerugian hari ini, kecuali barang yang memang terjual hari ini.
- **INV-K03** Pemetaan baris lama → baru harus eksplisit (lineage per baris), bukan dicocokkan lewat atribut yang bisa kembar.
- **INV-K04** Setiap penulisan langsung ke tabel Native di luar writer Native terdaftar, alasannya ditulis, dan tercatat di lineage (`docs/cp7/RECEIPT_CORRECTION.md` butir 4 dan dokumen yang setara milik GPT).
- **INV-K05** Draft terkait (invoice, retur, pembayaran, potong, transfer) memblokir koreksi dan disebut nomornya.
- **INV-K06** Koreksi berulang (R1, R2, …) menghasilkan satu dokumen berlaku dan satu baris efektif di kartu mutasi.
- **INV-K07** Tabel fakta dan buku (jurnal, mutasi stok, fakta recost, lineage) **append-only**: `UPDATE`/`DELETE` ditolak oleh trigger bahkan untuk peran admin aplikasi. Auditor wajib mencoba merusaknya di dalam savepoint dan mencatat penolakannya (kode, misalnya `MATERIAL_ADJUSTMENT_REVALUATION_FACT_APPEND_ONLY`). Pembalikan selalu baris baru.

### 5.C Konkurensi dan idempoten

- **INV-C01** UUID permintaan yang sama dengan payload yang sama menghasilkan satu efek. UUID sama dengan payload berbeda ditolak secara atomik.
- **INV-C02** Versi baris (`row_version`, `review_token`) dicek. Data yang berubah sesudah ditinjau ditolak.
- **INV-C03** Dua sesi bersamaan menghasilkan urutan yang sah, atau salah satunya ditolak. Tidak ada efek setengah jadi.
- **INV-C04** Kegagalan di langkah terakhir membatalkan semua efek (atomik).
- **INV-C05** Balasan yang hilang bisa di-reconcile memakai UUID yang sama. Writer tetap terkunci sampai statusnya pasti.
- **INV-C06** Setiap command meninggalkan database bersih: tidak ada advisory lock tersisa, tidak ada sesi tambahan, skema `public` tidak berubah, dan batas transaksi dipulihkan penuh. Runner ketat memeriksa ini sesudah **setiap** kasus (`full_boundary_restored`, `session_leaks`), dan kasus yang melanggar ditandai `FAIL` walau oraclenya lolos.

### 5.A Akses dan keamanan

- **INV-A01** Izin dicek di awal dan di akhir command. Izin yang dicabut di tengah jalan menggagalkan transaksi tanpa sisa.
- **INV-A02** Peran nol atau nonaktif ditolak (fail-closed).
- **INV-A03** Tidak ada kunci server di artefak klien. Gate artefak UAT dan scan rahasia harus lolos.
- **INV-A04** Advisor keamanan tidak menunjukkan temuan baru di luar daftar yang sudah ditinjau.
- **INV-A05** RLS dan grant persis seperti yang dideklarasikan; tidak ada akses langsung ke skema privat.

### 5.UI Layar

- **INV-UI01** Angka yang tampil = angka sumber. Tidak ada perhitungan uang di klien yang bisa berbeda dari server.
- **INV-UI02** Sesudah 403, balasan hilang, atau pemulihan bersama, fakta lama disembunyikan sampai dibaca ulang.
- **INV-UI03** Aksi yang mengubah uang atau stok punya langkah periksa dan konfirmasi. Penolakan ditampilkan jelas dalam bahasa Indonesia.
- **INV-UI04** Tampilan desktop, HP, dan iPad menampilkan angka yang sama.

### 5.Pol Kebijakan dan keputusan owner

- **INV-POL01** Nilai kebijakan adalah pengaturan di aplikasi dengan nilai awal `PENDING_POLICY_VALUE`. **Tidak ada angka karangan.**
- **INV-POL02** Kebijakan yang masih pending membuat fitur yang bergantung padanya berstatus belum siap, bukan memakai nilai default diam-diam.
- **INV-POL03** Satu aturan bisnis, satu sumber. Dua implementasi berbeda untuk hal yang sama adalah temuan.
- **INV-POL04** Skenario uji yang oraclenya bertentangan dengan keputusan owner yang lebih baru adalah skenario **basi**, bukan bug produk. Ia ditandai `SUPERSEDED_BY_OWNER_RULE`, dipindah ke historis, dan ditulis ulang pada tingkat yang benar. **Produk tidak pernah diubah supaya skenario lama lulus.** Contoh nyata: paket uji BF yang memasang tarif laundry pada SKU, ditolak produk sesuai D13 (tarif dari vendor).
- **INV-POL05** Hasil `COUNTEREXAMPLE` yang diterima owner lewat keputusan tertulis (contoh: sen per PO, T3 = A) tetap dicatat `COUNTEREXAMPLE` dengan rujukan keputusannya. Tidak direlabel `PASS`, tidak dihapus dari matriks, dan laporan menampilkan aturannya kepada pembaca keuangan.

### 5.M Saldo awal, impor, dan cutover

- **INV-M01** Saldo awal (stok, WIP, utang, piutang, uang muka, upah) sama persis dengan dokumen sumber cutover, per baris.
- **INV-M02** Impor bersifat idempoten dan menolak baris yang tidak valid dengan alasan. Tidak ada baris yang hilang diam-diam.
- **INV-M03** Sesudah cutover, semua cek integritas bernilai nol pelanggaran.
- **INV-M04** Paket rilis diuji **dari baseline hosted yang sebenarnya**, bukan baseline yang diasumsikan. Preflight baca-saja mencatat versi ledger hosted dan objek yang ada; pemasang membawa semua pendahulu yang hilang (contoh nyata: hosted masih v2.6.20 sehingga 30 berkas CP6 membutuhkan 28 pendahulu A–AB, total 58). Hash setiap berkas pendahulu diverifikasi auditor terhadap berkas asli di repo.
- **INV-M05** Pemasang menolak sebelum mengubah admission bila: baseline berbeda, katalog G-01 bergeser, berkas sudah terpasang, endpoint salah, bukan pemilik database, atau ada maintenance lain. Semua penolakan ini punya kasus uji masing-masing, dan pemasang **tidak pernah mematikan sesi orang lain**.

### 5.N Reminder dan notifikasi

- **INV-N01** Reminder dihitung dari fakta yang berlaku. Dokumen yang dibalik atau dibatalkan tidak memunculkan alert palsu, dan episodenya selesai dengan jelas.
- **INV-N02** ACK atau snooze tidak mengubah fakta bisnis.

### 5.D Detektor, alarm, dan cek integritas

- **INV-D01** Setiap detektor punya **kontrol positif dan negatif** di run auditor: diam pada buku yang benar (0 baris), dan **naik tepat +1** ketika auditor merusak satu angka di dalam savepoint, lalu kembali 0 sesudah rollback. Detektor yang tidak bisa dibuat berbunyi berlabel `TIDAK TERUJI`, bukan `PASS`.
- **INV-D02** Detektor yang berbunyi pada buku yang benar adalah **cacat detektor** (S1), bukan alasan membuang alarm: ia disetel ulang ke tingkat yang benar (per dokumen, per fakta), dan kontrol negatifnya dibuktikan lagi sesudah disetel. Mematikan alarm memerlukan keputusan owner tertulis.
- **INV-D03** Detektor membaca tabel yang **memang ditulis mesin yang berlaku**. Detektor lama yang membaca tabel yang tidak lagi ditulis mesin baru (contoh nyata: `material_cost_revaluation_state` vs fakta v2.6.20t) adalah temuan.
- **INV-D04** Nol pelanggaran dicatat **sebelum dan sesudah** setiap skenario §7, bukan hanya di akhir run.

**Batas kesimpulan detektor (klarifikasi Fable):** kontrol negatif §5.D membuktikan kepekaan terhadap kerusakan dan jalur yang benar-benar diuji; aturan tersebut tidak menjanjikan semua kesalahan pasti tertangkap. Oracle independen dan rekonsiliasi §13 tetap wajib. Penolakan perusakan tabel append-only membuktikan pencegahan INV-K07, bukan kepekaan detektor INV-D01.

---

## 6. Pola bug yang sering lolos (wajib dicari aktif)

| ID | Pola | Contoh nyata di repo ini |
|---|---|---|
| POLA-01 | Pencocokan lewat atribut yang bisa kembar (`limit 1` tanpa kunci unik) | Baris pengganti penerimaan dicocokkan lewat bahan/harga/jumlah, sehingga lot dan catatan tertukar atau hilang (diperbaiki `19ff70ee`). Anchor baris SALE pengganti di koreksi nota (diperbaiki GPT) |
| POLA-02 | `null`/unknown dibaca sebagai 0 | AUD-A04-R2, W13 |
| POLA-03 | Status dokumen tidak difilter, sehingga yang dibalik atau draft ikut terhitung | Draft potong berstatus `CUT` dengan `material_issue_posted=false`, bukan `DRAFT` |
| POLA-04 | Zona waktu: UTC vs WIB, transaksi sekitar tengah malam, fixture "hari ini jam 10" yang gagal sebelum jam 10 | Run 37048755577 FAIL karena jam |
| POLA-05 | Tanggal efek salah: koreksi tercatat hari ini, bukan di tanggal ekonominya | Keluarga AY/AZ/AW |
| POLA-06 | Gate atau pengaman tidak ikut diperbarui saat input baru ditambahkan | `VITE_DISPOSABLE_API_PORT` membuat gate UAT gagal (diperbaiki `1c171fd9`) |
| POLA-07 | Workflow tidak terpicu karena filter path, sehingga perubahan tidak teruji | Build UX tidak dijalankan di `cp7/integration` |
| POLA-08 | Bukti yang dipin sudah basi setelah sumber berubah (hash bundle) | `CURRENT_STATE.json` sesudah SQL P09 berubah |
| POLA-09 | Dua salinan aturan atau pesan yang menyimpang | Pemetaan pesan penolakan ganda (disatukan) |
| POLA-10 | Validasi hanya di UI, tidak di server (atau sebaliknya) | — |
| POLA-11 | Pembulatan per baris vs per dokumen berbeda, sehingga selisih sen menumpuk | Keluarga sen supplier (CP6-03) |
| POLA-12 | Uji yang tautologis: expected dihitung dengan fungsi yang sama yang diuji | — |
| POLA-13 | Fakta basi di layar sesudah 403 atau balasan hilang | Panel pembetulan (diperbaiki) |
| POLA-14 | Batasan unik menyertakan atau melupakan dokumen yang dibalik (nomor dipakai ulang) | Nomor invoice unik per supplier termasuk yang dibalik |
| POLA-15 | Kinerja kuadratik pada riwayat panjang, sehingga time-out membuat proses setengah jalan atau dilewati | 364 transfer pada satu roll |
| POLA-16 | Alat auditor sendiri salah, lalu hasilnya terbaca sebagai hasil produk (bentuk skenario, peran sesi, kolom salah nama, re-pin sha mengganti semua sha 40-hex termasuk action pihak ketiga) | r12 rev1–rev4, C0 `permission denied`, BC pin rev1 (`supabase/setup-cli@<sha-salah>`) |
| POLA-17 | Skenario basi: oracle mengikuti aturan lama yang sudah dicabut owner, lalu "gagal" dibaca sebagai bug | `cp6_bf_free_modes.py` memasang tarif laundry di SKU setelah D13 |
| POLA-18 | Hasil mengekor: auditor menerima klaim karena auditor lain atau penulis sudah hijau, tanpa menjalankan sendiri | penerimaan 29 Sep yang bersandar pada run penulis untuk D07/D09/F3 |
| POLA-19 | Baseline diasumsikan: paket diuji dari AB padahal hosted masih v2.6.20 | 30 vs 58 berkas |
| POLA-20 | Prasyarat pemasangan berpacu dengan sesi sisa (database belum terkuras), job jatuh sebelum kasus apa pun | BE pin rev1 `before` |
| POLA-21 | Fixture memakai jam dinding ("hari ini jam 10") sehingga hasil tergantung jam run; fixture harus relatif ke `clock_timestamp()` | Run 37048755577 |
| POLA-22 | Pertanyaan ke owner yang sebenarnya sudah dijawab, atau pertanyaan tanpa rekomendasi default; owner dipaksa menjelaskan ulang | register D11/GBD-03/UI-01, 1 Okt |

---

## 7. Skenario wajib (matriks adversarial)

Setiap modul yang menulis uang, stok, atau HPP wajib diuji dengan skenario yang relevan di bawah ini. Kalau tidak relevan, tulis alasannya.

- **SKN-01** Data setahun penuh (≥ 364 hari aktivitas), lalu koreksi di awal tahun.
- **SKN-02** Invoice terlambat atau final mengubah harga sesudah barang dipotong, dijual, dan diretur.
- **SKN-03** Periode tertutup, lalu koreksi ke tanggal di dalamnya, lalu periode dibuka kembali.
- **SKN-04** Bayar sebagian, bayar lebih, bayar dari uang muka, refund.
- **SKN-05** Retur sebagian, retur sesudah pembayaran, retur sesudah koreksi.
- **SKN-06** Dua baris identik (SKU, jumlah, dan harga sama) dalam satu dokumen.
- **SKN-07** Sen ganjil: 1/3, 0,005, alokasi ke banyak baris; angka sangat besar (≥ 9.007.199.254.740.993) dan sangat kecil.
- **SKN-08** Nol, negatif, `null`, string kosong, unknown.
- **SKN-09** Tengah malam WIB (23:59:59 vs 00:00:00), transaksi yang melewati tengah malam.
- **SKN-10** Dua orang menyimpan bersamaan; UUID sama dikirim dua kali; payload berbeda dengan UUID sama.
- **SKN-11** Balasan hilang lalu muat ulang; izin dicabut di tengah proses; peran nonaktif.
- **SKN-12** Draft vs posted; pembalikan dari pembalikan; koreksi berulang R1, R2, R3.
- **SKN-13** Tanggal mundur (backdate) yang membuat stok negatif pada urutan kronologis.
- **SKN-14** Multi-gudang, multi-supplier, multi-mandor, multi-vendor laundry.
- **SKN-15** Salah bahan, salah gudang, salah supplier, salah tanggal, salah nomor (koreksi identitas).
- **SKN-16** Data cutover nyata (saldo awal) diproses sampai satu periode penuh.
- **SKN-17** Rekomendasi dengan data tidak lengkap: harga belum final, yield belum terkualifikasi, deadline tidak diketahui, pasokan mundur.
- **SKN-18** Laporan dibaca berulang-ulang dan dari dua sesi: hasilnya identik, dan tidak ada efek samping.
- **SKN-19** **Perusakan terkendali:** satu angka di tabel state/fakta/jurnal diubah di dalam savepoint; semua detektor terkait harus naik; rollback mengembalikan nol. Bila tabelnya append-only, penolakannya dicatat sebagai bukti INV-K07.
- **SKN-20** **Regrouping tanpa jejak fisik:** mengubah pengelompokan komersial (SKU/range/kategori) tidak menulis mutasi stok, lot, produk, jurnal, dan tidak mengubah buku; riwayat "siapa pada jam berapa" kontinu tanpa celah (`effective_to` = `effective_from` berikutnya) dan dapat dibaca untuk waktu lampau.
- **SKN-21** **Pemasangan dari hosted nyata:** salinan sekali pakai pada versi ledger hosted yang sebenarnya, dipasang penuh dengan akun non-superuser seperti hosted, lalu dicopot (rollback) tanpa sisa; semua penolakan pra-admission INV-M05 dicoba satu per satu.
- **SKN-22** **Lintas checkpoint CP1–7:** saldo awal cutover (CP6 AC..) → pembelian dan potong (CP3–5) → aksesori/laundry/konversi (BC..BF) → penjualan, retur, pembayaran (CP7 P11–P13) → laporan BR dan reminder → koreksi R1 di awal rantai → semua cek integritas nol, laporan per tanggal direproduksi, rekomendasi berubah hanya bila faktanya berubah.
- **SKN-23** **Regresi baseline:** seluruh paket regresi CP3–5 (326 + AS 34 + AR 174 + AT 16 + AU 15 kasus dan balapannya) dijalankan pada kandidat akhir; setiap kasus yang berubah status wajib punya disposisi tertulis (`EXPECTED_CHANGE` dengan kasus pengganti penulis, atau temuan).

- **SKN-24** **Sambungan antarmesin:** sumber yang ditolak matcher karena warna/SKU/range tidak cocok tidak boleh menjadi alokasi sah hanya dengan mengganti label menjadi `CANDIDATE_MATCH`. Uji pasangan cocok sebagai kontrol, lalu telusuri keluaran matcher → allocator → rencana → command publik; kelulusan kernel privat hanya menutup kernel itu.
- **SKN-25** **Gratis sah, bukan nol sembarang:** bentuk konfigurasi FREE/WAIVED yang sah menurut keputusan owner dan jalankan sampai laporan; bandingkan dengan tarif nol tanpa izin, tarif belum diketahui, serta tarif normal. Penolakan nol saja tidak membuktikan jalur gratis bekerja; konfigurasi tidak terbentuk = `INCOMPLETE`, bukan otomatis bug produk.
- **SKN-26** **Batas angka dan daftar:** uji tepat di bawah, pada, dan di atas batas tipe/skala nominal serta batas halaman yang sebenarnya. Sertakan sekitar Rp21.474.836,48 bila jalur memakai sen 32-bit, dokumen satu dan banyak baris, diskon nol, serta sumber lama setelah batas 50/200 bila batas tersebut masih dipakai. Pencarian, pilihan, total, dan ekspor harus sesuai cakupan kontraknya; halaman pertama tidak mewakili seluruh data.
- **SKN-27** **Koreksi yang benar-benar selesai:** untuk setiap jenis transaksi dalam inventaris, jalankan jalur buat → edit draft → post → koreksi/pembalikan sah → baca ulang seluruh dampak. Uji juga larangan hapus/edit dokumen posted. Penolakan yang aman tidak menggantikan bukti jalur koreksi sah yang bisa dipakai pengguna; jika tidak tersedia, catat fungsi belum lengkap.
- **SKN-28** **Batas identitas dan waktu:** ganti anggota SKU/range sebelum, tepat pada, dan sesudah komitmen transaksi, termasuk sisi asal/hasil konversi dan dokumen REVERSED. Cocokkan identitas historis, PCS, biaya, jurnal, laporan per tanggal, serta snapshot rekomendasi terhadap aturan owner; membuktikan PCS tetap tidak cukup untuk menyatakan HPP/label tetap.
- **SKN-29** **Keluaran yang benar-benar dipakai:** cocokkan angka dan izin antara RPC, layar, file laporan yang diunduh, serta proyeksi Tanya AI. Dengan peran operasional, coba filter/ID sumber yang tidak berhak, cache setelah pencabutan izin, dan instruksi yang disisipkan dalam catatan sumber. Periksa kebocoran pada isi respons, alasan, total, file, dan prompt; UI yang menyembunyikan angka saja tidak cukup. Reminder diuji sampai perubahan episode/ACK/snooze; arsip bukan bukti utang lunas. Pengiriman WA memakai transport uji tanpa penerima nyata dan tidak diklaim sebagai bukti pengiriman live.

---

## 8. Kelas keparahan

| Tingkat | Arti | Contoh |
|---|---|---|
| **S0 – Bahaya bangkrut** | Angka uang, stok, HPP, laporan, atau rekomendasi **salah tanpa ketahuan**, atau data rusak permanen | Utang tercatat lebih kecil diam-diam, HPP salah di laporan laba, rekomendasi produksi dari data basi |
| **S1 – Salah tapi tertangkap** | Angka salah tetapi pengaman atau cek integritas menolak atau menandainya; atau alur penting macet tanpa jalan keluar | Command ditolak karena bug; koreksi tidak bisa dilakukan |
| **S2 – Fungsi atau UX** | Tidak merusak angka, tetapi menyesatkan atau mempersulit | Pesan tidak jelas, tombol sulit ditemukan |
| **S3 – Dokumen atau bukti** | Klaim dokumen tidak sesuai bukti; bukti basi | Jumlah kasus di dokumen tidak sesuai manifest |

Kalau ragu, pilih yang lebih tinggi. **Semua S0 dan S1 harus selesai** sebelum gerbang §12.

Hasil non-PASS yang **bukan** cacat produk tetap ditulis, dengan klasifikasi eksplisit: `AUDITOR_TOOL` (POLA-16), `SUPERSEDED_BY_OWNER_RULE` (POLA-17), `ACCEPTED_BY_DECISION` (INV-POL05), `INFRA_RACE_RERUN_PASSED` (POLA-20, satu rerun), `GUARD_BY_DESIGN` (penjaga skenario yang memang harus merah). Tanpa klasifikasi, hasil merah dihitung sebagai temuan.

---

## 9. Format laporan auditor

```
# AUDIT <AUDITOR> — commit <sha> tree <sha> — <tanggal>
Lingkungan: <PostgreSQL/Node/browser/OS>
Perintah yang dijalankan: <daftar>

## Ringkasan
S0: n, S1: n, S2: n, S3: n — invarian PASS/FAIL/INCOMPLETE: …

## Temuan
### <AUDITOR>-001 — <judul satu kalimat>
- Keparahan: S0/S1/S2/S3
- Invarian/pola: INV-…, POLA-…
- Lokasi: path:baris (semua lokasi terkait)
- Rantai dampak: dokumen → … → laporan/layar
- Skenario yang membuatnya rusak: langkah demi langkah, dengan angka
- Bukti: TERBUKTI (perintah + output, run CI) / DUGAAN (alasan dari kode) / BELUM DIVERIFIKASI
- Tingkat bukti: STATIC/LOCAL/NATIVE_QUALIFIED
- Usulan perbaikan + uji yang harus ditambahkan (gagal sebelum, lulus sesudah)

## Matriks invarian
INV-U01 … INV-N02: PASS/FAIL/INCOMPLETE + bukti singkat

## Yang belum saya periksa (wajib)
Daftar berkas/modul/skenario yang tidak sempat atau tidak bisa diperiksa, beserta alasannya.

## Hasil merah yang bukan temuan (wajib)
Setiap FAIL/INCOMPLETE/COUNTEREXAMPLE yang tidak dihitung temuan: run, kasus, klasifikasi §8, alasan satu kalimat.

## Label asal-bukti per klaim (wajib)
Tabel klaim → label §2.9 → run/commit. Klaim tanpa label dianggap REUSED_WRITER_EVIDENCE.

## Pertanyaan untuk owner, masing-masing dengan rekomendasi auditor (wajib)
Tidak ada pertanyaan tanpa jawaban yang disarankan dan alasannya; owner cukup menjawab "ya" atau mengoreksi. Pertanyaan yang jawabannya sudah ada di register keputusan tidak boleh muncul di sini.

## Ringkasan untuk owner (bahasa sehari-hari, ≤ 10 kalimat)
Apa yang lolos, apa yang tidak, apa yang belum diperiksa siapa pun, dan apa yang harus owner putuskan.

## Fokus tambahan yang menurut saya paling berisiko
```

---

## 10. Aturan penyatuan (oleh Fable)

1. **Gabungan, bukan irisan.** Temuan yang hanya ditulis satu auditor tetap masuk.
2. **Satukan berdasarkan akar masalah.** Catat auditor mana saja yang menemukannya. Temuan yang ditemukan sendirian oleh satu auditor justru diberi perhatian lebih, karena itu titik buta yang lain.
3. **Perselisihan diputuskan dengan reproduksi, bukan suara terbanyak.** Kalau dua auditor berbeda pendapat, jalankan skenarionya. Kalau belum bisa dijalankan, statusnya `INCOMPLETE`, bukan ditutup.
4. **Keparahan diambil yang tertinggi** di antara auditor, kecuali ada bukti yang menurunkannya.
5. **Gabungkan daftar "belum diperiksa"** dari ketiga auditor. Bagian yang tidak diperiksa oleh **siapa pun** ditugaskan ke putaran kedua.
6. **Hasilnya satu register temuan** (ID baru `REG-001…` dengan rujukan ID asal), dan rencana perbaikan berurutan: S0 → S1 → S2 → S3, dikelompokkan per keluarga akar masalah (`cp6-efficient-audit-rule.md`).
7. **Tidak ada temuan yang dibuang diam-diam.** Temuan yang ditolak ditulis alasannya beserta buktinya.
8. **Konvergensi bukan bukti.** Dua auditor yang sama-sama hijau tidak menutup apa pun bila keduanya mengekor run penulis (POLA-18). Penyatu menjalankan ulang secara native setiap klaim penutup yang hanya berlabel `REUSED_*` sebelum menulis `REG-… CLOSED`.
9. **Daftar "merah yang bukan temuan"** dari semua auditor disatukan dan diperiksa silang: klasifikasi yang berbeda untuk kasus yang sama diputuskan dengan reproduksi.
10. **Register keputusan owner dimutakhirkan dalam penyatuan yang sama**: setiap keputusan baru owner dicatat verbatim (tanggal, saluran, siapa yang mendengar), skenario yang kedaluwarsa karenanya ditandai, dan daftar "terbuka untuk owner" dibersihkan dari yang sudah dijawab.

---

## 11. Aturan perbaikan

1. **Reproduksi dulu:** uji yang gagal di commit lama, lalu lulus sesudah perbaikan. Kedua hasilnya disimpan.
2. **Satu penulis aktif pada satu waktu.** Penulis tidak mengesahkan pekerjaannya sendiri; auditor lain memeriksa perbaikannya.
3. **Perbaikan minimal**, tetapi untuk seluruh keluarga akar masalah (semua jalur yang terdampak menurut §4.2).
4. **Definisi Native yang sudah diterima tidak diubah** kecuali lewat lapisan yang terdaftar (`scripts/cp6_layers.py`, `supabase/release/cp6-t3/MANIFEST.json`, `scripts/cp7-src/procurement/accepted-deltas.sql`) dengan rollback.
5. **Keputusan bisnis bukan milik auditor atau penulis.** Kalau perbaikan memerlukan keputusan (kebijakan, batas, angka), catat sebagai pertanyaan owner dan pakai `PENDING_POLICY_VALUE`.
6. Sesudah perbaikan: **jalankan ulang semua workflow yang memasang bagian yang berubah**, bukan hanya yang terpicu filter path (POLA-07). Lalu audit ulang bagian yang diubah.

---

## 12. Gerbang siap produksi (definisi selesai)

Semua butir di bawah wajib `PASS` dengan bukti. Status `production_go` tetap `false` sampai owner memutuskan sendiri.

1. Register temuan: semua S0 dan S1 tertutup dengan bukti; S2 dan S3 tertutup atau diterima owner secara tertulis.
2. Satu commit kandidat yang dipin. Seluruh CI hijau pada commit itu: semua workflow CP6/CP7, Build UX, CodeQL, advisor, browser desktop dan HP, race, dan HTTP Auth nyata.
3. Semua cek integritas (`run_v*_checks`, `V2620*`) bernilai nol pelanggaran, sebelum dan sesudah seluruh skenario §7.
4. **Uji dengan data nyata (shadow run):** data cutover asli dijalankan di lingkungan uji selama minimal satu periode tutup buku. Hasilnya dicocokkan per angka dengan catatan manual atau sistem lama: stok per roll/SKU, utang, piutang, kas, HPP per PO, dan laporan. Setiap selisih dijelaskan sampai nol.
5. Backup dan restore diuji. Rollback ke versi sebelumnya diuji tanpa sisa.
6. Pengawasan sesudah live sudah siap (§13).
7. Tanda tangan owner.
8. **Semua klaim penutup berlabel `INDEPENDENT_NATIVE_RERUN` atau `INDEPENDENT_SOURCE_REVIEW`** dari minimal satu auditor yang bukan penulisnya, dengan hitungan per kasus tercatat. Tidak ada gerbang yang ditutup oleh `REUSED_WRITER_EVIDENCE`.
9. **Setiap detektor punya bukti kontrol negatif** (INV-D01) pada kandidat akhir.
10. **Pemasangan penuh dari salinan baseline hosted nyata** (SKN-21) lulus dengan akun non-superuser, dan preflight hosted baca-saja terbaru berumur < 7 hari pada saat jendela maintenance.
11. **Daftar "belum diperiksa siapa pun"** (§10 butir 5) kosong, atau setiap sisanya diterima owner secara tertulis dengan nama bagiannya.

---

## 13. Pengawasan sesudah live

Karena nol bug tidak bisa dijamin, sistem harus menangkap kesalahan sebelum merugikan:

1. **Cek integritas harian** (`run_v*_checks`) dengan hasil yang dilihat owner. Satu pelanggaran pun menjadi alarm.
2. **Rekonsiliasi berkala:** stok fisik vs sistem (opname), saldo bank vs kas sistem, utang supplier vs tagihan supplier, piutang vs konfirmasi pelanggan.
3. **Label kepastian** di setiap laporan dan rekomendasi: angka pasti, angka belum pasti, dan data yang kurang.
4. **Keputusan besar tidak diambil dari satu angka saja.** Rekomendasi produksi dan laporan laba menampilkan sumber dan asumsinya, sehingga owner bisa mengecek sebelum bertindak.
5. Setiap koreksi tercatat dengan pelaku, alasan, dan lineage, sehingga kesalahan bisa dilacak dan dibetulkan tanpa menghapus riwayat.

---

## 14. Perintah praktis

```bash
# Identitas kandidat
git rev-parse HEAD; git rev-parse HEAD^{tree}

# Penulis dan pembaca tabel
git grep -nE "(insert into|update|delete from)\s+erp\.material_stock_movements"
git grep -n "erp\.material_stock_movements" -- scripts/cp7-src supabase src

# Frontend
npm run test:security
npx tsc -b
npx vitest run   # tes keluarga DB/Playwright butuh PostgreSQL native atau browser; bandingkan dengan baseline

# Workflow (CI adalah bukti)
ls .github/workflows/
```

Catatan lingkungan:
- Di mesin tanpa PostgreSQL native non-root dan browser Playwright, sebagian tes vitest gagal karena lingkungan (lihat `docs/HANDOFF_CLAUDE_UNTUK_GPT_MERGE.md` §5 dan §8.2). Bandingkan selalu dengan baseline commit pembanding.
- Kasus berat (misalnya 364 transfer) bisa sangat lambat di mesin lokal; pakai CI sebagai bukti.

Temuan yang sudah diketahui dan masih terbuka, untuk dicek ulang dan bukan diulang dari nol: `docs/HANDOFF_CLAUDE_UNTUK_GPT_MERGE.md` §6 dan §8.4, serta `docs/cp7/ACTIVE_CONTINUATION.md`.

---

## 15. Log revisi

| Tanggal | Penyunting | Bagian | Ringkasan |
|---|---|---|---|
| 2026-10-03 | Claude | Semua | Versi awal: aturan main, peta, metode, katalog invarian INV-*, pola POLA-01..15, skenario SKN-01..18, keparahan, format laporan, penyatuan, perbaikan, gerbang, pengawasan. |
| 2026-10-03 | Fable (auditor independen) | §1.7–1.9, §2.8–2.12, §4.2.6, §5.D (INV-D01–D04), INV-K07, INV-C06, INV-POL04–05, INV-M04–05, POLA-16..22, SKN-19..23, §8 klasifikasi non-temuan, §9 empat bagian wajib baru, §10.8–10.10, §12.8–12.11 | Hanya menambah dan mempertajam; tidak ada aturan yang dilonggarkan atau dihapus. Semua tambahan berasal dari kejadian nyata audit CP6 putaran 1–15 (alat auditor cacat, skenario basi vs D13, penerimaan yang mengekor run penulis, baseline hosted v2.6.20 vs 58 berkas, balapan prasyarat pemasangan, kontrol negatif D07, register keputusan owner yang terlewat). Ditulis di cabang audit `audit/cp6-final-20260924-gpt-a0bcadf`; auditor tidak menulis ke cabang penulis. |
| 2026-10-03 | Astra (peserta/auditor independen) | Penegasan §2.2/2.9/2.12/12.8 dan §5.D; SKN-24..29; §16 | Memasukkan tiga klarifikasi Fable yang disampaikan owner; menambah identitas lingkungan/bukti, manifest kasus, pemisahan oracle dan eksekusi, pembuktian race/balasan hilang, disiplin koreksi alat, batas hosted, inventaris fungsi CP1–7, dan tata penilaian lomba. Semua baris versi Fable dipertahankan; tambahan ini bukan hasil uji produk atau perubahan keputusan bisnis. Berlaku sama untuk semua peserta setelah panduan putaran disahkan/dibekukan. |

---

## 16. Penguatan Astra: bukti yang bisa diperiksa dan lomba yang adil

Bagian ini memperjelas pelaksanaan aturan di atas, mengikuti urutan otoritas §0.1. Tidak memberi izin hosted, tidak mengubah kontrak bisnis, dan tidak mengizinkan peserta menurunkan syarat agar lulus.

### 16.1 Bekukan paket audit, bukan nama cabangnya saja

- Manifest putaran mencatat `round_id`, waktu pembekuan, commit/tree produk, versi aturan, register keputusan owner, lingkup CP1–7, inventaris kasus wajib, lingkungan, serta peserta/penyatu. Log lama yang boleh dibaca adalah versi sebelum pembekuan (§2.2), bukan isi terbaru di cabang bergerak.
- Catat terpisah `candidate_sha`, `workflow_sha`, `harness_sha`, hash fixture/oracle, paket pemasang dan pendahulunya, lockfile, versi dependency/container, serta konfigurasi yang memengaruhi hasil (tanpa rahasia). Direktori §2.8 adalah daftar awal; pemasang, workflow, konfigurasi build, dan dependency yang memengaruhi perilaku juga masuk identitas bukti.
- Penegasan §1.7: dispatch workflow kandidat memakai ref kandidat; dispatch workflow auditor memakai ref cabang audit miliknya dan memasang produk pada `candidate_sha` yang tepat. Keduanya mencatat SHA hasil resolusi; tidak ada commit pemicu di cabang writer. Cocokkan SHA sebelum dispatch dan identitas yang benar-benar terpasang di runner.
- Perubahan produk atau aturan di tengah putaran tidak diam-diam mengganti baseline. Catat perubahan, bekukan kandidat/aturan berikutnya bersama owner, dan kualifikasi ulang bagian terdampak sesuai §4.2/§11; bukti lama tetap bertanggal dan terikat kandidat lama. Penulisan panduan ini belum memulai atau membekukan putaran.

### 16.2 Bukti per kasus dan oracle yang mandiri

- Manifest kasus dibuat sebelum eksekusi: ID stabil, kebutuhan/invarian, lapisan yang diuji, peran, prasyarat, expected, sumber oracle, dan batas klaim. Ledger hasil memuat run/attempt, ID, input/fixture hash, observed, status asli, status protokol, alasan pemetaan, dan tautan bukti. Penambahan kasus saat eksplorasi dicatat beserta alasannya; kasus gagal tidak dihapus.
- Bandingkan **himpunan ID dan jumlah kemunculan**, bukan total PASS saja: setiap kasus wajib punya tepat satu hasil kanonik; riwayat attempt tersimpan terpisah. ID hilang, duplikat tak dijelaskan, status tidak dikenal, skip, cancel, timeout, dan log terpotong tidak dihitung PASS. Tetap kumpulkan kelompok uji lain yang aman sesudah satu kelompok gagal (protokol CP6).
- `COUNTEREXAMPLE`, `NO_ROUTE`, dan hasil mentah lain tetap disimpan; normalisasi mengikuti protokol CP6 dan disposisi kontrak, tidak mengikuti warna job. Laporan menjumlahkan kasus unik, attempt, reused, dan runtime independen secara terpisah agar satu bukti tidak dihitung berkali-kali.
- Tambahkan `oracle_origin` dan `fixture_origin` selain label asal-bukti §2.9. Menjalankan tes writer sendiri membuktikan eksekusi independen, **belum** membuktikan rancangan tes/oracle independen. Setiap keluarga risiko uang, stok, HPP, akses, dan laporan mendapat kasus kontrak yang dirancang auditor sendiri; angka expected tidak dihitung oleh helper yang sedang diuji.
- Simpan expected per dimensi, bukan hanya total seimbang: pihak, SKU/ukuran/lot, akun, tanggal, sumber biaya, dan baris lineage. Total nol/imbang masih bisa menyembunyikan alokasi ke pihak atau ukuran yang salah. Uji perubahan urutan baris/pembagian batch hanya jika kontrak menyatakan hasil semestinya setara.

### 16.3 Penolakan, fixture, dan koreksi alat

- Kasus penolakan harus membuktikan prasyarat sah, kontrol positif, kode/alasan penolakan yang dimaksud, dan tidak ada efek tersisa. Menangkap sembarang exception bukan PASS. Penegasan §2.11: akses langsung fixture ke skema privat yang tidak berhak adalah cacat alat; fasad publik sah yang gagal di dalamnya dengan `permission denied` harus diselidiki sebagai kemungkinan cacat produk.
- Pisahkan snapshot sebelum command, efek sesudah command, dan keadaan sesudah cleanup. Keberhasilan bisnis dibuktikan **sebelum** rollback/disposal; "sesudah rollback semua nol" hanya bukti pemulihan. Uji atomisitas menggagalkan langkah yang dituju setelah langkah sebelumnya benar-benar tercapai.
- Batas satu rerun §1.9 tetap berlaku. Koreksi alat yang terbukti salah, reproduksi sengketa §10.3, dan uji kandidat perbaikan §11.1 adalah kualifikasi baru yang wajib mencatat alasan, diff alat/produk, versi oracle, serta hubungan ke run lama. Ini tidak mengizinkan mengganti nama kasus, UUID, seed, timeout, atau expected untuk menyembunyikan kegagalan; gagal/INCOMPLETE lama tetap tersimpan. Rerun identik sesudah kasus berjalan untuk mencari hijau dilarang.
- Kegagalan kedua sebelum kasus berjalan menutup kelayakan run, tetapi bukan dengan sendirinya bukti bug produk. Klasifikasi infra/alat/skenario basi memerlukan bukti penyebab; bila penyebab belum diketahui, tulis INCOMPLETE, bukan menuduh produk atau menganggap aman.

### 16.4 Race, balasan hilang, dan detektor harus benar-benar terpancing

- Dua proses yang diluncurkan bersamaan belum membuktikan race. Catat barrier, PID/sesi, titik tunggu atau lock yang diamati, urutan commit/release, dan hasil yang sah menurut kontrak. Untuk pencabutan izin, buktikan pencabutan sudah commit sebelum command melanjutkan titik validasi yang hendak diuji.
- Kasus balasan hilang membuktikan command asli sudah commit, respons sungguh terputus pada transport uji, lalu reconcile/replay memakai UUID yang sama. Cocokkan jumlah efek bisnis dan keadaan UI sesudah pemulihan. Mock sukses atau sekadar menampilkan pesan "jaringan gagal" tidak membuktikan alur tersebut.
- Untuk INV-D01, sebut ID detektor dan unit pelanggaran yang diharapkan naik tepat +1, lalu simpan **seluruh** keluaran detektor terkait sebelum/selama/sesudah injeksi. Jangan menyembunyikan alarm tambahan agar hitungan tampak cocok; cakupan dan hasil detektor lain dijelaskan.
- Bila append-only mencegah fixture rusak, catat bukti pencegahan. Uji sensitivitas detektor dilakukan terpisah pada salinan disposable dengan injeksi kesalahan yang didokumentasikan, lalu dibuang/dipulihkan. Catat hash/grant/trigger yang berbeda; lingkungan yang pengamannya dilemahkan tidak boleh dipakai untuk menerima keamanan kandidat asli. Tanpa injeksi yang sah dan terukur, sensitivitasnya tetap TIDAK TERUJI.

### 16.5 Cakupan penuh berarti kebutuhan sampai bisa dipakai

- Inventaris dibentuk dari kontrak/keputusan owner **dan** rute UI, fasad publik, writer, pembaca, serta tabel yang benar-benar terpasang. CP1/CP2 dicatat eksplisit juga, tidak dianggap tercakup hanya karena regresi CP3–5 lolos. Petakan setiap kebutuhan ke jalur positif, penolakan, koreksi, pembacaan hilir, dan bukti; N/A wajib alasan spesifik.
- Setiap fitur edit/delete/koreksi mengikuti kontrak status dan izin yang berlaku, bukan aturan baru auditor. Buktikan jalur sah selesai, alasan blocker menyebut sumbernya, pengguna bisa menuju penyelesaian yang tersedia, dan setelahnya stok/HPP/jurnal/laporan konsisten. Guard yang aman dengan semua jalur sah masih macet tidak dihitung "fitur selesai".
- FREE/WAIVED, UNKNOWN, policy pending, kehabisan data, dan model fallback diuji sebagai keadaan berbeda. UNKNOWN/fallback yang aman tidak menutup kebutuhan happy path dengan data sah; model juga harus punya bukti positive promotion pada data uji independen tanpa kebocoran holdout.
- Baca UI terhubung dan keluaran hilir sesuai klaim, termasuk laporan unduhan, rekomendasi SKU/prioritas, reminder produksi/aksesori/utang/piutang, serta batas koneksi WA. Tidak mengirim pesan nyata (§1.3); fungsi yang baru dibuktikan dengan transport uji ditulis demikian.
- Catat `feature_complete`, `audit_complete`, dan `production_go` terpisah dengan denominator/scope jika memakai persen. Ambiguitas keputusan atau fungsi belum terhubung tidak disamarkan dengan "100% tes lulus". Status CP6/CP7 mengacu keputusan owner terbaru; kalimat status lama dalam panduan tidak otomatis membuka kembali atau menutup checkpoint.

### 16.6 Rilis, pemulihan, dan penjagaan bukti

- §1.2 melarang SQL hosted, sedangkan §1.8 menjelaskan tata cara baca bila diizinkan. **§1.8 bukan izin baru atau pengecualian otomatis:** tanpa instruksi owner yang secara eksplisit menyelesaikan konflik ini, auditor tetap tidak menjalankan SQL hosted. Preflight dari operator yang berwenang diberi label asalnya; menyalin receipt bukan bukti auditor membacanya sendiri. Syarat baseline §12.10 tetap belum terpenuhi jika bukti yang diwajibkan belum tersedia.
- Pemasangan pada baseline disposable mencatat seluruh berkas/objek yang terpasang, bukan angka total berkas saja; perbedaan dev/release, grant, trigger, konfigurasi dan pendahulu dijelaskan. Pemasangan bersih saja tidak menggantikan uji upgrade dari baseline relevan.
- Backup/restore, rollback pemasangan, dan pembalikan transaksi adalah tiga klaim berbeda. Uji masing-masing sesuai kontrak, termasuk kondisi sudah ada transaksi setelah upgrade dan penolakan rollback yang tidak aman. Setelah pemulihan, cocokkan isi/relasi/grant serta kemampuan menjalankan command baru, bukan hanya proses keluar dengan kode 0.
- Arsip bukti memuat sumber probe, manifest, expected/observed, log asli, ringkasan dan checksum; salinan dipertahankan sebelum artifact CI kedaluwarsa. Jangan memasukkan token, password, URL bertanda tangan, atau data asli sensitif ke repo publik. Gunakan fixture sintetis untuk bukti publik; redaksi disebut dan bukti lengkap hanya di lokasi yang diizinkan owner. Ini tidak mengubah kewajiban shadow run asli §12.4.

### 16.7 Penilaian lomba dan konflik kepentingan

- Sebelum putaran dimulai, owner/penilai menetapkan lingkup, waktu, fasilitas yang tersedia, format penyerahan, dan cara penilaian yang berlaku sama. Kendala tool/akses dicatat; tidak dianggap membuktikan produk rusak atau boleh menutup celah bukti. Angka bobot lomba tidak ditetapkan sepihak oleh peserta.
- Tiap peserta mengunci laporan, manifest dan probe-nya dengan commit/hash sebelum membaca hasil putaran peserta lain. Tidak membaca log Actions, artifact, PR, atau komentar peserta lain yang membocorkan putaran itu. Paparan tak sengaja dicatat waktu/sumber/bagiannya; temuan terkait kemudian diberi label cross-check, bukan diklaim penemuan buta.
- Nilai temuan berdasarkan **akar masalah yang terbukti, dampak yang terbukti, dan kelengkapan reproduksi**, bukan banyaknya baris temuan, angka test, label S0, kecepatan memposting, atau nama model. Gejala satu akar masalah disatukan; penemuan mandiri yang sama tetap mengakui semua penemunya. Bagian dugaan dibedakan dari dampak yang sudah dibuktikan.
- Fable tetap menyatukan sesuai §10. Karena penyatu juga peserta, sengketa yang memengaruhi nilai/temuannya tidak diputuskan sendiri: auditor lain mereproduksi dan owner/penilai menetapkan keputusan. Peserta tidak menerima perbaikan hasil tulisannya sendiri; peran penulis sebelumnya di bagian terkait diungkapkan.
- Register temuan menyimpan `first_seen_sha`, `retested_sha`, status kini, bukti sebelum/sesudah, serta disposisi. Temuan yang sudah sembuh ditutup pada kandidat baru setelah uji relevan; writer tidak diminta memperbaiki ulang hanya karena laporan lama masih merah. Bukti yang belum cukup tetap terbuka sebagai kekurangan bukti, terpisah dari bug terbukti.
- Laporan untuk owner memisahkan **temuan tes sendiri**, **hasil cross-check sesudah penguncian**, dan **belum terbukti**; handoff writer menyatukan seluruhnya per akar masalah. Tidak ada bonus untuk menciptakan pekerjaan writer tanpa reproduksi yang sah.
- Kosongnya daftar "belum diperiksa" berarti seluruh inventaris wajib yang dibekukan sudah memiliki disposisi/bukti, bukan seluruh kemungkinan input sudah dicoba. Penerimaan risiko oleh owner tetap ditulis sebagai penerimaan risiko, bukan PASS pengujian. Tidak ada aturan atau pemenang lomba yang menjamin nol bug.

---

> **VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.**
