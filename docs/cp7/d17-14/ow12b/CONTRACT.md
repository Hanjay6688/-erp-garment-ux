# OW12b — pemakai modul keuangan resmi A

23 Oktober2026 WIB. Kontrak pemakai B, sebelum perubahan caller. Modul dasar A tetap milik A:
`cp7.finance-capture.v1`, cabang A b91a60b, `ow12/KONTRAK_OW12A.md`. Tahap ini harus berada di atas
OW12a A dan tahap produksi B; tidak mengubah SQL dasar beku, angka laporan, finance_apply, background runner A,
atau header operasional yang sudah disegel.

Permintaan bertahap menambah `p_query.finance_mode: STAGED|DEFERRED` (absen = DEFERRED untuk klien lama).
Tanggal/group_mode tetap query operasional tiga kolom yang sama. Pilihan dicatat di reference job yang immutable;
UUID sama dengan pilihan berbeda ditolak. STAGED memanggil A.start dengan job_id, query dan jam capture asli.
Operasional selesai tanpa menunggu laporan; A menjalankan keluarga FINANCE pada server.

Status job tetap endpoint yang sama; hanya job STAGED menambah `finance_capture` dengan kontrak
`cp7.analysis-finance-sidecar.v1`: request_id, job_id, query, reference, state, capture dan result.
Header status memuat id capture A. Header/dokumen operasional tersegel tetap tidak berisi angka keuangan;
hasil keuangan terpisah melalui id job/capture, sehingga hash halaman operasional tidak berubah sesudah terbit.
Ini penempatan metadata pemakai B atas ketentuan header/id pada kontrak A, dicatat untuk penggabung.

Hak operasional dan actor job diperiksa dahulu. Sebelum membaca status A, periksa OWNER/ADMIN serta
finance.reports.view melalui report_finance_access; status_of A bersifat privat dan mengandalkan penjagaan caller.
Hak dicabut menyembunyikan metadata/angka keuangan (ACCESS_REVOKED); perubahan akses selama baca menolak jawaban.
READY memanggil A.result lalu fungsi finance_apply yang sama dengan analisis/laporan; tidak ada rumus uang baru.
Query, tanggal Jakarta, pemilik job, id capture dan hash sumber harus cocok. RUNNING/FAILED tidak memuat angka.

Klien menyimpan finance_mode bersama UUID sebelum kirim dan sesudah operasional selesai, agar pemulihan tetap
mengacu ke pilihan yang sama. Status uang dipantau terpisah dengan endpoint status job, tanpa mengambil seluruh
header/halaman ulang. Angka hanya ditampilkan ketika hasil laporan READY dan hak saat ini masih ada; HPP/laba yang
belum lengkap tetap menunggu, bukan nol. Jam operasional dan jam laporan resmi dibaca ditampilkan masing-masing.

Belum kualifikasi Native: A menguasai komposisi ujung rantai dan module OW12a belum tersedia pada branch B.
Adapter uji lokal tidak boleh dipakai sebagai bukti laporan Enteng atau ±3.600 barang. OW12b tetap terbuka sampai
sambungan nyata, angka identik dan ukuran waktu sebelum/sesudah terbukti.
