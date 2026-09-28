# CP7 S0 — cangkang terpisah

Tanggal kerja: 28 September 2026. Referensi CP6:
`da20943c25cafe887d96943428fc157f80839e24`.
Branch: `cp7/empty-body-20260928`. **CP6 HOLD; accepted execution base null;
integrasi dan production GO false.**

## Cara meninjau

Jalankan `npm ci`, `npm run build`, lalu `npm run preview` dalam checkout ini.
Buka `/cp7-preview` pada server preview, atau pilih **Pratinjau CP7** dari menu
ERP demo. Mulai dalam kondisi kosong; pilih **Contoh framework v2** secara
sengaja untuk menampilkan contoh kontrak asli. Runtime connected menolak
cangkang ini sebelum kontrol contoh dipasang.

Layar yang tersedia: prioritas produksi, Stok & saran SKU, pratinjau panel
Buat/Bagi Potongan, Business Report, Reminder, Tanya AI, preview lokal WA,
serta enam kartu benchmark bersumber. Semua consumer menerima satu hasil
analisis contoh. Belum ada kalkulator bisnis, query CP6, transaksi, penerbitan
laporan, arsip server, atau pengiriman pesan.

## Bukti lokal

| Pemeriksaan | Hasil | Arti dan batas |
|---|---|---|
| `npm test` | PASS: 54 file, 597 test | Termasuk 19 pemeriksaan kontrak/projection dan 3 DOM CP7 baru |
| `npm run build` | PASS | TypeScript, Vite, source/access/CSS ownership dan pemeriksaan artefak klien |
| `npm run test:security` | PASS | Pemeriksaan sumber/batas yang tersedia; bukan bukti native DB |
| Playwright CP7 | PASS: 6/6 | Tiga skenario pada desktop 1440×1000 dan mobile 412×915 |
| Review screenshot | PASS lokal | Desktop/mobile planner terbaca; laporan gambar di output Playwright |
| CodeQL dan CI remote | PENDING pada checkpoint ini | Status final harus dibaca pada commit PR yang benar |
| CP6/CP7 native dan independent acceptance | NOT_RUN | Tidak disimpulkan dari tes shell; 84 case ERP framework tetap terbuka |

Perintah browser: `npx --no-install playwright test --config playwright.cp7.config.ts`.
Di runner lokal, unduhan Chromium bawaan Playwright gagal validasi arsip;
dipakai Chrome for Testing headless shell **154.0.8037.57**, diunduh dari URL
resmi Google dengan verifikasi TLS dan ZIP, melalui `CP7_BROWSER_EXECUTABLE`.
CI tetap memakai browser yang dipin paket Playwright. Perbedaan ini perlu
dibaca bersama hasil CI, bukan dianggap hasil browser yang sama.

CLI agent-browser dicoba tetapi daemon gagal mulai, termasuk percobaan debug.
Verifikasi browser di atas berasal dari Playwright nyata dan inspeksi gambar,
bukan keberhasilan agent-browser. Percobaan pertama 5/6: tes belum membuka
menu mobile ERP sebelum kembali ke CP7. Langkah pengguna itu ditambahkan;
rerun lengkap 6/6. Build awal juga mengungkap impor Node di tes di dalam `src`;
tes filesystem dipindahkan ke `tests/cp7`, kemudian build dan suite lulus.

Skenario browser memeriksa kesamaan hasil lintas consumer; detail sumber;
dua pintu panel Potongan; laporan dan arsip kosong; reminder unknown; prompt
AI dan clipboard gagal; preview WA; partial/error/stale; akses ditolak;
filter; kembali ke ERP; serta tidak adanya request API/RPC/luar origin atau
console error pada alur enam consumer. Tombol apply/publish/send ditolak.
DOM + port tests terpisah menguji penolakan runtime UAT dan disposable.
Simulasi hak akses ini belum membuktikan RLS atau revocation server.

## Sambungan berikutnya

Lihat [shell-mandate.md](shell-mandate.md) untuk pembagian S0/S1 dan daftar
P00–P21 yang ditunda, [source-receipt.json](source-receipt.json) untuk hash
kontrak, serta [benchmark-decisions.md](benchmark-decisions.md) untuk sumber
pakar. Benchmark memilih kandidat metode dan skenario evaluasi; tidak ada
angka pabrik atau target layanan yang diaktifkan.

Sesudah CP6 diterima, bandingkan accepted tree dengan referensi di atas,
finalkan parser/izin/snapshot backend, hubungkan port, lalu uji angka,
keanggotaan exact size, permission, replay dan transaksi atomik. Cangkang
yang lulus S0 belum menjanjikan integrasi langsung lulus.
