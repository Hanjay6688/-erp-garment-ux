# F05 — mulai di sini untuk writer utama

Checkpoint owner 30 September 2026. Cabang `cp7/f05-consumers-shell-20260930`, draft [PR #37](https://github.com/Hanjay6688/-erp-garment-ux/pull/37), source teruji `ec8e27890319ef898f0bb8b06028daa12a9d2f08`. Status **cangkang fixture teruji**; integrasi transaksi dan penerimaan independen belum ditutup.

## Tugas pertama, tanpa membaca ulang seluruh CP7

1. Fetch head F05 dan integrasi terbaru. Pastikan SHA F05 masih checkpoint yang diterima dan writer lain tidak mengubah berkas yang sama. Catatan ini tidak membuktikan editor chat lain berhenti.
2. Baca `docs/cp7/f05/HANDOFF.md`, dokumen ini, `YIELD_ANALYZER.md`, lalu receipt `continuation-v1/VERIFICATION.json`. Bukti awal dan `yield-v1/` adalah riwayat; jangan memakai jumlah tes lama sebagai tes source baru.
3. Jalankan perintah F05 di bawah. Untuk perubahan consumer, fokus pada keluarga yang berubah. Jangan mengulang matrix database F03/F04 yang tidak terpengaruh; native/Auth/race tetap diperlukan saat memasang reader atau command sebenarnya.
4. Integrator memutuskan entry/route/hak akses dan mapping hasil server yang sudah memenuhi kontrak. Pindahkan komponen consumer ke direktori runtime milik packet, sambungkan entry utama, lalu buktikan gate no-orphan. Preview ini tidak otomatis masuk bundle ERP utama.
5. Pasang satu irisan baca P14 → P15 → P16/P17 dengan run/scope/scenario yang sama, tanpa mengaktifkan apply/WA. Bagian yang input atau bukti upstream-nya belum tersedia tetap unavailable. Tidak perlu menunggu seluruh keluarga yang tidak menjadi ketergantungan irisan itu.

## Kondisi yang benar-benar diamati

Source F05 di atas mempunyai 47 tes unit F05, build/TypeScript/secret scan preview serta 18 cerita browser desktop/HP; hasil final ada pada receipt checkpoint. Tes ini adalah writer verification, bukan penerimaan auditor atau tes reader produksi.

Integrasi yang diamati: `3c825db217d3a495ba263cf47d1d10d05b8a8392`. `CURRENT_STATE.json` di head itu masih menyebut F03 berjalan, F04/F05 PLANNED dan seluruh connection operasional/apply/publish/WA false. F04 terpisah terakhir diamati pada `f6162a9e6f4257d4cab7181c227e7af31d415a07`; adanya branch bukan bukti engine diterima. Baca ulang head/status saat mulai. Jangan menyalin status PLANNED integrasi menjadi penilaian bahwa PR F05 tidak punya cangkang; CURRENT_STATE adalah berkas integrator dan belum kami ubah.

Framework `work_packets.json` tetap acuan dependency; kata v1 historis di input packet tidak mengganti kontrak kompilasi/fixture yang sekarang `cp7.analysis.v2`. 48 berkas framework tidak disentuh.

## Apa yang bisa dipakai dan apa yang harus disambungkan

| Bagian | Bisa dipakai dari checkpoint | Pekerjaan integrator/producer berikutnya | Dependency/gate |
| --- | --- | --- | --- |
| P14 | Kartu prioritas, ukuran fisik, alasan/refs, WIP/ETA, unknown bahan; draft Buat/Bagi lokal tetap utuh | Entry Stok/Planner/Buat/Bagi asli; reader berizin; deep link sumber; production-status command | P08/P11 menurut framework; apply harus latest-state/lock/envelope dan bukti upstream, bukan hanya tombol UI |
| P15 | Template Indonesia deterministik dari satu proyeksi; arsip/revisi/export sesi | Reader periode P13; persistence/publish/history server berizin; koreksi terhubung ke arsip immutable | P13/P14; keuangan UNKNOWN/pending tidak menjadi margin READY |
| P16 | Attention NEW/ACK/SNOOZED/DONE terpisah dari condition; manual sesi; queue WA simulasi dedupe | Facade reminder existing, condition observation lengkap, lifecycle/policy/persistensi server; trigger dan outbox dengan fencing | P15; incomplete != sehat, DONE != masalah beres. WA nyata tetap gate CP7C |
| P17 | Pertanyaan, serialized prompt, copy/open dengan manual fallback | Snapshot server yang sudah disaring izin, scope/truncation metadata, integration Auth/browser | P14; V1 tidak menambah API AI/key/chat otomatis/writeback |
| Analyzer potong | Lebar opsional dan kosong; mix berulang; range/status/reasoning dari port privat; unknown ditahan | Mapping input roll asli, keluarga bahan/pola/komposisi/unit; producer pembanding/model dan kontrak disepakati; kartu inline form asli | Range saat ini sintetis. Tidak memasang model atau schema F03/F04 lewat consumer |

Kartu analyzer saat ini memakai roll contoh yang terpisah dari draft Buat/Bagi. Tidak ada auto-trigger pada SAVE operasional. Integrasi berikutnya boleh mengevaluasi saat input relevan berubah/hasil potong lengkap, dengan debouncing/cancellation dan tanpa menghambat save; trigger final mengikuti lifecycle form asli yang diverifikasi integrator. Tidak ada jaminan cukup data setelah satu tahun.

## Peta berkas dan fungsi yang disentuh berikutnya

Root preview: `tests/cp7/browser/planner/f05-preview/`.

| Berkas/fungsi | Peran dan langkah pemakaian |
| --- | --- |
| `F05App.tsx` | Composition root menerima `readPort?: AnalysisReadPort` serta `yieldReadPort?: YieldReadPort`. Runtime tetap DEMO_SIMULATION; mengganti prop tidak membuka mode operasional. |
| `ProductionPanel.tsx` | P14; meneruskan yieldReadPort ke kartu. Tidak menambah kalkulator di JSX. |
| `CuttingYieldAnalyzer.tsx` | Render hasil dan input contoh. Guard/context serta identity pembaca membatalkan hasil lama; isi/hapus lebar juga membatalkan hasil. |
| `cuttingYieldContract.ts` | Proposal PRIVAT `f05.cutting-yield-preview.v1`, menerima SYNTHETIC_ONLY. Bukan schema RPC produksi; jangan melabeli data asli sebagai synthetic untuk melewati guard. |
| `cuttingYieldFixtures.ts` | Hanya contoh UI; angka tidak diambil sebagai normal usaha. `mix`/`example` pada signature port adalah kontrol harness, bukan request produksi. |
| `model.ts` | Period withholding, arsip immutable sesi, attention/queue simulasi dan serialisasi pertanyaan. |
| `../../../families/reports/preview/BusinessReport.tsx` | P15; jangan mengganti tanggal fixture lalu menganggap angka sebagai hasil periode lain. |
| `../../../families/reminder/preview/ReminderPanel.tsx` | P16; mutasi perhatian tidak menutup kondisi sumber. |
| `../../ai-v1/preview/AiPanel.tsx` | P17; satu authorized prompt, async clipboard success/failure dan popup fallback. |
| `src/cp7/workspace.ts` | Shared projection/read-port DEMO yang dipakai harness. Berkas bersama milik integrator; cangkang tidak menghitung forecast/netting/HPP kedua. |

Contoh dependency injection untuk **tes/harness**, dengan fungsi stabil yang disiapkan di luar render:

```tsx
<F05App runtimeMode="DEMO_SIMULATION" readPort={analysisFixtureAdapter} yieldReadPort={yieldFixtureAdapter} />
```

Reader pengganti tidak otomatis dipanggil. Snapshot lama segera disembunyikan; hasil async reader lama ditolak, dan pengguna harus memuat secara eksplisit. Saat actor_scope_id/access_epoch atau hak tampilan berubah, state workspace (arsip, antrean, draft, prompt/analyzer) dibuat ulang. Run baru dengan scope/epoch yang sama boleh mempertahankan arsip filed lama; stale tetap menahan pekerjaan baru. Belum ada verifikasi ACL server nyata.

## Keputusan owner analyzer yang tidak boleh hilang

- Lebar **tidak wajib**, kosong dari awal. Jangan isi nominal keluarga atau 0 diam-diam. Analisis tanpa lebar tetap boleh bila producer punya dukungan data dan interval valid; tidak boleh membuat SAVE cutting bergantung pada analyzer/lebar.
- Basis utama keluarga bahan (merek/pabrik/varian yang dipetakan sah), pola/revisi, meter dan komposisi ukuran. Susut mengikuti riwayat bahan, bukan asumsi semua batch mustahil berbeda.
- 28×2 + 29×2 + 30×2 berbeda dari 28×1 + 29×3 + 30×2 dan 30×6. Histori campuran tetap tidak otomatis mengajari konsumsi setiap ukuran secara terpisah. Kombinasi baru boleh UNKNOWN.
- Normal/rendah/tinggi adalah perbandingan dengan interval producer. Tampilkan sumber, dukungan data, periode, versi model/policy, alasan dan apa yang perlu diperiksa. Jangan memakai ambang ±10% atau kuota satu tahun tanpa validasi.
- Tanpa lebar/pengukuran independen, jangan memastikan sedikit akibat kain sempit, roll pendek, BS atau pencurian. BS laundry bukan bukti cacat cutting. Sisa issued − consumed bukan pengukuran sisa fisik.
- Train/calibration/test dipisah per waktu/batch. Jangan memasukkan hasil batch yang sedang dinilai ke model untuk menilai dirinya sendiri, menghitung revisi sebagai observasi baru, atau menghapus riwayat jelek demi akurasi.

Desain producer dan sumber riset ada dalam `YIELD_ANALYZER.md`; tidak perlu riset ulang sebelum mapping data yang benar tersedia.

## Verifikasi satu perintah

Dari root repo, sesudah dependency locked terpasang:

```sh
node tests/cp7/browser/planner/f05-preview/verify-f05.mjs
```

Menjalankan TypeScript, seluruh unit F05, build preview dan secret scan. Tidak menginstal dependency, mengirim WA, mengakses ERP hosted atau men-deploy. Kegagalan menghentikan langkah berikutnya dan menulis FAIL/NOT_RUN. Receipt baru berada di `test-results/f05-continuation/checks.json` bersama JSON unit; hash input ditangkap, dan perubahan input saat tes berjalan membuat verifikasi gagal. `git_head` bukan satu-satunya bukti jika working tree berubah.

Untuk browser sekaligus:

```sh
node tests/cp7/browser/planner/f05-preview/verify-f05.mjs --browser
```

Playwright/Chromium harus sudah tersedia. Browser menggunakan preview lokal port 4195 dan menolak server lama yang masih memakai port itu, supaya tidak mengetes bundle sesi lain. Jika executable Playwright yang cocok tidak tersedia, tetapkan `F05_BROWSER_EXECUTABLE` ke executable yang benar; jangan mengubah oracle untuk mengatasi masalah alat. Writer checkpoint menggunakan Chromium Headless Shell 141.0.7390.37, desktop1440×1000 dan HP412×915.

```sh
F05_BROWSER_EXECUTABLE=/path/to/headless_shell node tests/cp7/browser/planner/f05-preview/verify-f05.mjs --browser
```

`--help` menampilkan batas perintah. Main build/security/CodeQL tetap memakai CI repo yang ada. Runner ini bukan pengganti tes native/Auth integrasi, acceptance auditor, atau gate rilis. Workflow bersama belum menjalankan dedicated build/browser F05 secara otomatis; integrator dapat menambahkan runner saat F05 dipromosikan.

## Tes saat penyambungan pertama

| Skenario | Expected yang harus dibuktikan pada koneksi asli |
| --- | --- |
| Run/scope/scenario sama di Stok, panel, laporan, reminder, prompt | Angka/refs/basis identik, tidak ada kalkulator kedua atau alokasi terulang setelah filter |
| Data kosong/partial/error/stale atau role dicabut | Unknown/error nyata, tanpa fallback fixture, output lama/prompt/arsip lintas scope tidak bocor |
| Form asli masih kotor | Buka/tutup/filter panel tidak menimpa draft; read tidak mem-post ledger/reservation |
| Dua apply/double click/reload dan source berubah | Same envelope dan domain lock/latest-state; satu dampak, bukan hanya useRef UI |
| Periode harian/mingguan/custom dan invoice/koreksi terlambat | Snapshot/batas waktu/keuangan tepat; arsip lama utuh dan revisi tertaut |
| ACK/DONE/snooze saat source belum pulih/unknown | Perhatian berubah; kondisi bisnis tidak ditutup; suppress/recheck sebelum eventual dispatch |
| Width null lalu diisi/dihapus; ratio berubah; request lama selesai belakangan | Save tetap boleh tanpa width; penilaian lama ditahan; campuran unsupported tidak memakai range lama |
| Semua-30 belum punya dukungan atau data historis bias/drift | Unknown atau estimasi eksploratif sesuai policy; tidak memberi kepastian normal tanpa bukti |
| Clipboard ditolak / popup diblokir / payload besar | Fallback manual; tidak mengklaim copy/sent; metadata dan unknown tidak dipotong diam-diam |

Bukti fixture saat ini tidak menutup skenario koneksi asli di atas. Native SQL tidak dijalankan untuk tambahan F05 ini karena tidak ada SQL/DB reader/mutator baru.

## Batas penulisan dan berhenti

Writer F05 hanya menulis packet-owned paths dan `docs/cp7/f05/`. Integrator memegang App/main/routes, runtime, auth/access catalog, shared DTO/schema, source/migration/CI manifests dan CURRENT_STATE. F03/F04 tetap tidak disentuh oleh sesi F05 ini. Jangan memperluas SYNTHETIC_ONLY menjadi koneksi nyata tanpa kontrak/server reader yang disepakati, jangan men-deploy atau membuka transport untuk menutup checklist cangkang.

Jika head F05 bergerak tak dikenal atau writer utama sudah mengubah berkas yang sama, hentikan push; bandingkan delta secara read-only dan serahkan checkpoint. Jika upstream yang diperlukan belum lengkap, lanjutkan pekerjaan consumer yang independen dan tandai dependency tersebut; jangan pura-pura accepted.

## Prompt singkat untuk sesi writer berikutnya

> Lanjutkan ERP CP7 dari integrasi terbaru; baca `docs/cp7/f05/WRITER_NEXT.md` dan draft PR37. F05 adalah cangkang fixture P14–P17 dengan analyzer cutting berlebar opsional, source ec8e27890319ef898f0bb8b06028daa12a9d2f08. Verifikasi hash/receipt dan jalankan verify-f05 sebelum mengubahnya. Jangan tulis ulang cangkang atau riset. Satu integrator memegang berkas bersama; writer lain tetap di berkas terpisah. Cari irisan reader/route P14 yang dependency-nya sudah terbukti, lanjutkan ke consumer satu run yang sama, lalu buktikan Auth/dirty form/unknown/stale tanpa kalkulator kedua. Jangan aktifkan apply/publish/WA sebelum dependency dan native/public gates terkait lolos. Lebar kosong tidak menghalangi save atau penilaian yang didukung data; missing width tidak boleh diimputasi. Model/range asli belum terlatih; all-30 belum didukung bukan izin mengarang. Laporkan source/tree, tes nyata, dependency yang belum siap dan langkah persis berikutnya; production_go tetap false.
# Pintu masuk terkini · integrator CP7

Dokumen lanjutan cangkang di bawah adalah checkpoint historis. Mulai sesi writer utama dari ../CURRENT_PROGRESS.md dan ../CURRENT_STATE.json; reader/persistence/analyzer asli yang sudah tergabung tidak dikerjakan ulang dari preview fixture. Bukti Native dan scope terbukanya punya receipt terpisah. Source69 dependency navigation sedang diuji; kontrak/perintah/skenario dan first failures di ../TRANSACTION_DEPENDENCIES_HANDOFF.md. Tetap satu writer/integrator untuk berkas bersama, tanpa self-certification/hosted GO.
