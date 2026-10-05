# F05 P14–P17 — cangkang consumer teruji dengan fixture

> Pintu masuk integrator saat ini,3 Oktober2026: bagian di bawah adalah bukti cangkang/checkpoint20260930. Runtime CP7 sekarang mempunyai reader Native, publikasi/arsip/revisi, attention/policy/episode, proyeksi Tanya AI berizin dan analyzer pada form potong asli, dengan bukti terpisah di ../CURRENT_STATE.json (antara lain analysis152, attention284, learned cutting57 dan E01 bridge9). Mulai dari ../CURRENT_PROGRESS.md dan handoff paket Native yang dirujuk di sana. Status fixture lama di bawah tidak membatalkan bukti yang lebih baru, dan bukti Native terbatas tidak menutup seluruh F05/P18–P21. Jangan menyambungkan lagi port contoh sebagai data asli. WA live, API AI otomatis/writeback dan data/policy yang belum ada tetap tidak dianggap tersedia.

Status: **WRITER_FIXTURE_SHELL_VERIFIED**. Integrasi operasional, penerimaan auditor, dan production GO masih terbuka.

Sumber checkpoint awal: `373a8d64e7f459fe47d142e4bd6a42456462793f`, dari integrasi `8f2d81c0198a1c451314811d074f7c88a9cf793a`. Cabang: `cp7/f05-consumers-shell-20260930`. Hash setiap sumber ada di [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json); hasil dan batas pembuktian ada di [VERIFICATION.json](VERIFICATION.json).

## Checkpoint lanjutan writer — colokan reader dan verifikasi terarah

Mulai sesi berikutnya dari [WRITER_NEXT.md](WRITER_NEXT.md), bukan menebak dari checkpoint lama. Source terbaru: `ec8e27890319ef898f0bb8b06028daa12a9d2f08`. Peta integrasi ada di [continuation-v1/INTEGRATION_MAP.json](continuation-v1/INTEGRATION_MAP.json); receipt source ini ada di [continuation-v1/VERIFICATION.json](continuation-v1/VERIFICATION.json).

Composition root kini meneruskan `yieldReadPort` ke kartu analyzer. Pergantian pembaca menahan hasil terdahulu dan response tertunda; pergantian actor scope/access epoch membuang state sesi. Runner `verify-f05.mjs` menjalankan TypeScript, unit F05, build dan secret scan; `--browser` menambah cerita desktop/HP dan memulai preview sendiri dari root repo. Kegagalan browser pertama karena cwd server tersimpan pada `continuation-v1/evidence/FIRST_CHECKS.json`; bukan bug angka atau SQL. Receipt final membedakan PASS dengan kegagalan awal.

Checkpoint sebelum bagian ini adalah riwayat sumber masing-masing. Producer asli, DTO bersama, route/hak akses, form cutting asli, persistence report/reminder dan delivery tetap menunggu integrator/dependency; colokan test tidak membuka runtime operasional.

## Checkpoint sebelumnya — analyzer hasil potong, lebar opsional

Sumber checkpoint analyzer: `3849278b4b582ce988733278e7fe6ebf04224034`. Proposal/logic dan batas data ada di [YIELD_ANALYZER.md](YIELD_ANALYZER.md); hash sumber serta receipt terbaru ada di [yield-v1/SOURCE_MANIFEST.json](yield-v1/SOURCE_MANIFEST.json) dan [yield-v1/VERIFICATION.json](yield-v1/VERIFICATION.json). Manifest, receipt dan angka pengujian bagian “Bukti” di bawah tetap merupakan checkpoint awal.

Kartu P14 baru menerima rentang/status/penjelasan dari port privat dengan fixture sintetis. Lebar kosong dari awal, tidak diwajibkan dan tidak diimputasi; isi/hapus lebar membatalkan hasil lama. Campuran berulang dipertahankan; semua-30 tidak mengambil rentang campuran 28–30. Contoh rendah/tinggi/panjang kurang/lebar sempit menampilkan bukti yang diketahui serta pemeriksaan, tanpa memastikan penyebab kehilangan/BS.

Verifikasi terbaru: **40 tes F05, 849/849 tes unit seluruh repo, 18/18 browser desktop/HP**, TypeScript, dua build, security/static ownership dan dua secret scan lolos. Dua screenshot analyzer dan receipt JSON terkompresi tersedia dalam `yield-v1/evidence/`. Angka tetap data contoh; tidak ada producer terlatih, pembacaan cutting nyata, pembaruan kontrak shared atau pemasangan kartu pada form operasional. Lebar opsional sudah diuji pada cangkang ini; penyimpanan cutting asli tidak disentuh.

## Yang sudah bisa dicoba

| Packet | Perilaku cangkang |
| --- | --- |
| P14 | Rekomendasi SKU per ukuran fisik; rank dan alasan dari AnalysisResult; sumber/revisi, WIP, alokasi, ETA/basis, asumsi dan bahan unknown. Panel bersama dari Buat/Bagi mempertahankan draft lokal saat dibuka, difilter dan berpindah menu. Kontrol status/apply/save masih terkunci. |
| P15 | Briefing Indonesia deterministik, sumber angka, rumus/operand/kesiapan metrik, filter harian/mingguan/kustom yang menahan periode tanpa data, arsip sesi immutable, revisi terpisah dan ekspor teks. Tidak ada publish server. |
| P16 | Episode contoh dari action analisis, aksesori/AR/AP yang tetap UNKNOWN, ACK/snooze/done perhatian terpisah dari kondisi sumber; reminder manual sesi, jam contoh dan antrean WA simulasi dengan deduplikasi. Tidak ada scheduler/transport aktif. |
| P17 | Pilihan/teks pertanyaan, satu prompt dari proyeksi berizin, payload lengkap tanpa potong diam-diam, copy dengan bukti promise sukses/gagal, open ChatGPT dengan fallback popup. Tidak ada jawaban AI otomatis, API/key atau writeback. |

Semua halaman dimulai kosong. Fixture harus dipilih eksplisit. Kosong, kurang, stale, gagal baca, akses ditolak, dan akses operasional tanpa metrik keuangan diuji. Tidak ada fallback contoh saat pembacaan gagal. Pembacaan lama difencing; pengurangan hak membuang arsip, antrean, draft dan prompt sesi sebelumnya. Snapshot stale mempertahankan arsip lama tetapi menahan arsip/revisi baru serta antrean baru.

Sumber angka tetap fixture resmi `cp7.analysis.v2` dan satu `projectShell`. Tidak ada rumus forecast/netting/biaya baru di JSX. Angka 18/8 dan ETA adalah input contoh framework; kapasitas, bahan, biaya, piutang dan utang tidak direkayasa. Fixture satu tanggal tidak berubah menjadi hasil mingguan hanya karena filter diganti. Periode metrik ditampilkan terpisah dari tanggal snapshot.

## Mengapa entry masih terpisah

Gate `check-source-ownership.mjs` mewajibkan seluruh runtime di `src` terjangkau dari `src/main.tsx`. Entry utama, route/access catalog, kontrak, CSS bersama, manifest, CI dan CURRENT_STATE merupakan kepemilikan integrator. Cangkang disimpan sebagai **harness preview yang executable** dalam direktori tes milik packet, dengan TSConfig, build dan tes browser sendiri. Tidak ada penggantian gate atau penyamaran runtime sebagai berkas `.test`.

Integrator dapat memindahkan komponen murni ke direktori `src/cp7/ui`, `reports`, `reminder`, `ai-v1` yang terdaftar setelah memilih route/permission/reader. Entry demo ini tidak otomatis masuk bundle ERP utama. Berkas F03/F04, SQL, fixture bersama dan 48 berkas framework tidak diubah.

## Cara menjalankan

Jalankan dari root repositori dengan dependensi yang sudah terpasang:

```sh
npx --no-install tsc -p tests/cp7/browser/planner/f05-preview/tsconfig.json
npx --no-install vite build --config tests/cp7/browser/planner/f05-preview/vite.config.mjs
npx --no-install vite preview --config tests/cp7/browser/planner/f05-preview/vite.config.mjs --host 127.0.0.1 --port 4195 --strictPort
```

Buka `http://127.0.0.1:4195/tests/cp7/browser/planner/f05-preview/index.html`. Browser otomatis dapat menjalankan preview bila port belum aktif:

```sh
npx --no-install playwright test --config tests/cp7/browser/planner/f05-preview/playwright.config.mjs
```

`F05_BROWSER_EXECUTABLE` opsional untuk executable Chromium yang tersedia. Pada lingkungan writer, unduhan Chrome penuh versi baru menghasilkan arsip tidak valid; headless shell Chromium 141 dari paket browser stabil berhasil tersedia dan dipakai. Dependensi repo tetap sama.

## Bukti

- 20 tes F05; 829/829 tes unit seluruh repositori pada sumber final.
- 14/14 kasus browser: tujuh alur pada desktop 1440×1000 dan HP 412×915. Termasuk ekspor, draft yang tidak tertimpa, arsip/revisi/stale, ACK/UNKNOWN, antrean dedupe, akses ditolak, payload tanpa finance pada hak operasional, clipboard/popup fallback, nol console/page error, nol request ERP/eksternal dan tanpa horizontal overflow pada empat menu.
- Build utama, TypeScript/build preview, security static ownership dan secret scan kedua bundle lolos. Ini tidak menambah pembuktian native SQL F03/F04.
- Receipt JSON asli dikompresi tanpa perubahan di `evidence/unit-results.json.gz` dan `evidence/browser-results.json.gz`; delapan screenshot browser berada di `evidence/screenshots/`. Hash tersedia dalam VERIFICATION.
- Clipboard/popup sukses/gagal memakai stub yang diinjeksi ke browser. Clipboard OS asli, login/percakapan ChatGPT asli, pengiriman WA dan izin server nyata tidak diuji.
- Pemeriksaan visual writer membaca kondisi kosong, Panel produksi HP dan Tanya AI desktop. Screenshot menu lain direkam otomatis; tidak mengklaim semuanya telah diaudit visual secara independen.

Workflow CP7 Shell S0 yang sudah ada menjalankan tes unit, security, build utama, browser S0 dan CodeQL ketika branch ini dipush. Ia **belum menjalankan build/browser preview F05**. Menambahkan langkah F05 ke workflow bersama merupakan pekerjaan integrator; hasil browser F05 di sini berasal dari eksekusi lokal yang dicatat.

## Yang masih menunggu

P14 command bridge P08/P11, deep link ke dokumen asli, master-status mutation dan engine P05–P08. P15 pembaca periode/keuangan P13 serta publish/history/revision server. P16 facade reminder existing, episode/policy lengkap, persistensi ACK/snooze dan timestamp resume, scheduler/outbox server dan CP7C delivery. P17 authorized snapshot server, scope/truncation envelope serta verifikasi akses nyata.

Arsip, reminder, isian dan antrean adalah sesi lokal: hilang saat reload, hak berubah atau snapshot menjadi tidak tersedia. Snooze hanya memperagakan perhatian; tidak menjanjikan pekerjaan terjadwal. Rekaman kondisi tidak ditutup oleh DONE operator. Tidak ada rangkuman finance READY, lunas, shortage terselesaikan, optimal schedule atau production GO yang disimpulkan dari fixture ini.
