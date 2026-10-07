# Takeover writer ERP Garment — GPT, 8 Okt 2026

GPT mengambil mandat writer dari checkpoint Claude `7927b42c`, atas instruksi
owner di chat. Cabang produk tetap `claude/new-session-deapao`; satu writer.
Catatan lama yang menyatakan hanya Claude menulis adalah status historis.
Tidak ada perubahan main, Cloudflare, hosted Enteng, legacy atau produksi.

## 1. Urutan otoritas dan konteks seluruh ERP

Instruksi/keputusan owner di atas addendum yang disahkan, kemudian framework.
Kode dan hasil CI adalah bukti implementasi, bukan pengganti kontrak. Prinsip
utama: reliable data; keuangan/laporan, stok dan HPP; UNKNOWN bukan nol.

| Area ERP | Aturan yang tetap berlaku |
|---|---|
| Akses dan pemulihan | PostgreSQL otoritas, hak diperiksa kembali setelah kunci; UUID disimpan sebelum tulis, UNKNOWN/VERIFYING memagari lintas tab/rute, satu transaksi untuk koreksi dan pembalikan. |
| Keuangan | Decimal eksak; laba = pendapatan − HPP − beban; neraca/jurnal seimbang; laporan baca-saja dan angka yang belum lengkap tetap UNKNOWN. |
| Pembelian/AP | Penerimaan menimbulkan GRNI perkiraan; invoice final mengoreksi biaya/AP pada tanggal ekonomi; invoice terlambat tetap sah; pembayaran/retur/kredit tidak terhitung dua kali. |
| Penjualan/AR | Draf mencadangkan sekali; posting tidak mencadangkan lagi; retur parsial mempertahankan lot/HPP dan alokasi kredit; koreksi harga baris yang sudah diretur memerlukan pembetulan retur terlebih dahulu. |
| Stok/HPP/produksi | Root fisik dan versi ukuran terpisah dari SKU komersial; seluruh mutasi PCS/biaya terkonservasi; koreksi biaya merambat kronologis; PAUSED/STOPPED menahan produksi, bukan penjualan FG yang tersedia. |
| Payroll | Kode pekerja tetap; upah berasal dari payroll, nilai absensi diberi label tersendiri; BS/pekerjaan belum selesai/kompensasi dan saldo negatif mengikuti kontrak, aturan Afui tidak dikarang. |
| Model/perencanaan | Data as-known tidak bocor melewati cutoff; fallback baseline eksplisit; netting/yield/jadwal/kebutuhan kain dan aksesori memakai fakta/asumsi yang ditinjau, tidak menyulap UNKNOWN menjadi 0. |
| UI | 48 rute dan 111 izin tetap dimiliki katalog; mode demo/terhubung jelas, dependensi/koreksi/pembalikan terlihat; hak backend tidak diganti dengan menyembunyikan tombol. |
| Waktu | Tanggal fisik, ekonomi, diketahui dan pengakuan dipisahkan; tanggal bisnis WIB; tidak ada larangan backdate umum yang menggantikan aturan Native. |

Rujukan: `docs/AUDIT_PANDUAN_PRO_MAX.md`,
`docs/cp7/framework-v2/00_MULAI_DI_SINI.md`, `01_KONTRAK_DAN_INTEGRASI.md`,
`02_BACKBONE_TEKNIS.md`, `04_BUKTI_DAN_ORACLE.md`,
`06_RUSUK_KEBUTUHAN_OWNER.md`, `docs/cp6-d11-kebijakan-dan-gbd03.md`, dan
`docs/cp7/acceptance/HANDOFF.md`. CP6 diterima independen menurut cakupannya;
HOLD operasional/pemasangan dan `production_go=false` tetap terpisah.

GBD-03 opsi 1 dan lima keputusan D11 sudah disahkan; jangan dibuka ulang.
Delapan konfigurasi CP6 nyata, PL-5 B, retensi staged, driver server,
prioritas fitur downstream staged dan runner PL-8 tetap keputusan owner.

Master induk `ERP_GARMENT_MASTER_CONTEXT_2026-09-06.md` sudah dibaca lengkap
(1.138 baris), berikut dua master pemulihan 23 Sep yang dirujuk framework.
Konteksnya mencakup CP1/backup, CP3 attendance-HPP, CP4/Auth, CP4.5/identitas,
CP5/potong-pickup-BS, CP6/seluruh physical-financial lifecycle, lalu CP7,
cleanup CP7.5, operasi CP7C dan audit/cutover CP8. Status kandidat September
di bagian awal master adalah historis; CP6 CLOSED menurut receipt 29 Sep,
HOLD operasional/konfigurasi dan production GO tetap terpisah.

Detail utama yang ikut dibawa: HPP absensi diakui APPROVED sekali dan PAID
hanya settlement; denominator selesai dijahit; FG parsial tetap menyisakan
biaya WIP; Susulan tidak masuk QC kedua kali; Rework/rewash tidak membuka
entitlement lama; PO/invoice/retur/kredit serta biaya late invoice menjaga
lineage dan tanggal. Versi lama WIP exact-SKU-only telah diperluas CP7 rev3
menjadi kandidat bersyarat, tanpa mengubahnya menjadi FG pasti.

Paket source review `audit-candidate/staged-5000-20261008/README.md` memuat
manifest 2.098 berkas, hash kompilasi F03/full-staged, acuan seluruh ERP dan
batas P21 yang sebenarnya. Tidak ada klaim bahwa seluruh chat historis
dari semua akun telah diperoleh.

## 2. Produk yang dilanjutkan

Seluruh lima patch integrator, patch SQL P dan patch frontend F dipasang
bersama sesuai checkpoint. Prototipe yang tidak dipakai dihapus dari kode
aktif; sumbernya tetap ada dalam Git/patch checkpoint. Kontrak produk ada di
`docs/cp7/p19/P19_STAGED_5000_20261007.md` §10.

- Enam RPC staged v1, sepuluh tabel privat/RLS/immutable, satu acuan MVCC,
  unit nyata history/baseline/supply/schedule/netting/fabric/analysis/pages.
- Batas 5.000 target, 500.000 sel riwayat, 1.000.000 pasangan; setiap unit
  tetap 8 detik. Header/halaman masing-masing maksimal 8.000.000 byte UTF-8.
- Identitas header+hash halaman benar juga pada hasil tanpa halaman. Setiap
  halaman diverifikasi; uji menyusun ulang teks analisis dan Original persis.
- Satu UUID dijaga lintas capture/job/staged. NET_PAIRS tidak dihitung sebagai
  kemajuan target. 5.001 target ditolak eksplisit, tidak dipotong.
- Pause/reload melanjutkan UUID yang sama. Buka hasil DONE hanya GET/header/
  halaman, tanpa hitung ulang. Label produk diindeks sekali per header.
- PAGES/PAGE_INDEX melewati bacaan sumber/scenario/netting/allocation yang
  tidak mereka pakai; badan pembangun halaman tetap persis.

Run staged tidak masuk tabel run biasa. Laporan, pengingat, AI, rincian stok,
workspace kain, draf rencana dan arsip yang membutuhkan satu hasil lengkap
belum tersedia pada staged, sesuai kontrak; halaman tidak diperlakukan
sebagai seluruh hasil. Keuangan staged DEFERRED, bukan nol.

## 3. Bukti kandidat dan latensi

Head pertama `cb98b0f8` belum qualified: kernel/shell/transport lama lulus,
tetapi harness staged/scale dan CodeQL JavaScript gagal. Log/Original/
screenshot pertama disimpan, penyebab dan perbaikannya ada di
`docs/cp7/evidence/gpt-staged-5000-20261008/README.md`.

Kandidat perbaikan `43d26996d767f47bb21d86e988b92c9dcf994703` sudah di-push;
15 workflow dijalankan pada source yang sama, termasuk P12/P13/koreksi nota/
koreksi pembayaran supplier yang dulu terlewat filter. Kernel 5.000×30/100
lulus tanpa retry (123/136 detik proses penuh); staged12 dan transport15
lulus. Uji skala aplikasi masih INCOMPLETE karena dua cacat harness:
pembacaan timeout sebagai batas struktural dan respons browser terhapus dari
cache inspector. Original/gate gagal tetap disimpan. Perekam pasif CDP dan
vonis batas sudah diperbaiki, dengan regresi angka/hash/refusal tetap ketat;
kandidat berikutnya harus lulus seluruh 15 workflow pada satu source.

**Kualifikasi writer selesai di source `59d63e46ea5b109101a4e0a2eff7d27a8f3541f8`,
tree `2ac496cbacca2fe9ed1a924d0ffcc93bdb2b8844`: 15/15 workflow, 35/35 job sukses.**
Receipt `59d63e46-same-source-ci.json` mencatat setiap run/job. Shell dan Build
masing-masing lulus 1.666 uji/191 berkas, suite kernel staged 14 uji dan tiga
vektor, enam SARIF CodeQL tanpa temuan. Native/Auth/HTTP/browser staged 12/12,
transport 15/15 dan tangga aplikasi skala 5/5 lulus. P12 roster/review/absensi
semuanya hijau. Seluruh Original dan kegagalan sebelumnya tetap utuh.

Tangga aplikasi menggunakan sumber yang diisi lewat writer Native, real Auth,
PostgREST dan Chromium. Semua 5.000 target selesai pada 1/30/100 hari, 26
halaman per vektor; semua halaman dibaca dan diperiksa hash/kontrak beku,
cakupan penuh, hak serta pemulihannya. Buka DONE tidak request/step ulang.

| Riwayat 5.000 target | Hitung baru sampai halaman pertama | Buka hasil DONE | Pindah halaman, min–maks |
|---|---:|---:|---:|
| 1 hari | 83,030 dtk | 1,057 dtk | 0,554–0,693 dtk |
| 30 hari | 92,311 dtk | 1,003 dtk | 0,575–0,709 dtk |
| 100 hari | 110,541 dtk | 1,074 dtk | 0,581–0,723 dtk |

Waktu load berasal dari klik asli sampai data terverifikasi dan dua frame
paint. Ada 75 klik halaman lanjutan pada ketiga vektor 5.000. Ini satu
observasi per vektor di lingkungan disposable/loopback, bukan SLA pabrik.
Acknowledgement 5,7–6,5 ms dan progres pertama 5,21–7,26 dtk tetap dicatat
terpisah; keduanya tidak berarti hitungan selesai. Unit SQL terlama di
vektor aplikasi 5.000 adalah 1,410 dtk; batas RPC tetap 8 dtk. Observasi eksak
ada di `59d63e46-full-app-observations.json` dan Original scale5.

Kapasitas tersebut untuk jalur **staged operasional**. Jalur tunggal tetap
memiliki batas lama; fitur downstream staged dan keuangan tetap sesuai §2.
Tiga detail schema laporan lama (model tanpa `restore_components`, label
jadwal 70 meski predicate/ID mewajibkan 71, label P18 Full Cycle 1 meski dua
ID E01/E13 diwajibkan) disimpan dengan receipt khusus, tanpa menulis ulang
Original atau melonggarkan predicate. Ini titik review auditor yang eksplisit.
P20/P21 §14 mencatat
objek, prioritas auditor, pemasangan dan rollback; bukan acceptance independen.

Arahan owner 8 Okt 02:09 WIB: **3 detik sasaran optimasi, bukan gerbang wajib**.
Catat waktu aktual. Pisahkan waktu hitung job, capture, acknowledgement,
klik halaman sampai data terverifikasi+dua paint frame, dan buka hasil DONE.
Jangan menganggap acknowledgement sebagai hasil analisis sudah termuat.
Pengukuran loopback Chromium/disposable Native bukan SLA pabrik/hosted.

## 4. Batas kelanjutan

Source di atas sudah dibekukan sebagai kandidat review writer; dokumentasi
penutupan berikutnya tidak mengubah sumber produk/alat uji yang dikualifikasi.
Paket `audit-candidate/staged-5000-20261008/`, SELF_CHECK §6, kontrak P19 §11
dan P20/P21 §14 memisahkan fitur selesai, batas terbuka dan penerimaan auditor.

Kelanjutan yang belum dilakukan: integrasi terkendali ke `cp7/integration`,
P20 audit independen atas kandidat yang dipin, kemudian P21 untuk komposisi
penuh yang memuat staged serta T2/backup/restore/rollback sesudah pemakaian
sesuai cakupan nyata. P21 hijau saat ini hanya latihan F03, USE ditahan lalu
di-rollback; jangan menganggapnya penerimaan pemasangan seluruh paket.

Tidak mengirim pesan ke orang lain, meminta kredensial atau mengubah hosted/
main/deployment/produksi. Tidak melonggarkan rumus, oracle angka, hak,
kelengkapan, hash atau batas 8 detik agar CI hijau. `independent_acceptance`
dan `production_go` tetap false.
