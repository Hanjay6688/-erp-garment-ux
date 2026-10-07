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
Kualifikasi belum diterima sebelum seluruh hasil dan Original dibaca.
P20/P21 §14 mencatat
objek, prioritas auditor, pemasangan dan rollback; bukan acceptance independen.

Arahan owner 8 Okt 02:09 WIB: **3 detik sasaran optimasi, bukan gerbang wajib**.
Catat waktu aktual. Pisahkan waktu hitung job, capture, acknowledgement,
klik halaman sampai data terverifikasi+dua paint frame, dan buka hasil DONE.
Jangan menganggap acknowledgement sebagai hasil analisis sudah termuat.
Pengukuran loopback Chromium/disposable Native bukan SLA pabrik/hosted.

## 4. Batas kelanjutan

Setelah CI selesai: simpan receipt/bukti source yang tepat, catat kinerja
sebelum/sesudah, lengkapi SELF_CHECK §6 dan P20/P21 dengan status terpisah
fitur/batas terbuka/penerimaan auditor. Bekukan kandidat yang benar-benar
lulus untuk pemeriksaan independen. Penggabungan integration dan audit
independen belum dilakukan dalam checkpoint ini.

Tidak mengirim pesan ke orang lain, meminta kredensial atau mengubah hosted/
main/deployment/produksi. Tidak melonggarkan rumus, oracle angka, hak,
kelengkapan, hash atau batas 8 detik agar CI hijau. `independent_acceptance`
dan `production_go` tetap false.
