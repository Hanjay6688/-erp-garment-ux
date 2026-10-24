# Kandidat gabungan ERP — 24 Oktober 2026

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.

Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

Kandidat ini menggabungkan susunan A/B yang telah diperbaiki untuk isolasi draf
retur, pembacaan produk pembanding, dan konfirmasi pilihan pembanding. Bukti
penulis tetap terpisah dari penerimaan auditor. `production_go=false`; status
formal induk tetap 5/16. Cabang resmi, database hosted, dan pengiriman WA nyata
tidak berubah.

## Kode yang dipasang

Entrypoint: `scripts/cp7_current_analog_installation.py`, kontrak
`cp7.current-AB-return-with-analog-metadata.v1`. Verifier pendahulu dijalankan
sebelum setiap delta; seluruh 22 kelompok katalog diperiksa. Penambahan analog
berupa dua tabel dan tiga RPC publik; tahap analog ini tidak mengganti fungsi
lama dan tidak menerapkan perkiraan permintaan ke target produksi.

Penggabungan memakai dua merge dengan dua induk, tanpa rebase atau force:

- `47eaf367`: cabang bukti A `d30bfb4a` + UI teruji `09a95b1d`.
- `8bc670ba`: hasil tersebut + kualifikasi Auth `4b7e037e`.

Seluruh sumber aplikasi, konfigurasi build, dan registry sama persis dengan
kandidat UI yang benar-benar diuji. Selisih dari kandidat UI hanya penambahan
berkas kualifikasi, workflow, dan bukti. Modul konsumen/perhitungan B yang lebih
baru belum dipasang oleh entrypoint ini.

## Bukti asli yang tersedia

| Bukti | Kandidat | Hasil yang benar-benar diamati |
|---|---|---|
| Pemulihan analog lengkap | `469ed1e8` | 8 tahap, 7 kontrol penolakan, 5 syarat paket lulus; pemulihan penuh sesudah pemakaian, kemudian retur berikutnya tetap READY |
| Browser gabungan | `09a95b1d` | 6 alur lulus pada 3 salinan penuh; Auth, sesi, database uji, dan console bersih |
| Auth gabungan | `4b7e037e` | 2 alur Grade A/B lulus; penolakan akses, replay, perubahan uang/stok/HPP, serta inverse resmi tepat |
| Transaksi kerja/payroll pertama | `997ffe2a` | 12 PASS + 1 INCOMPLETE pada baseline dan current; 26 eksekusi seluruhnya tercatat |
| Skenario anak 9 pcs | `d7338a92` | Satu baseline dan satu current PASS; tepat 9 × 1,25 = 11,25, laporan READY, 5 syarat paket lulus |

Rincian run, job, artifact, ukuran byte, SHA256, dan syarat paket ada pada JSON
bukti di direktori ini. Laporan asli pertama yang gagal tetap INCOMPLETE.
Jumlah lintasan uji bukan jumlah fitur baru atau penerimaan seluruh scope.

Kegagalan payroll pertama berasal dari prasyarat baru yang hanya mengizinkan
4/6/10 pcs, sedangkan operasi anak asli memang menulis 9 pcs. Pengganti menerima
tepat 9 pcs dengan tarif asli 1,25 dan kewajiban 11,25. Seluruh oracle lock,
commit/abort, lineage kerja, dan READY lama dipertahankan. Dua belas skenario
lain tidak diulang hanya untuk memperoleh angka hijau.

## Batas sumber dan pemulihan

SOURCE historis tidak diubah agar cocok dengan UI baru. Seluruh 1.264 pin UI6
sesuai kandidat gabungan. Deklarasi Native/Auth berbeda pada empat berkas UI
dan registry yang telah dikualifikasi; deklarasi race juga berbeda pada CSS
yang sama-sama telah diuji. Perbedaan dicatat eksplisit, bukan dinormalisasi.
Menjalankan gate historis langsung pada root gabungan bukan pengganti checkout
sumber historis yang tepat.

Inverse sebelum pemakaian memeriksa seluruh baris dan seluruh sequence sebelum
DDL pertama. Sesudah pemakaian wajib memakai pemulihan backup penuh; pengujian
tidak mereset sequence. Draf tetap bukan sumber pengakuan keuangan. Riwayat
POSTED dibatalkan melalui inverse bernama. Izin terkini diperiksa lagi setelah
menunggu lock maupun saat replay. UNKNOWN tetap dibedakan dari nol.

Pemeriksaan merge: 158 uji klien pada 6 berkas, TypeScript, sumber, akses, dan
CSS lulus. Ini pemeriksaan penulis, bukan audit independen atau pengulangan
seluruh kualifikasi database pada commit merge.

## Pekerjaan berikut dan batas keputusan

Teruskan pekerjaan setelah checkpoint. Bukti asli child9 sudah terikat
bersama bukti lain pada kandidat ini. Lanjutkan integrasi B yang sudah
memenuhi bukti komponennya, berikut pemeriksaan efek keuangan, stok, HPP, dan
pemulihan pada susunan penuh.

Consumer B `587586ee` mempunyai Native6 dan browser2 PASS secara terpisah.
Provenance Native3 pada sumber tersebut masih 2 PASS + 1 INCOMPLETE karena
fixture mencoba menonaktifkan owner terakhir. Pengaman last-owner harus tetap
berlaku. Transport consumer, pemulihan setelah pemakaian pada susunan A penuh,
uji model terhadap riwayat, dan penerimaan OW11 lengkap tidak disimpulkan dari
bukti komponen tersebut.

Keputusan owner yang belum ditutup tetap terbuka: kelebihan bayar laundry/
piutang vendor, OW04b D/E untuk kredit yang sudah digunakan, absen tanpa sewing,
dan batas umur koreksi HPP. Nilainya tidak dikarang. Skala pabrik sekitar 3.600
barang dan batas kualifikasi historis yang masih terbuka juga tidak dinyatakan
selesai oleh paket ini.

Catatan publik hanya memuat metadata kualifikasi dan konstanta fixture sintetis.
Baris mentah serta rincian posisi keuangan disimpan pada laporan asli.
