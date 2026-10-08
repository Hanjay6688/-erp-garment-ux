# Kandidat audit lanjutan CP7 — 8 Okt 2026

Kelanjutan sesudah pembekuan (`../../CONTINUATION_AFTER_FREEZE_20261008.md`) dikunci di sini untuk satu kali audit.
Kandidat beku `../final-20261008/` (`9d57b7f5` = `cp7/integration`) **tidak diubah**: tidak ada push ke
`cp7/integration`, `main`, deployment, atau Supabase hosted.

## Identitas kandidat

- **Commit sumber kandidat: `976f4c43096ba4ac34569a4bb9d27582cac40d3c`** di cabang `claude/new-session-deapao`.
- Basis: kandidat beku `9d57b7f576eaf4a3535c70003c3d67fdc4c8fcff`. Selisih per berkas (status, ukuran, SHA-256 sebelum
  dan sesudah): `SOURCE_DELTA.json` — 123 berkas (79 baru, 44 berubah; 93 bukan dokumen), tanpa berkas dihapus.
- Commit dokumentasi sesudah `976f4c43` tidak mengubah sumber dan tidak otomatis menerima kualifikasi CI dari `976f4c43`.

## CI pada satu commit (`CI_RECEIPT.json`)

Ke-15 workflow kualifikasi cabang Claude (set yang sama dengan kualifikasi kandidat beku) dijalankan pada `976f4c43`:
yang terpicu oleh push berjalan sendiri, sisanya dijalankan manual (`workflow_dispatch`) di cabang yang sama tanpa
commit baru. Hasil: **15/15 workflow dan 42/42 job sukses**; tidak ada yang gagal, dibatalkan, atau dilewati.
Workflow lama integrasi (`cp7-*.yml`, termasuk keluarga F03) hanya terpicu di `cp7/integration` dan **tidak**
dijalankan untuk kandidat ini, karena cabang itu tidak boleh diubah.

Suite baru di workflow `CP7 P19 Analysis Job Transport` (Native, balapan dua sesi, HTTP Auth nyata, browser desktop+HP):

| Suite | Kasus | Isi |
|---|---|---|
| `p19-plan-v2-18` | 18 | Rencana produksi v2 dari analisis bertahap; draf dari snapshot berlabel waktu, pengesahan memeriksa ulang data live dalam satu transaksi |
| `p19-report-v2-20` | 20 | Business Report v2; angka aktual dan keuangan dari sumber resmi per tanggal laporan |
| `p19-reminder-v2-16` | 16 | Pengingat v2; diperiksa ulang sebelum klaim dan sebelum selesai, yang sudah beres tidak ditagih |
| `p19-ai-v2-9` | 9 | Tanya AI v2; ringkasan berbatas dengan label waktu, tanpa keuangan, tanpa menulis |
| `pl5-history-yield-20` | 20 | PL-5 B yield histori: kebijakan berversi, Wilson satu sisi 90%, produk+ukuran lalu model yang sama |
| `k2-retention-10` | 10 | Hasil analisis sementara disimpan 7 hari sesudah selesai, lalu berlabel kedaluwarsa |
| `p19-staged12`, `p19-transport11`, `p19-scale5` | — | Suite lama P19 tetap hijau; `p19-scale5` juga mengukur ukuran simpan (K3) |

## Kegagalan pertama yang disimpan (tidak diedit)

Semua di `../../evidence/`: `plan-v2-20261008/01..04`, `report-v2-20261008/01`, `ai-v2-20261008/01`,
`reminder-v2-20261008/01..02`, `pl5-history-yield-20261008/01`, `snapshot-v2-20261008/01..03`.
Hampir semuanya cacat skrip uji. **Satu cacat produk** ditemukan CI dan diperbaiki di `976f4c43`: layar pengingat v2
membandingkan gema query dari server sebagai teks; jsonb mengubah urutan kunci, jadi setiap halaman ditolak dan
daftar tidak tampil (`reminder-v2-20261008/02`). Catatan run pertama yang menyebutnya "balapan skrip" keliru dan
dikoreksi oleh catatan kedua. Tidak ada oracle atau guard lama yang dilonggarkan.

## Ukuran simpan (K3, hanya pengukuran)

Diukur di CI (`p19-scale5` job 113438908297 pada `976f4c43`, 100 target, `pg_column_size` sesudah kompresi TOAST): halaman 167.258 B, header 9.415 B,
acuan sumber 130.553 B, indeks rencana 262.336 B, data antara (intermediate) 1.967.521 B — total ±2,5 MB, ±78% data
antara. Teks halaman 5.000 target 206.443.568 B sebelum kompresi (26 halaman); dengan rasio kompresi yang sama
perkiraan satu run 5.000 target ±125 MB, ±100 MB di antaranya data antara. Angka 5.000 ini **perkiraan**, bukan ukuran.
Data antara **tidak** dihapus otomatis saat run selesai (uji lama membaca data antara sesudah selesai); data antara
dihapus oleh pembersih 7 hari K2, yang belum terjadwal (penjadwal server = CP7C).

## Pilihan bawaan yang dipakai (bukan keputusan baru owner)

- Pengingat v2: pengingat kain ditahan bila bahan berubah sesudah analisis; pengingat produksi memakai kebutuhan yang
  sudah berkurang; kebijakan dan tujuan memakai tabel yang sama dengan v1; klaim v2 tidak terlihat oleh v1 (batas
  tercatat); pengiriman tetap pratinjau lokal.
- PL-5 B: formulir terisi paket owner 8 Okt; kebijakan baru berlaku sesudah pemilik/admin menyimpannya di aplikasi;
  tingkat keyakinan, metode dan urutan tingkat tetap.
- K2: fungsi pembersih ada tetapi tidak berjalan terjadwal.

## Belum selesai / di luar kandidat

- CP7C: penjadwal server, hapus otomatis terjadwal, backup malam.
- Hapus data antara segera sesudah run selesai (lihat K3).
- Audit independen P20 atas kandidat ini; `independent_acceptance=false`, `installed_P21_acceptance=false`,
  `production_go=false`. Hosted Enteng dan ERP lama tidak disentuh.
