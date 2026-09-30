# Cutting-yield analyzer — satu mesin F04, consumer F05

Instruksi owner 30 September 2026: bereskan analyzer, hilangkan pembagian yang membingungkan, buat kemajuan nyata tanpa mengarang angka pabrik. Patch ada pada cabang `cp7/f04-f05-yield-analyzer-20260930`, berbasis head F05 `29f07b486e54b165f807a473370afbb01c155631`. F03, entry/kontrak bersama, manifest, CI dan framework beku tidak diubah.

## Kepemilikan tunggal

| Tanggung jawab | Pemilik | Berkas |
| --- | --- | --- |
| Memilih riwayat, dedupe/revisi/cutoff, menghitung rentang, menentukan LOW/NORMAL/HIGH dan alasan | **F04 / P07** | `scripts/cp7-src/models/cutting-yield.sql` |
| Kontrak privat, identitas input/mix dan guard hasil | **F04 / P07** | `scripts/cp7-src/models/cuttingYieldContract.ts` |
| Riwayat sintetis, runtime disposable dan uji mesin | **F04 / P07** | `tests/cp7/families/models/yield/`, `yield.test.ts` |
| Input demo, memanggil port, menahan hasil lama, menampilkan rentang/sumber/alasan | **F05 / P14** | `CuttingYieldAnalyzer.tsx`, `yieldHttpPort.ts` |
| Backend demonstrasi pada Vite lokal; bukan RPC/Worker operasional | Harness F05 untuk memanggil F04 | `yieldServer.mjs`, `vite.config.mjs` |

`cuttingYieldContract.ts` dan `cuttingYieldFixtures.ts` di direktori F05 tinggal compatibility re-export. Fixture hasil yang ditulis sebelumnya sekarang berada pada F04 sebagai **test double UI**. Entry preview memakai HTTP → SQL F04 → hasil → kartu F05. Komponen tanpa port menahan hasil; backend gagal tidak kembali ke range test double. Tidak ada mesin normal-range kedua di F05.

## Apa yang betul-betul dihitung sekarang

1. Input memakai M dan PCS sebagai string numerik; lebar boleh `null`. Merek/pabrik/material, pola dan revisinya, marker yang diketahui atau null, serta multiset ukuran membentuk identitas pembanding. Material ID harus sudah membedakan varian; belum ada mapping keluarga asli di patch ini.
2. Server memberikan riwayat dan kebijakan. Satu observasi cutting selesai per **logical roll/slice ID**; revisi bernomor tidak menambah observasi. Duplicate identik dihitung sekali, isi berbeda pada nomor revisi sama ditolak. Revisi terbaru yang diketahui sebelum cutoff dipilih; VOID/incomplete tidak kembali ke revisi lama.
3. Riwayat scope lain, roll yang sedang dinilai, sebelum window dan setelah cutoff dikeluarkan. Cutoff v1 berpresisi **tanggal**, bukan jam/transaksi. Reader produksi kelak harus mengikat watermark/version dan menentukan cutoff timestamp yang benar.
4. Cari komposisi persis dan panjang terpakai yang sama. Nilai numerik `100` dan `100.00` sama. Jika lebar diisi, hanya lebar sebanding yang sama; jika kosong, riwayat berbagai lebar dan unknown boleh bergabung, dengan basis `WITHOUT_WIDTH`. Null marker cocok dengan null, bukan semua marker.
5. Urutkan hasil historis PCS; batas bawah/atas adalah observasi pada indeks `max(1, ceil(q × jumlah pembanding))`. PostgreSQL NUMERIC menjaga jumlah besar, tanpa floating point atau perkalian meter di browser. Status LOW bila aktual < bawah, HIGH bila > atas, NORMAL bila di dalam termasuk batas.
6. Hasil membawa peer ID/revisi, periode, metode/policy, dasar lebar, aturan pemilihan dan pemeriksaan lapangan. Aktual roll kini hanya dipakai untuk perbandingan akhir, tidak untuk membentuk range.

Ini **rentang referensi empiris**, belum interval prediksi dengan coverage yang terkalibrasi. Nama DTO `EMPIRICAL_REFERENCE` sengaja membedakannya. Normal berarti berada dalam kebiasaan pembanding yang dipilih, bukan sertifikat efisiensi ideal/kualitas atau bukti kain tidak hilang.

## Kebijakan demo bukan angka bisnis

Demo memasok `minimumPeers=20`, kuantil `0.1/0.9`, window `2026-03-01` s.d. `2026-09-01` sebagai parameter uji yang terlihat dan berversi. Tidak ada default produksi. Nilai itu **bukan rekomendasi pakar, toleransi ±10%, target coverage 80%, atau syarat pabrik**. Kuantil observasi historis sendiri belum membuktikan coverage kejadian berikutnya. Kalibrasi pada batch/waktu baru dan keputusan owner diperlukan sebelum alert nyata.

Riwayat demo dibuat sintetis dan diketahui hasilnya untuk oracle; kecocokan tes tidak membuktikan akurasi lapangan. Uji revisi/ACL/cutoff menilai kode, bukan kualitas data pabrik. Batas sampel kernel 1.000 rows, slots 100. Tidak ada klaim skala ERP penuh.

## Yang sengaja belum diisi dengan dugaan

- Kombinasi baru seperti 30 semua, marker baru, panjang atau lebar yang belum mempunyai pembanding: `UNSEEN_COMBINATION`. Ada pembanding tetapi kurang dari kebijakan: `INSUFFICIENT`. Aktual belum lengkap: `INCOMPLETE`.
- Belum ada regresi campuran, interpolasi panjang/lebar, geometri marker, model susut, train/calibration/drift detector atau model aktif dari transaksi. Exact matching adalah baseline pertama; jarang READY bila data kurang bervariasi adalah batas nyata, bukan alasan mengarang.
- Meter terpakai adalah **input yang disuplai**, tidak otomatis dipercaya sebagai pengukuran fisik. Selisih declared/measured menjadi temuan bersyarat dari data uji; tidak menyimpulkan roll pendek, lebar diakali, pencurian atau BS. Tanpa pengukuran independen, penyebab tetap tidak diketahui.
- Belum ada per-size output prediction; `sizeSlots` adalah komposisi marker/rencana input, bukan pembuktian rasio dari label range atau output setelah potong. Integrator harus membuktikan mapping ini dari source asli.
- `rollId` pada kernel harus menjadi ID logical slice/kejadian, bukan physical roll yang boleh dipakai berkali-kali. Reader harus membedakan kejadian cutting, replay, pickup dan koreksi. Reader itu belum dipasang; jangan menyalin physical ID begitu saja.

## Jalur eksekusi dan batas akses

Schema privat `cp7_yield`, owner `cp7_capture`, SECURITY INVOKER, `search_path=''`; PUBLIC/anon/authenticated/service_role tidak punya akses schema/function. File SQL adalah sumber kernel, **bukan migration**. Tidak ada GRANT/RPC/registry operasional.

Runtime test membuat database disposable sendiri, memakai Unix socket tanpa listener TCP; tidak membaca URL/credential DB eksternal. CI wajib PostgreSQL native, tidak boleh green-skip. Override WASM lokal harus eksplisit; receipt melabelinya `PGLITE_LOCAL_NOT_AUTH_PROOF`. PGlite v0.5.8 hanya dependency eksternal uji lokal, tidak masuk package/lockfile ERP.

Endpoint `/__cp7_demo_yield` hanya dipasang oleh Vite preview/dev pada localhost. Ia membatasi ukuran/body/method/origin dan konteks fixture resmi; riwayat/policy dibuat server. Client tidak bisa memasok history, SQL, bounds atau URL. Ini **bukan autentikasi pengguna ERP**, bukan bukti RLS atau real role access. SQL dan history tidak masuk client bundle. Production build ERP tetap tanpa endpoint ini.

## Lanjutkan tanpa bingung

1. Periksa SHA branch, bukti `docs/cp7/f04/yield-v1/VERIFICATION.json` dan source hashes. Jangan pakai receipt checkpoint F05 lama sebagai bukti source analyzer baru.
2. Jalankan verifier. Native PostgreSQL lokal harus non-root dan terpasang pada `/usr/lib/postgresql/<major>/bin`:

```sh
node tests/cp7/browser/planner/f05-preview/verify-f05.mjs --browser
```

Untuk mesin root yang hanya mempunyai WASM lokal, pasang dependency di luar repo lalu berikan path eksplisit (jangan gunakan override untuk native CI):

```sh
npm install --prefix /tmp/cp7-yield-deps --no-audit --no-fund --ignore-scripts @electric-sql/pglite@0.5.8
F04_YIELD_PGLITE_MODULE=/tmp/cp7-yield-deps/node_modules/@electric-sql/pglite/dist/index.js node tests/cp7/browser/planner/f05-preview/verify-f05.mjs --browser
```

Browser perlu Playwright Chromium terpasang; opsi executable lokal tetap `F05_BROWSER_EXECUTABLE`. Preview menggunakan konfigurasi F05 dan port 4195 sebagaimana handoff sebelumnya.

3. Integrator memasukkan patch ini setelah cangkang F05. Path F04 math/DTO dan F05 consumer dalam satu commit bertujuan membuat dependency reviewable, bukan memindahkan kepemilikan model ke F05. Jangan mengaktifkan runtime atau mengubah canonical framework sebagai bagian patch ini.
4. Setelah input upstream dapat dibuktikan: buat reader history berizin dengan snapshot lengkap, lineage/slice, unit/family/mix yang valid dan policy bisnis yang disepakati. Promosikan DTO shared melalui integrator. Jangan melabeli data asli `SYNTHETIC_ONLY` untuk melewati guard.
5. Baru sesudah mapping dan holdout batch/waktu lolos, hubungkan kartu inline cutting; analisis boleh dipicu perubahan input/hasil lengkap dengan debounce/cancellation. **Save cutting tidak bergantung pada lebar/analyzer**. Hook form/scheduler sebenarnya belum dibuat karena milik jalur integrasi.

Riset yang mendasari cara membatasi klaim: [PostgreSQL aggregates](https://www.postgresql.org/docs/17/functions-aggregate.html), [function security](https://www.postgresql.org/docs/17/sql-createfunction.html), [NIST prediction interval](https://www.itl.nist.gov/div898/handbook/pmd/section5/pmd512.htm). Pilihan exact cohort/order statistics adalah keputusan implementasi kami, bukan pernyataan bahwa satu rumus paling cocok untuk semua bisnis. Penjelasan domain dan kandidat lanjutan tetap pada `docs/cp7/f05/YIELD_ANALYZER.md`.
