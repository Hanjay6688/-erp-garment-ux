# Audit silang r3 dan rencana r4 (ditulis penulis sebelum perbaikan, dilengkapi saat laporan Sol masuk)

Laporan r3 yang sudah dikunci atas kandidat `b53b5acd`:

| Auditor | Cabang / kunci | Vonis |
|---|---|---|
| Fable | `audit/fable-cp1-7-r3-b53b5acd-20261017`, kunci `2033fdfc` (`audit/fable_cp17_r3/`) | Oracle D16-1 nomor 1–5 ditutup, FABLE-016 dan FABLE-018 ditutup, tidak ada temuan baru; FABLE-012 tetap ditunda (D14-9) |
| Astra | `audit/astra-cp1-7-r3-b53b5acd-20261018`, kunci `741ffdf3` (`audit/astra_cp17_r3/`) | TAHAN: 2 S1, 2 S2 |
| Sol | `audit/sol-cp1-7-r3-b53b5acd-20261017`, segel `ff6374ad` (`audit/sol_cp17_r3/`) | Tidak ada temuan produk baru dari pengujian buta; tiga butir terbuka yang sudah diketahui untuk penulis |

## Per akar masalah

| Akar | Temuan (tingkat tertinggi dipakai, best practice F29b) | Pemeriksaan keabsahan oleh penulis | Butir r4 |
|---|---|---|---|
| Jalur publik lama menulis tanpa penjaga fasad CP7 | ASTRA-R3-01 (S1), Sol KNOWN-POOL-PUBLIC-ENTRYPOINTS | Sah menurut sumber: `supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql:470-544` hanya memanggil `erp.require_owner_admin()` lalu penulis Native, dan diberi ke `authenticated`; aplikasi CP7 tidak memanggilnya. Keluarga: 69 fungsi publik non-CP7 yang bisa dieksekusi peran browser; 40 dipakai aplikasi, 4 rute pengingat pribadi, 25 ditutup | R4-01 |
| Buka ulang PO terhalang pembalik penyesuaian barang jadi positif | ASTRA-R2-01 sisa (S1) | Sah menurut sumber: `po-reopen.sql` menghitung setiap gerakan negatif sebagai pemakaian dikurangi pembaliknya sendiri, sehingga −2 pembalik dari +2 dihitung pemakaian | R4-02 |
| Audit Trail melewati id lebih kecil yang commit belakangan | ASTRA-R3-02 (S2) | Sah: direproduksi lokal dengan jadwal Astra pada `audit.sql` lama (COUNTEREXAMPLE), lulus pada yang baru | R4-03 |
| Angka WIP tersambung pucat di kartu putih | ASTRA-R3-03 (S2) | Sah menurut sumber: kartu memberi latar `#fff`, teks mewarisi `#f4f6fb`. Keluarga yang sama ditemukan sensus keterbacaan baru di Pola, panel pool HPP, tombol RecordTools BS, dan layar Master Data tersambung | R4-04 |
| Penulisan pengganti saat cek pemulihan backup | Sol KNOWN-BACKUP-REPLACEMENT-WRITE | Sah seperti tertulis di docstring alat (`scripts/cp7_nightly_backup.py`, "Operating boundary") | Disiapkan sebagai patch, tidak dipasang: semua pekerjaan backup ditahan sampai CP7C (owner D13-9a). `docs/cp7/cp17/r4-sol/` |
| Analisis langsung lambat | Sol KNOWN-P19-DIRECT-LATENCY | Sah sebagai pengukuran (run Sol 39146762696); celah yang sudah dideklarasikan di `P19_LOADING_BUDGET_20261006.md`. Owner D17-1: dikerjakan di r4 | R4-05 |

Butir bukti audit yang Sol simpan untuk dirinya (bukan pekerjaan penulis): 21 kasus browser CP17 biasa INCOMPLETE karena
grup melewati tengah malam WIB (hasil pertama disimpan, kualifikasi alat oleh Sol), lima percobaan ulang tanggal internal
dicatat terpisah, tiga oracle tambahan belum dijalankan.

## Keputusan owner di putaran ini

- D17-1 (19 Okt 2026 WIB): "A beresin aja, mau gw tinggal tidur soalnya" — kecepatan analisis langsung dikerjakan di r4
  sebelum paket uji ulang. Kutipan lengkap di `docs/cp7/OWNER_DECISIONS_20261008.md`.
