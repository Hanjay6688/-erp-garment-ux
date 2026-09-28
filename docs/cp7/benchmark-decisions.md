# Benchmark CP7 — dibaca 28 September 2026

Owner meminta benchmark pakar untuk hal yang belum dipastikan. Referensi ini
menjadi dasar pilihan metode dan skenario uji, bukan pengganti fakta CP6 atau
otorisasi parameter bisnis. Enam kartu sumber juga tampil di pratinjau.

| Area | Keputusan teknis awal | Batas yang tetap terbuka |
|---|---|---|
| Forecast | Bandingkan model dengan mean/naive; metode sederhana tetap kandidat sah [1] | Belum memilih pemenang tanpa histori |
| Evaluasi | Rolling origin dan horizon relevan; future-known rows tidak masuk training [2] | Eligibility/fold aktual di P05–P07 |
| Safety stock | Sediakan kelak perbandingan **CSL** 90/95/99% sebagai skenario uji dari latihan MIT [3] | Bukan angka standar garment; bukan fill rate; tidak aktif otomatis |
| Input buffer | Error ramalan, lead time, service target, metode harus eksplisit [4] | Nilai per vendor/tahap/ukuran perlu data; jangan menyamakan model SAP dengan jaminan kapasitas CP7 |
| Intermittent | Croston/varian dievaluasi, jangan mengklaim interval/confidence tanpa model sah [5] | Stockout/missing bukan observasi nol; no-leakage tetap |
| WA | Status antre/sent/delivered/read terpisah [6] | Dokumentasi provider sebagai pembanding, bukan pemilihan provider |

**Inferensi untuk CP7:** parameter contoh boleh dipakai untuk membandingkan
skenario dan membangun input UI. Tidak ada benchmark yang membuktikan accepted
CP6, hak pengguna, waktu laundry Hansen, kapasitas mandor, tarif, pembagian size,
tanggal jatuh tempo, atau saldo hutang/piutang. Field itu tetap unknown sampai
sumbernya tersedia. Prioritas owner tetap dipertahankan; tidak diganti aturan
penjadwalan generik yang mengasumsikan satu mesin dan pekerjaan tanpa kendala.

Belum ada algoritme forecast/safety-stock statistik ditambahkan pada S0.
Mesin produksi tetap mengikuti ADR backend dalam framework. Kontrak DAYS
versus STATISTICAL dipertahankan dan tidak menumpuk dua buffer. Pemilihan
numerik final memerlukan hasil backtest/risiko/modal dan keputusan setup usaha.

1. Hyndman & Athanasopoulos, FPP3 §5.2: https://otexts.com/fpp3/simple-methods.html
2. FPP3 §5.10: https://otexts.com/fpp3/tscv.html
3. Chris Caplice, MIT ESD.260, Inventory Management: Probabilistic Demand,
   slide 13/18/20 (2006): https://ocw.mit.edu/courses/esd-260j-logistics-systems-fall-2006/resources/lect11/
4. SAP Extended Safety Stock Planning (konsep, dokumentasi versi historis):
   https://help.sap.com/saphelp_snc70/helpdata/en/62/96cb530898214be10000000a174cb4/content.htm
5. FPP3 §13.2: https://otexts.com/fpp3/counts.html
6. Twilio Track Outbound Message Status:
   https://www.twilio.com/docs/messaging/guides/track-outbound-message-status

Tidak ada sumber blog SEO/angka industri tanpa konteks yang dipakai untuk
menetapkan parameter usaha. Rujukan di atas dibaca sebagai sumber primer
penulis/pengajar/penerbit produk; usia bahan ajar tidak menjadi klaim data
pasar terbaru.

## Delta riset: belajar pola dan memilih metode

Permintaan owner berikutnya mencakup praktik perusahaan besar/kecil, pola
usaha sendiri, alasan pemilihan SKU/jumlah, dan pemicu backend. Rekomendasi:
model belajar dari fakta eligible, dibandingkan pada data uji kronologis,
lalu hasilnya melewati netting, timeline, bahan dan kapasitas yang eksplisit.
Statistik dan machine learning sama-sama dapat belajar pola; tidak ada
jaminan model paling rumit paling akurat pada data Hansen.

Kandidat awal tetap baseline mean/naive/moving mean, SES, damped/seasonal bila
eligible, serta SBA/TSB untuk intermittent. Global LightGBM layak menjadi
challenger setelah dataset siap. DeepAR bukan persyaratan awal. Satu tahun
histori tidak membuktikan musim tahunan berulang; stockout/missing tidak
diubah menjadi nol permintaan. SKU baru memerlukan analog beralasan/skenario.

| Bukti primer tambahan | Hal yang didukung | Batas |
|---|---|---|
| Amazon Science, SCOT (2022) | Forecast ML + optimasi/simulasi | Bukan akurasi untuk Hansen |
| Studi Zara, implementasi 2006/publikasi 2010 | Alokasi inventori toko dengan kendala ukuran | Bukan formula produksi atau klaim algoritme Zara sekarang |
| Fast Retailing, Ariake (2024) | Algoritme permintaan dan penyesuaian produksi mingguan | Formula spesifik tidak dibuka |
| Katana, Buttercream Clothing | Perencanaan produksi dan inventori kain pada usaha kecil | Studi vendor, bukan audit independen atau bukti forecast ML |
| M5, preprint 2020/publikasi 2022 | Solusi berbasis LightGBM kuat pada kompetisi data retail | Tidak membuktikan Walmart mengoperasikan solusi pemenang |

- https://www.amazon.science/latest-news/solving-some-of-the-largest-most-complex-operations-problems
- https://web.mit.edu/jgallien/www/ZaraInterfacesPaperDraftFeb23.pdf
- https://www.fastretailing.com/eng/sustainability/news/2411131510.html
- https://katanamrp.com/wp-content/uploads/2021/06/buttercream-clothing.pdf
- https://statmodeling.stat.columbia.edu/wp-content/uploads/2021/10/M5_accuracy_competition.pdf

Ini shortlist untuk evaluasi, bukan aktivasi estimator. Prototipe pemicu dan
batas CP7/CP7C ada di [automation-seam.md](automation-seam.md). Laporan riset
owner `CP7_Riset_Metode_dan_Pola_Data_20260928.md` memuat perbandingan rumus,
asumsi, sumber primer, kebutuhan data, evaluasi, dan rancangan penjelasan.
