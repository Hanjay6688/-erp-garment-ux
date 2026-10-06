# P19 — kernel analisis linear, hitung latar belakang, dan transport segmen

Status: bukti penulis di cabang `claude/new-session-deapao`. Ini bukan audit independen P20 dan bukan GO. `full_P19_acceptance=false`, `independent_acceptance=false`, `production_go=false`. Tidak ada batas waktu, batas body, atau nilai kebijakan pabrik yang dinaikkan atau dikarang.

## 1. Kernel analisis: kuadratik menjadi linear (sumber `90615b4c`)

**Penyebab.** Pernyataan SQL per baris yang tidak sederhana di PL/pgSQL menyalin variabel jsonb yang dirujuknya ke setiap custom plan. Ada tiga tempat yang merujuk seluruh hasil netting `n`:

- query timeline per target;
- ETA per posisi;
- alokasi per sumber.

Ketiganya membuat waktu tumbuh kuadratik terhadap jumlah target.

**Perbaikan.** Semua peta dibangun sekali di awal:

- edge dan `match_results` per target;
- ETA per posisi (semua baris disimpan, jadi posisi ambigu yang dikunjungi tetap ditolak SQLSTATE 21000 seperti subquery skalar lama);
- input teralokasi per sumber;
- sumber berarah.

Teks timeline yang dibekukan GPT (`cp7_timeline_compile_equivalence.NEW_TIMELINE`) tidak diubah satu karakter pun. Teks itu kini berjalan di blok bersarang, dengan `n` yang hanya berisi edge dan `match_results` milik target itu, dalam urutan array asli. Hasil pencarian edge pertama dan `CONFIRMED_TARGET` karena itu identik dengan sebelumnya. Penggabungan potongan hasil membaca array SQL secara langsung.

**Kontrol kesetaraan:**

| Kontrol | Isi | Hasil |
|---|---|---|
| `f05-assembly` (GPT) | 24 seed × 3 ukuran, null material, refusal 21000, kontrol negatif terhadap ab4 | lulus |
| `f05-timeline` (GPT) | pin teks timeline beku, lalu old vs new untuk 0/15/2700 event | lulus tanpa diubah |
| `f05-kernel-maps` (baru) | 60 input kaya: banyak posisi, edge ganda per (key, target), match JSON null atau tidak ada, `match_results`, sumber ganda, ETA hilang atau tanpa `result`, input null; paritas refusal; dua kasus ETA ganda (loop edge dan loop sumber) | lulus; mendeteksi semua mutan yang tidak setara (urutan edge dibalik, filter `confirmed_target` dihapus, input hanya yang pertama, `match_results` dibuang, cek 21000 loop sumber dihapus). Mutan `eta->0`→`eta->-1` setara karena kasus yang lolos selalu punya paling banyak satu ETA per posisi. |
| analysis152 Native (run 37515388149, job 112446873695) | termasuk kontrol kompilasi timeline (swap teks beku) dan pembandingan penuh dengan ab4 pada fakta Native nyata | **PASS** |

**Angka CI** (run 37515388418, job `p19-assembly` 112446871602, PostgreSQL native sekali pakai dengan stand-in sumber eksplisit; detail di `../evidence/p19/kernel-maps-90615b4c/RECEIPT.json`):

| Target | Pendahulu ab4 | Kandidat GPT sebelumnya | Sekarang | Output |
|---|---|---|---|---|
| 300 | 904,7 ms | 244,8 ms | 201,7 ms | 1.869.020 byte, identik |
| 1.200 | 13.196,1 ms | 1.113,5 ms | 784,2 ms | 7.436.505 byte, identik |
| 5.000 | 247.659,3 ms | 13.152,5 ms | **3.265,5 ms** | 30.970.077 byte, identik (sha `a1718d3d…`) |

Ini hanya kernel perakit. Capture aplikasi 5.000 target yang nyata (sumber Native, insert, serve) belum diukur, dan body 30,97 MB tetap tidak bisa lewat satu respons 8 MB. Karena itu bagian 2 diperlukan.

**Sisa biaya yang diketahui.** `fact()` memakai `set search_path`, sehingga tidak bisa di-inline. Pengerasan itu sengaja tidak diubah. Membangun `v` dan `semantic_hash` atas dokumen 31 MB sudah linear, tetapi dibatasi memori.

## 2. Hitung latar belakang dan transport segmen (sumber `c1f91041`)

**SQL** ada di `scripts/cp7-src/planning/analysis-jobs.sql`, skema privat `cp7_analysis_jobs` milik `cp7_capture`. Tabel `jobs`, `documents`, dan `segments` memakai RLS dengan kebijakan `false`. `documents` dan `segments` imutabel.

| RPC publik (`authenticated` saja) | Fungsi |
|---|---|
| `erp_cp7_request_analysis_job_v1(p_query,p_request)` | Mencatat permintaan per (aktor, UUID). Query berbeda dengan UUID yang sama ditolak `CP7_ANALYSIS_REQUEST_CHANGED`. Capture biasa yang sudah memiliki UUID itu langsung dipakai sebagai hasil (DONE, tanpa hitung ulang). Status WAITING atau FAILED tanpa worker dimulai ulang dengan `attempts+1`. |
| `erp_cp7_run_analysis_job_v1(p_request)` | Menjalankan compiler capture yang sama dengan kunci per-UUID yang sama dengan capture biasa. Semuanya berjalan dalam satu request biasa di bawah **batas 8 s yang ada**. Pembatalan karena batas itu ditangkap, lalu hanya status `FAILED`/`CP7_ANALYSIS_JOB_STOPPED` (57014) yang di-commit. Penolakan CP7 menyimpan kodenya sendiri; error lain tidak dipantulkan (`CP7_ANALYSIS_JOB_ERROR`). |
| `erp_cp7_get_analysis_job_v1(p_request)` | Status WAITING, RUNNING, DONE, atau FAILED, dengan `requested_at`, `started_at`, dan `finished_at`. RUNNING dibaca dari `pg_locks` tanpa mengambil kunci, sehingga pembacaan status tidak pernah menunda worker. |
| `erp_cp7_read_analysis_manifest_v1(p_run)` | Pemeriksaan otoritas dan keuangan setara `serve`, dilakukan sekali. Mengembalikan `source_state`, `access_epoch` (sha256 dari akses aktor saat ini), dan dokumen (byte UTF8, jumlah karakter, sha256, jumlah segmen). |
| `erp_cp7_read_analysis_segment_v1(p_run,p_index,p_access)` | Satu segmen imutabel. Mensyaratkan run milik aktor dan epoch akses yang tidak berubah. Source tidak dihitung ulang per segmen. |

**Segmen.** Satu segmen berisi 2.000.000 code point, jadi body-nya ≤ 8.000.000 byte, yaitu batas body yang sudah ada. Dokumennya adalah keluaran `serve` tanpa `source_state` yang hidup. Nilai itu datang dari manifest.

**Klien** ada di `src/nativeAnalysisTransport.ts`. Setiap segmen dicek indeks, run, jumlah code point, byte, dan sha256-nya. Sesudah itu seluruh dokumen dicek byte dan sha256-nya. Baru kemudian validator lengkap yang tidak diubah (`parseNativeAnalysis`) berjalan. Batas dokumen rakitan di klien adalah 64.000.000 byte, yaitu 8 × batas body yang ada dan sekitar 2 × Original stand-in 5.000 target. Ini batas teknis transport/memori, bukan kebijakan pabrik. Dokumen yang lebih besar ditolak utuh, dan tidak ada hasil sebagian yang ditampilkan.

**Panel** (`src/NativeAnalysisPanel.tsx`) berubah secara aditif. Ke-18 skrip browser GPT yang menunggu `erp_cp7_capture_analysis_v1` tetap berlaku.

- "Ambil analisis ERP terbaru" tetap memakai capture biasa. Kalau lewat 3 s, status berubah menjadi "Sedang dihitung sejak jam HH.MM.SS WIB (tanggal)".
- Hasil di atas batas satu body dibaca sebagai segmen dari run dan UUID yang sama. Ini berlaku juga untuk Periksa sumber, Tanya AI, dan Arsip.
- Tombol baru "Hitung di latar belakang" menyimpan UUID-nya di kunci terpisah. Sesudah reload, panel membaca status server: kalau RUNNING, panel menunggu; kalau DONE, panel mengambil segmen; kalau WAITING atau FAILED, panel menawarkan "Lanjutkan perhitungan yang sama" dengan UUID yang sama.

**Uji lokal:**
- kontrol SQL `tests/cp7/families/f05-analysis-jobs.test.ts` (stand-in), mencakup:
  - status;
  - RUNNING lewat kunci yang dipegang;
  - segmen multibyte;
  - hash;
  - penolakan epoch, aktor lain, dan indeks;
  - timeout 300 ms → FAILED, lalu attempt 2 → DONE;
  - hak dan imutabilitas;
- 6 uji unit transport;
- 6 uji DOM panel.

Suite penuh 1.578/1.578 lulus, build dan `test:security` lulus.

**Suite Native** `claude-p19-transport.yml` memakai deklarasi `P19_TRANSPORT.json` dengan 11 kasus:

| Kelompok | Kasus |
|---|---|
| Native | <ul><li>Original rakitan sama dengan `serve` dan teks tersimpan</li><li>multi-segmen tepat (satu run sintetis eksplisit, khusus transport, tanpa kredit analisis)</li><li>otoritas: aktor lain, epoch berubah, hak hilang, keuangan sama dengan `serve`, basi sama dengan `serve`, tanpa jalur API langsung</li><li>identitas UUID</li></ul> |
| Race | <ul><li>dua worker menghasilkan satu Original</li><li>kunci nyata pada `erp.products` membuat batas statement menghentikan worker, sementara status terbaca RUNNING, lalu attempt 2 → DONE</li><li>hak dicabut saat worker menunggu kunci</li></ul> |
| HTTP Auth nyata | <ul><li>alur lengkap</li><li>pengguna dinonaktifkan → 403 di kelima RPC</li></ul> |
| Browser | <ul><li>desktop: balasan run hilang sesudah commit, lalu reload dan pulih tanpa worker kedua</li><li>mobile: alur latar belakang</li></ul> |

Hasilnya dicatat di bagian 3. Kegagalan pertama disimpan apa adanya.

## 3. Hasil suite Native

Menunggu run pertama untuk `c1f91041`.

## 4. Yang masih terbuka

- **Lebih dari 8 s.** Job ini berjalan di bawah batas statement 8 s yang ada. Perhitungan yang lebih lama berhenti dengan status jujur `CP7_ANALYSIS_JOB_STOPPED`. Pekerjaan yang memang lebih lama butuh worker database di luar request HTTP, misalnya pg_cron. Itu mengubah instalasi (ekstensi di hosted) dan memerlukan batas waktu job tersendiri. Keduanya keputusan owner atau instalasi untuk P21, jadi tidak dikarang di sini.
- **Transport segmen baru untuk analisis.** Kondisi pengingat, laporan, dan klaim masih memakai batas 8 MB masing-masing.
- **Capture aplikasi penuh 5.000 target** (sumber Native nyata, serve, dan render browser) belum diukur. Latensi klik-sampai-tampil 1 s/2 s/3 s di browser juga belum dikualifikasi.
