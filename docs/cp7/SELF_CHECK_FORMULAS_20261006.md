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
| IN-1 | Model hasil potong | Fold latih ikut batch sebelum aturan dicatat (6 batch bukan 3) | Kernel hanya menerima record batch prospektif terpilih | `cutting-model-producer.test.ts` (6≠3) | `3d4cfbea` |
| IN-2 | Model hasil potong | Batch sesudahnya yang tercatat di dalam fold terakhir masuk holdout (4 bukan 3) | idem | idem (4≠3) | `3d4cfbea` |

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
| SL-4 | Koreksi nota menyalin nilai refund retur lama apa adanya setelah harga berubah (harga naik → piutang lebih 25; harga turun → koreksi ditolak) | Tampilkan & minta peninjauan refund pengganti di form koreksi, atau hitung ulang proporsional bila refund lama = porsi neto per pcs |
| SL-5 | Beberapa pembaca uang mengeluarkan `::text` tanpa `round(…,2)` | Moot bila kolom `numeric(…,2)`; seragamkan bila skala kolom berbeda |
| AP-5 | Pengingat hutang memakai jatuh tempo invoice paling awal walau sudah lunas | Pakai jatuh tempo invoice pertama yang belum tertutup pembayaran (FIFO) atau nyatakan aturan |
| AP-6 | Input "16.000" dibaca 16 (harga) | Tolak pola ribuan ambigu di field harga (seperti tarif harian) |
| AP-7 | Total koreksi dibulatkan sekali vs AP Native per baris | Pastikan skala `net_amount` Native; bila 2 desimal, jumlahkan per baris |
| PR-5 | "Perkiraan upah" absensi ≠ upah payroll (ikut PIECE/NONE) | Ganti label menjadi nilai absensi, atau hitung hanya DAILY/HYBRID |
| PR-6 | Payroll APPROVED dengan net minus menyembunyikan detail | Edge legacy; terima net < 0 sebagai tidak dapat dibayar |
| IN-4 | Basis label buku FG v2 "movement snapshot" padahal HPP lot terkini | Ganti nama basis & label "HPP lot saat ini" |
| FIN-4 | Pembanding default bukan bulan kalender sebelumnya | Default ke rentang bulan sebelumnya bila periode mulai tanggal 1 |

## 5. Uji & CI

- Lokal (bukan bukti): DOM/unit yang disebut di atas, `cutting-model-producer.test.ts` (2 uji baru gagal di kode lama, lulus sesudahnya), typecheck.
- CI cabang Claude: `17ce3f76` — Build UX, Shell, P13 Finance (Claude), Receipt Correction, P18, P21, Supplier Payment Create: **success**.
- `2d4f5f38` / `3d4cfbea`: P12 Payroll (roster, payroll-review), Supplier Payment Correction, Note Correction, Receipt Correction, Shell — lihat §6 (diisi saat run selesai).

## 6. Hasil CI per commit

(diisi saat run selesai)
