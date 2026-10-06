# CP7 — Pemeriksaan mandiri rumus & keuangan (6 Okt 2026)

**Status: persiapan audit, BUKAN audit independen.** `independent_acceptance=false`, `production_go=false`, CP6 tetap HOLD.
Semua temuan di bawah berasal dari pembacaan kode + reproduksi lokal (PostgreSQL 16 sekali pakai / node), lalu diperbaiki di
cabang `claude/new-session-deapao` dengan uji yang **gagal pada kode lama** dan lulus sesudahnya (kecuali disebut lain).
Hasil lokal LOCAL_PG16_DEV bukan bukti; bukti adalah run CI yang dicatat per baris.

Cakupan: keuangan inti (laba rugi, posisi, arus kas), penjualan/piutang, pembelian/hutang, payroll, persediaan/HPP/model potong,
perencanaan (sebagian; pemeriksa perencanaan dihentikan lebih awal untuk menghindari tumpang tindih dengan kerja kernel P19).

## 1. Ringkasan rumus inti yang diperiksa dan BENAR

| Rumus | Lokasi | Hasil |
|---|---|---|
| Laba kotor = pendapatan penjualan (bersih retur/diskon) − HPP | native snapshot, `planning/analysis-finance.sql` | benar (bukan pendapatan saja) |
| Laba bersih = laba kotor + pendapatan lain − beban | native snapshot | benar |
| Posisi: aset = liabilitas + ekuitas + laba berjalan | native, `financeReportContract.ts` | benar |
| Arus kas: saldo awal + debit − kredit = saldo akhir; transfer antar rekening netto 0 | `finance/analysis.sql` | benar, BigInt di parser |
| Piutang: bruto − retur = neto; sisa = neto − dibayar; retur ≤ jual per alokasi | `sales/*.sql`, `salesReadContract.ts` | benar |
| Hutang: sisa = AP final − pembayaran; pembayaran ≤ sisa; konversi satuan beli dikali faktor | `invoices/*`, `procurement/*` | benar |
| Payroll: net = upah kerja + absensi + reimburse − potongan + manual; cicilan berjumlah tepat net | `payroll/*` | benar |
| Stok FG: fisik = tersedia + reservasi; koreksi hitung = hitung − buku | `fg/*`, `materials/*` | benar |
| Nilai persediaan = qty × HPP lot (unknown tetap null, bukan 0) | `fg/*` | benar |
| Target perencanaan: ceil(D×(L+R+B)); kuantil empiris = sampel ke-ceil(q·n) | `baseline/target.sql` | benar |

## 2. Temuan yang DIPERBAIKI

| ID | Area | Cacat | Perbaikan | Uji (gagal di kode lama) | Commit |
|---|---|---|---|---|---|
| FIN-1 | Analisis keuangan | Pertumbuhan penjualan dibagi pembanding bertanda: pembanding −1.000.000 → +5.000.000 tampil **−600%** | `null` (N/A) bila pembanding ≤ 0; `formula_version` → `GROWTH_POSITIVE_BASE_AND_GROSS_MARGIN_PP_V2` | Native P13 `ZERO_BASELINE` (pendapatan minus: growth −130, margin null; pembanding minus: keduanya null) + parser | `17ce3f76` (CI P13 Claude: success 37524128572) |
| FIN-2 | Analisis keuangan | Perubahan margin kotor dihitung pada pendapatan minus: rugi kotor tampil **+40% margin** | `null` bila pendapatan salah satu periode ≤ 0 | sama | `17ce3f76` |
| FIN-3 | Demo halaman Keuangan (juga di `main`) | Kartu "LABA KOTOR AGU Rp141 jt · 34,1%" memakai **penjualan bruto sebelum retur**; Laba Rugi: 406,1 − 272,9 = **133,2 jt (32,8%)**. Alert GRNI (3 / Rp48,3 jt) dan posisi (hutang 77,76 jt, payroll 28,34 jt) tidak cocok dengan data AP/payroll | Satu set operand untuk kartu, grafik, Laba Rugi; posisi dihitung dari data yang sama, ekuitas sebagai sisa penyeimbang | typecheck; tampilan diperiksa di preview | `3d4cfbea` (+ PR demo main) |
| AP-1 | Koreksi penerimaan | `restate_all` memindahkan tanggal **semua** pembalikan pembayaran supplier, termasuk pembatalan lama/koreksi pembayaran → kas & hutang periode lama salah (contoh: kas 09-01 +100.000 padahal −900.000) | Hanya pembalikan yang dibuat perintah ini (`created_at = statement_timestamp()`) | Native `RF_OVERPAID_CREDIT_TO_NEXT_NOTA` + pembayaran yang dibatalkan lebih dulu | `2d4f5f38` |
| AP-2 | Koreksi penerimaan | Penghalang "kredit supplier aktif" tidak pernah hilang setelah kredit dikembalikan (tabel append-only, netto 0) | Hitung netto per retur/sumber/target ≠ 0 | Native baru `RF_CREDIT_RESTORED_UNBLOCKS` | `2d4f5f38` |
| AP-3 | Koreksi pembayaran supplier | Tanggal pengganti boleh di masa depan / sebelum barang datang (jalur buat baru menolak) | Aturan sama dengan jalur buat; panel menolak masa depan | Native `CP7_SUPPLIER_PAYMENT_CORRECTION_FIELDS` | `2d4f5f38` |
| AP-4 | Layar koreksi penerimaan | Diskon 100% ditolak karena float JS (2,3 × 15.750,5 = 36.226,149999…) | Perbandingan eksak BigInt mikro | `receiptCorrectionContract.test.ts` | `2d4f5f38` |
| SL-1 | Koreksi nota penjualan | Pembayaran hasil realokasi Native diputar ulang di jam terima asal, bukan tanggal realokasi → kas/piutang per tanggal salah | Ditolak (`CP7_NOTE_REALLOCATED_PAYMENT_REVIEW_REQUIRED`), sama dengan koreksi pembayaran | Native `NOTE_REVIEW_CHANGED…` diperluas | `2d4f5f38` |
| SL-2 | Koreksi retur | Baris alokasi baru otomatis qty 1 & **refund Rp0,00** → retur pengganti berkredit 0 bila tidak diubah | Baris baru kosong; wajib diisi | DOM test baru | `2d4f5f38` |
| SL-3 | Pembayaran penjualan | Saldo kredit pelanggan (sisa minus) membuat panel error saat render | Sen bertanda; ≤ 0 berarti tidak ada yang dibayar | DOM test baru | `2d4f5f38` |
| PR-1 | Data pekerja | Edit pekerja (`UPDATE_WORKER`) **menghapus kode pekerja** | Kode dari baris terkunci dibawa ke penulis Native | Native roster lifecycle | `2d4f5f38` |
| PR-2 | Payroll | `totals_match_items` memakai flag absensi master terbaru untuk payroll beku → tombol pelunasan terkunci keliru | Payroll APPROVED/PAID/REVERSED dibandingkan dengan itemnya sendiri | (repro stub; Native fixture absensi>0 belum tersedia) | `2d4f5f38` |
| PR-3 | Tarif harian | "75.000" tersimpan Rp75 (titik dibaca desimal) | Ditolak dengan pesan jelas; kontrak 6 desimal tetap | DOM test | `2d4f5f38` |
| AP-6 | Penerimaan, invoice supplier, hitung fisik, koreksi penerimaan | Harga/diskon rupiah "16.000" atau "1,500" diterima sebagai **Rp16 / Rp1,5** (field 6 desimal) | `moneyDecimal`: pola ribuan ambigu ditolak dengan pesan "… akan terbaca sebagai desimal, bukan ribuan. Tulis tanpa titik atau koma, misalnya 16000."; harga tersimpan yang tidak diubah tetap diterima. Pembayaran (2 desimal) sudah menolak sejak awal | `receiptCorrectionContract.test.ts` (gagal di kode lama), DOM `PurchaseInvoicePanel`, unit `moneyDecimal` | `06ce804b` (CI Shell/Build hijau di `dc7ee30c`) |
| PR-5 | Absensi | Pratinjau absensi menulis "Perkiraan upah Rp…" padahal angkanya hari dibayar × tarif harian, termasuk pekerja borongan/tanpa tarif harian; upah sebenarnya dihitung payroll | Label "Nilai absensi" + keterangan "bukan upah payroll"; angka Native tidak diubah | DOM `AttendanceEntryEditor`, oracle browser P12 memakai label baru dengan angka yang sama | `434b7c58` (P12 `--attendance-write` 37533256167: success) |
| IN-4 | Kartu stok FG (buku v2 terkoreksi) | Tiap mutasi tertulis "HPP tercatat Rp…" padahal v2 memakai **HPP lot saat ini** (sama di semua baris), bukan HPP saat mutasi | Layar v2: "HPP lot saat ini"; v1 tetap "HPP tercatat" (snapshot per mutasi). String `basis` kontrak tidak diubah (kompatibilitas parser/oracle) | DOM `ConnectedFgStockPage` (gagal di kode lama) | `434b7c58` |
| SL-4 | Koreksi nota penjualan | Retur lama diputar ulang dengan **refund lama** walau harga bersih per pcs baris itu dikoreksi: harga naik → piutang lebih (contoh retur 5 pcs refund 125 @25, harga jadi 30 → piutang +25); harga turun → ditolak Native tanpa penjelasan | Server menolak `CP7_NOTE_RETURNED_LINE_PRICE_CHANGED` bila (qty×harga−diskon)/qty baris yang diretur berubah; layar menjelaskan: betulkan/batalkan retur dulu lalu betulkan harga. Koreksi qty dengan harga per pcs sama tetap jalan. Pesan untuk SL-1 (`…REALLOCATED_PAYMENT…`) juga ditambahkan | Native `NOTE_FINANCIAL` diperkuat: 25→30 dan 25→20 ditolak, snapshot Native+privat identik; `clientError.test.ts` | `dc7ee30c` + `8a84faf8` (Note Correction 37534119936: success) |
| IN-1 | Model hasil potong | Fold latih ikut batch sebelum aturan dicatat (6 batch bukan 3) | Kernel hanya menerima record batch prospektif terpilih | `cutting-model-producer.test.ts` (6≠3) | `3d4cfbea` |
| IN-2 | Model hasil potong | Batch sesudahnya yang tercatat di dalam fold terakhir masuk holdout (4 bukan 3) | idem | idem (4≠3) | `3d4cfbea` |

### 2b. Perencanaan (pemeriksa perencanaan dilanjutkan sampai selesai)

| ID | Area | Cacat | Perbaikan | Uji | Commit |
|---|---|---|---|---|---|
| PL-1 | Estimasi permintaan → target | Laju harian dibulatkan ke atas di 12 desimal; permintaan horizon yang bulat jadi +1 pcs di `ceil` (20 pcs/30 hari × 30 hari → target **21**, bukan 20; 200/30 × 15 → 101). Ikut menimbulkan "gap" palsu 0,000000000001 di timeline netting | `trunc(...,12)`: laju tidak pernah melebihi nilai eksak; karena pecahan sejati ≥ 1/hari, tidak pernah turun di bawah bilangan bulat | `f04-demand-estimate-rounding.test.ts` (gagal di kode lama: 21/3/101) + 120 kasus acak = ceil eksak BigInt | `d7548eb8` |
| PL-2 | Netting | Posisi WIP yang sisanya 0 (bukti di graf, mis. saldo awal sudah jadi FG) dimasukkan sebagai suplai dengan qty/ETA tidak diketahui → status target **UNKNOWN selamanya**, gap null, kebutuhan kain/aksesori null | Lewati posisi `remaining_pcs = 0`, sama seperti loop anggaran di atasnya | repro kernel (agen, PG16 lokal); suite Native P08/analisis di CI | `d7548eb8` |

## 3. Temuan yang SESUAI DESAIN / tidak diubah (alasan dicatat)

| ID | Temuan | Alasan |
|---|---|---|
| IN-3 | Potongan dengan output 0 diterima sebagai observasi | Oracle yang ada mematok "explicit zero output" dipertahankan; ringkasan `cutting-yield/source.sql` memakai aturan berbeda (hanya label) |
| PR-4 | Tarif 6 desimal vs snapshot payroll 2 desimal | Desain Native (versi tarif numeric 6, snapshot numeric(18,2)) |
| SL-6 | Garis keturunan koreksi tidak terlihat oleh realokasi Native | Tidak terjangkau dari UI CP7; butuh guard di Native (di luar CP7) |
| FIN-5 | Perbandingan laporan tidak mencocokkan periode | Periode kedua laporan ditampilkan; perbandingan bulan-ke-bulan memang beda panjang |
| — | Kunci "Laba/rugi berjalan" = akumulasi belum ditutup | Label diperjelas di laporan posisi (`17ce3f76`) |

## 4. Temuan TERBUKA (perlu keputusan/desain, tidak diubah diam-diam)

| ID | Temuan | Rekomendasi |
|---|---|---|
| SL-4 | ~~Koreksi nota menyalin refund retur lama setelah harga berubah~~ | **Diperbaiki (gagal-tertutup)** — lihat §2 |
| SL-5 | Beberapa pembaca uang mengeluarkan `::text` tanpa `round(…,2)` | Moot bila kolom `numeric(…,2)`; seragamkan bila skala kolom berbeda |
| AP-5 | Pengingat hutang memakai jatuh tempo invoice paling awal walau invoice itu sudah tertutup pembayaran | **Tetap, dicatat**: pembayaran supplier Native per penerimaan, bukan per invoice, jadi "invoice mana yang lunas" butuh aturan FIFO yang belum disahkan. Arah salahnya aman (pengingat muncul lebih awal, tidak pernah terlambat); tidak ada angka uang yang berubah |
| AP-6 | ~~Input "16.000" dibaca 16 (harga)~~ | **Diperbaiki** — lihat §2 |
| AP-7 | Total koreksi dibulatkan sekali vs AP Native per baris | Pastikan skala `net_amount` Native; bila 2 desimal, jumlahkan per baris |
| PR-5 | ~~"Perkiraan upah" absensi ≠ upah payroll (ikut PIECE/NONE)~~ **Diperbaiki (label)** — lihat §2 | Ganti label menjadi nilai absensi, atau hitung hanya DAILY/HYBRID |
| PR-6 | Payroll APPROVED dengan net minus menyembunyikan detail | Edge legacy; terima net < 0 sebagai tidak dapat dibayar |
| IN-4 | ~~Basis label buku FG v2 "movement snapshot" padahal HPP lot terkini~~ **Diperbaiki (label layar)** — lihat §2 | Ganti nama basis & label "HPP lot saat ini" |
| FIN-4 | ~~Pembanding default bukan bulan kalender sebelumnya~~ | **Diperbaiki** (commit `8b5b6c21`): bulan penuh → bulan sebelumnya; MTD → hari yang sama bulan sebelumnya |
| PL-3 | Evaluasi model tidak pernah menyelesaikan fold pada data Native (cutoff latih = akhir hari origin, padahal capture selalu sesudahnya) → selalu `BASELINE_RETAINED` | Keputusan kontrak: cutoff = akhir hari origin+1 (prakiraan diterbitkan sesudah hari tutup) atau latih `lo..origin-1`. Aman sekarang (gagal-tertutup ke baseline) |
| PL-4 | Kapasitas mengabaikan beban yang melebihi jendela (tidak dibawa ke jendela berikutnya) | Bawa kelebihan ke jendela berikut atau UNKNOWN bila overbooked > 0 |
| PL-5 | Preflight rencana membandingkan pcs potong dengan gap pcs bagus tanpa yield (gap 100, yield 9/10 → seharusnya potong 112) | Bandingkan dengan `ceil(gap×den/num)` dari yield yang ditinjau, atau laporkan sisa `gap − floor(total×num/den)` Yield mana yang berlaku untuk start baru adalah nilai kebijakan → tetap PENDING_POLICY_VALUE, tidak dikarang |
| PL-6 | Kebutuhan bahan tetap tampil untuk produk PAUSED/STOPPED | **Sesuai desain (diperiksa ulang)**: kernel kain menandai baris itu `disabled=true` dan `claimant=false`, sehingga produk tersebut tidak mengambil stok/komitmen kain bersama dan tidak menimbulkan baris tak-terselesaikan; angka gross hanya informasi resep |
| PL-7 | Rencana yang sudah dipotong tidak mengurangi gap produknya (bisa direncanakan dua kali) | Hitung posisi CUT dari intent rencana sebagai suplai produk itu, atau blok preflight selama grup intent masih punya WIP |
| PL-8 | `supply-source` mengambil semua grup potong yang pernah ada (batas 1001) | Skala: pangkas grup yang sudah habis |

## 5. Uji & CI

Lokal (bukan bukti): uji DOM/unit yang disebut di §2, `cutting-model-producer.test.ts` (2 uji baru gagal di kode lama 6≠3 / 4≠3, lulus sesudahnya), typecheck.

## 6. Hasil CI per commit (cabang `claude/new-session-deapao`)

| Commit | Isi | Hasil |
|---|---|---|
| `17ce3f76` | FIN-1/FIN-2 | Build UX, Shell, **P13 Finance (Claude) 37524128572**, Receipt Correction, P18, P21, Supplier Payment Create, CodeQL: **success** |
| `2d4f5f38` | AP-1..4, SL-1..3, PR-1..3 | **Receipt Correction 37525626638 success** (AP-1/AP-2 + `RF_CREDIT_RESTORED_UNBLOCKS`), **Supplier Payment Correction 37525626741 success** (AP-3), **Note Correction 37525626878 success** (SL-1), P12 `--roster` success (PR-1), P18, P21, Build: success. P12 `--payroll-review`: semua kasus Native/HTTP PASS (termasuk PR-2), browser review lama INCOMPLETE karena oracle masih mencari `.cpay-net` "Bersih payroll" yang dipindah oleh F03 E05 (masalah lama, tidak dilonggarkan; dicatat). Supplier Payment Create: satu kasus INCOMPLETE karena `public_schema_unchanged=false` (semua asersi kasus PASS); run berikut pada kode yang sama + perubahan lain (`3d4cfbea`) **success 37526050957** |
| `3d4cfbea` | IN-1/IN-2, FIN-3 | Build, CodeQL, Receipt Correction, P18, P21, Shell, Supplier Payment Create: **success** |
| `bd92ce8e` / `a093c32c` | P19 kernel riwayat permintaan + history_build linear | diuji ulang di head `d7548eb8` (baris berikut) |
| `d7548eb8` | PL-1/PL-2 + semua di atas | **Shell 37529318500 success**: job `p19-assembly` 7/7 uji paritas PASS (`f04-demand-history-linear`, `f04-history-build-linear`, `f04-demand-estimate-rounding` 3 kasus tetap + 120 acak vs ceil BigInt, `f05-*`); benchmark CI (runner GitHub, kernel saja): riwayat permintaan 10×28 hr 250,7→64,2 ms, 100×30 hr 18.152→588 ms md5 sama; linear saja 200×60 hr 1,8 dtk, 400×60 hr 3,7 dtk, 1000×100 hr 16,4 dtk (ukuran job latar belakang); assembly 5000 target 172,9 dtk→2,6 dtk byte-identik; report_render 5000 target 13,2 dtk→0,36 dtk byte-identik. Build UX, P18, P21, Supplier Payment Create, Receipt Correction, CodeQL: **success**; **P08 Physical 37529318471 success** (fabric13-successor, attention284, plan39, fabric-physical21, analysis152 — memuat PL-1/PL-2) |
| `dc7ee30c` / `10eb465c` / `8a84faf8` | AP-6, PR-5, IN-4, SL-4, mode P12 `--attendance-write` | Build UX, Shell 37533009559, Receipt Correction 37533009542, P21 37533009650, Supplier Payment Create 37533009627, CodeQL: **success**. **P18** 37533009605: percobaan 1 E13 INCOMPLETE hanya karena `public_schema_unchanged=false` (semua asersi bisnis PASS, jalur tidak diubah), percobaan 2 **success**. **Note Correction**: 37533009678 gagal karena uji baru mengambil snapshot batas *sesudah* membaca nota pada fixture E01 (snapshot menggeser token tinjauan → `CP7_NOTE_REVIEW_CHANGED`); urutan diperbaiki + asersi token eksplisit → **37534119936 success**. **P12** 37533256167: `--roster` dan `--attendance-write` (label "Nilai absensi") **success**; `--payroll-review` Native/HTTP PASS, browser review INCOMPLETE karena masalah lama `.cpay-net` (sama seperti di `2d4f5f38`, tidak dilonggarkan) |

## 7. P19 — kernel riwayat permintaan (bukan temuan rumus, tetapi skala)

`cp7_demand.history` dan `cp7_planning.history_build` kuadratik (salinan jsonb per baris, pindai ulang stok per produk). Ditulis ulang linear, **hasil byte-identik** dengan pendahulu `c1f91041` (uji acak lama-vs-baru termasuk urutan penolakan pertama).
Lokal PG16 (bukan bukti): 100 target × 30 hari 23,8 dtk → 0,64 dtk; 200 × 60 hari 320 dtk → 2,3–3,0 dtk (md5 sama); batas 1000 × 100 hari 20,7 dtk dan 39 MB → tetap ukuran pekerjaan latar belakang, bukan layar <1 dtk. Batas (1000 target, grid 100.000) **tidak** dinaikkan.
