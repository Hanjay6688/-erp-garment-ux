# AX: tinjauan adversarial independen (23 September 2026)

- **Peninjau:** sub-agent Claude, baca-saja. Tidak ada file yang diubah dan tidak ada koneksi database.
- **Objek:** `scripts/cp6_ax_functions.sql`, `scripts/cp6_ax_build.py`, probe `scripts/cp6_ax_probe.py`, versi sebelum commit perbaikan ini.
- **Dasar pembacaan:** definisi helper diambil dari migration terbaru. Bila migration tidak mendefinisikannya, dipakai katalog bootstrap `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`.
- **Status bukti:** disposisi di bawah dibuat writer (Claude) sesudah temuan diverifikasi ke kode. Label: T1_FAMILY. Ini bukan penerimaan independen dan bukan bukti rilis.

## Temuan dan disposisi

| No | Sev | Temuan (ringkas) | Verifikasi writer | Disposisi |
|---|---|---|---|---|
| 1 | P1 | GOOD dari BS temuan tidak mengurangi pcs yang sedang di rework aktif. Aturan platform: `qty − resolved − qty_sent` untuk rework OPEN/IN_PROGRESS/PARTIAL. | Terbukti: `resolve_bs_case_disposition_v2` dan `validate_rework_quantity_state` memakai rumus itu. `rework_orders` tidak butuh PO. | **Diperbaiki.** Rumus yang sama dipakai. Kasus `AX:REWORK_IN_PROGRESS_NOT_AVAILABLE`. |
| 2 | P1 | Resolusi BS yang ditulis AX bisa dihapus lewat REVERSE_DISPOSITION di layar BS. Case terbuka lagi sementara lot dan jurnal tetap ada, jadi barang yang sama bisa masuk dua kali. | Terbukti: `reverse_bs_disposition_v2` menghapus semua resolusi non-rework. | **Diperbaiki.** Trigger `trg_guard_bs_resolution_fg_unsourced_v1` menolak UPDATE/DELETE resolusi milik penerimaan AX yang masih POSTED. Pembatalan AX mengubah status penerimaan dulu, baru menghapus resolusinya. Kasus `AX:BS_RESOLUTION_OWNED`. |
| 3 | P2 | Urutan kunci terbalik: posting mengunci baris BS lalu advisory lock, sedangkan pembatalan advisory lalu baris BS. Bisa deadlock. | Terbukti dari urutan kode. | **Diperbaiki.** Posting kini mengambil advisory lock `FG_HPP_SALES_V2620C` lebih dulu, sama dengan penjualan, penyesuaian, konversi, dan pembatalan. Bukti STATIC (`AX:LOCK_ORDER_STATIC`) dan race batal-vs-posting pada BS yang sama (`AX_RACE:BS_REVERSE_FIRST/BS_POST_FIRST`). |
| 4 | P1 | Rata-rata "stok yang ada" tidak menghitung barang yang direservasi draft penjualan (`SALE_RESERVE`). | Terbukti. Aturan buku non-PO (`compute_non_po_product_hpp_targets_v2620f`) menghitung reservasi aktif sebagai milik sendiri. | **Diperbaiki sesuai keputusan owner 23 Sep: "Ikut dihitung".** Stok tersedia tetap langsung berkurang saat direservasi (tidak diubah). Kasus `AX:RESERVED_STOCK_COUNTS_AS_ON_HAND`. |
| 5 | P2 (PLAUSIBLE) | Dipakai HPP lot versi terkini, bukan versi yang berlaku pada jam fisik. | Benar secara fakta. | **Tidak diubah, dengan alasan.** Koreksi HPP adalah biaya sebenarnya dari pcs yang sama. Prinsip owner: "kapan pun koreksi masuk, laporan menunjukkan angka sebenarnya". Hasilnya dikunci saat posting. Komentar fungsi diperbarui. |
| 6 | P2 | Sesudah versi SKU penerus berlaku, GOOD dari BS temuan tidak pernah bisa diterima: versi lama sudah berakhir, versi penerus dianggap produk tidak cocok. | Terbukti. | **Diperbaiki (keputusan 1C).** Dipakai versi dari identitas yang sama yang berlaku pada jam fisik. Tanpa `product_id`, sistem memilih versi itu sendiri. Kasus `AX:SUCCESSOR_AFTER_FOUND_BS`. |
| 7 | P2 | Batas nilai owner (1e16) lebih longgar dari kolom `numeric(18,6)` (batas 1e12), sehingga muncul error mentah 22003. | Terbukti dari tipe kolom. | **Diperbaiki.** Nilai per pcs harus di bawah 1e12 dan total di bawah 1e18, dengan kode `FG_UNSOURCED_VALUE_INVALID`. Diuji di `AX:INVALID_NUMBERS`. |
| 8 | P2 | `quality_grade` menerima teks apa saja, padahal reservasi, penjualan, dan konversi hanya menangani GRADE_A. | Terbukti. | **Diperbaiki.** Hanya GRADE_A (`FG_UNSOURCED_GRADE_INVALID`). Diuji di `AX:INVALID_NUMBERS`. |
| 9 | P2 | Stok AX di satu lokasi memblokir konversi (rebranding) seluruh stok SKU itu di lokasi tersebut. Penyebabnya aturan lama `NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW`. | Terbukti sebagai interaksi dengan kode lama. | **Belum diubah; dicatat untuk owner.** Tidak ada angka salah (ditolak, bukan dihitung keliru). Membuka konversi lot non-PO butuh alur HPP baru dan itu di luar AX. Masuk backlog dengan dampak bisnis. |
| 10 | P2 | Movement pembatalan bertanggal jam pembatalan. Jendela jam fisik "5 menit ke depan" membuat pembatalan gagal bila dilakukan sebelum jam itu lewat. | Terbukti. | **Tidak diubah, dengan alasan.** Jurnal dan movement pembatalan sama-sama diakui pada tanggal koreksi (pola ERP-DEC01), jadi buku fisik dan GL konsisten. Kegagalan di jendela 5 menit bersifat fail-closed dan bisa diulang. |

## Area yang diperiksa tanpa temuan
- **Keamanan:** SECURITY DEFINER + `search_path ''`, fungsi privat dicabut aksesnya, facade memeriksa owner, RLS tanpa privilege tabel.
- **Idempotensi:** kunci actor + operasi + request, dan hash payload dibandingkan.
- **Buku HPP non-PO:** target sama dengan buku besar saat posting dan saat pembatalan.
- **Zona waktu dan periode tertutup.**
- **Overdraw antar-posting GOOD:** kedua posting mengunci baris BS yang sama.
