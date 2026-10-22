# OW-05b — petunjuk layar koreksi mandor, langkah lengkap, riwayat terlihat

Dibuka kembali dari uji ulang A1 (`docs/cp7/d17-14/UJI_ULANG_CLAUDE.md`, bagian OW-05). Empat catatan:

| No | Catatan uji ulang | Yang dibuat |
|---|---|---|
| 1 | Nama layar di petunjuk tidak sama dengan menu ("layar Nota/Gaji", "WIP & Jahit", "layar PO", "layar Bahan Mandor") | Setiap jenis penghalang (19 jenis) diberi teks yang menyebut menu sidebar asli dan nama tombolnya, mis. "Keuangan › Payroll & Kasbon (tombol Batalkan payroll)". Bila tidak ada layar yang bisa membalik dokumen itu, teks berkata begitu terus terang. |
| 2 | Petunjuk sesudah koreksi hanya menyebut jahit dan nota | Daftar 9 langkah urut: WIP & Sewing, Nota Ambil Aksesori, Laundry, QC & Final SKU, Barang BS & Rework, Penjualan, Kain kantong, HPP & Rekalkulasi, Payroll & Kasbon. Ditampilkan sebelum koreksi dan disebut lagi di pesan hasil. |
| 3 | Riwayat koreksi tersimpan tetapi tidak terlihat | Panel menampilkan riwayat PO: waktu (WIB), mandor lama → mandor baru, jumlah pembagian diganti, oleh siapa, alasan; terbaru di atas. |
| 4 | Penghalang tanpa tautan ke dokumennya | Penghalang yang dokumennya bisa dibuka pembaca sumber transaksi yang sudah ada diberi tombol "Buka <nomor>": nota/gaji, QC, lot barang jadi (lewat QC asal), laundry, rework, nota ambil aksesori, draft pembagian. |

## Cara kerja

Tahap server baru `scripts/cp7_contractor_guidance/` di atas produk OW-05 yang sudah lulus, pola sama dengan OW-07/OW-08a:

- `cp7_contractor_correction.blockers_v1` diubah di satu tempat (dihitung tepat satu kali): setiap baris lewat `guide_v1`, yang hanya mengganti teks `step` dan menambah `menu` dan `source`. Urutan, id, status dan jumlah baris tidak berubah. Jenis penghalang yang tidak dikenal ditolak (`CP7_MANDOR_GUIDANCE_KIND_UNKNOWN`) supaya jenis baru tidak lolos tanpa petunjuk.
- `workspace_v1` diubah di satu tempat: `after_step` baru, ditambah `after_steps` dan `history`.
- Perintah koreksi, aturan token tinjauan, tabel riwayat dan semua penulis bisnis tidak diubah. Pembaca baru privat (tidak bisa dipanggil langsung oleh pengguna).
- Layar: `src/mandorCorrectionContract.ts` membaca field baru secara ketat; `src/MandorCorrectionPanel.tsx` menampilkan menu, tombol Buka (memakai `TransactionSourceLink` yang sudah ada), daftar langkah dan riwayat. Teks hasil tidak lagi menyebut "WIP & Jahit".

## Jenis yang belum punya layar pembalik (dikatakan terus terang di petunjuk)

- PO berstatus Ditahan/Dibatalkan (tidak ada tombol ubah status di aplikasi).
- Kasus BS manual (BS dari QC ikut batal saat QC dibatalkan; yang manual tidak punya tombol batal).
- Dokumen scrap lama (tidak ada penulis scrap di aplikasi sekarang).
- Hasil kerja/upah yang tidak berasal dari catatan selesai jahit (mis. data impor).
- Nota pengambilan berisi kain/bahan selain aksesori PCS (layar Nota Ambil Aksesori hanya untuk aksesori PCS).

Untuk PO seperti ini koreksi mandor tetap terkunci; petunjuknya tidak menyuruh membuka layar yang tidak ada.

## Uji

- Server, 6 kasus (`cp7-ow05b-native.yml`): rantai nyata jahit→laundry→QC→barang jadi→PO selesai dibandingkan berdampingan dengan pembaca OW-05 asli (baris sama, hanya teks/menu/tautan bertambah; tautan QC, laundry, lot benar-benar terbuka lewat pembaca sumber); semua 19 jenis dan cabangnya; 9 langkah sesudah koreksi; riwayat dua kali koreksi (urut terbaru, nama, alasan, pelaku; PO lain kosong; terlihat walau masih terkunci); perintah koreksi tidak berubah; pembaca privat ditolak untuk pengguna. Menu di semua teks dicocokkan dengan menu di `src/App.tsx`.
- Cabang yang belum dijalankan dengan data nyata: nota pengambilan kain/bahan (hanya diperiksa di database lokal sekali pakai dengan tabel tiruan).
- Layar unit: 16 kasus vitest (`src/MandorCorrectionPanel.dom.test.tsx`), termasuk tombol Buka yang memanggil pembaca sumber dan pindah ke Payroll & Kasbon, riwayat, dan penolakan data yang tidak sah.
- Browser nyata, desktop dan HP 390 (`cp7-ow05b-browser.yml`): dari penghalang klik "Buka <nota>", batalkan nota di Payroll & Kasbon, kembali ke WIP & Sewing, batalkan jahit, koreksi, lihat riwayat, catat ulang jahit. Uang dicek: mandor lama 0, mandor baru 24, WIP +24.

## Status

| Uji | Kepala | Run/job | Hasil |
|---|---|---|---|
| Browser nyata desktop + HP 390 | `eda58db5` | 39831356490 / 120008037841 | **2/2 PASS**. Artefak `cp7-ow05b-real-browser2`, 1.995.500 byte, sha256 `850f7acff4d6cd644efb4329cfc01aa777203ff2a21e52804b911c269b7a0e10` |
| Browser, percobaan pertama | `b7c20b98` | 39827224321 | Berhenti di langkah menyalakan database uji (masalah server CI, sebelum kode diuji) |
| Native6 | `3093e2d3` | 39826573395 | Percobaan 1–2 berhenti di langkah menyalakan database uji; percobaan 3 sedang berjalan |

OW-05b belum dinyatakan selesai sebelum Native6 lulus. Bukti uji browser OW-05 lama (`browser2-*`) tetap sebagai riwayat;
layar yang sekarang diuji oleh alur OW-05b.
