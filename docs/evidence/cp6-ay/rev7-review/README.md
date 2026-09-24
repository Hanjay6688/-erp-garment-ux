# Pemeriksaan independen AY rev7 (`0bbfd55`) — repro dan fuzz (T1_FAMILY, bukan bukti rilis)

Pemeriksa: sub-agent read-only dengan database stub sekali pakai sendiri (`rev7r_*`), tidak menulis repo.
Skrip di sini disalin apa adanya dari folder kerjanya. Path di dalamnya menunjuk scratchpad sesi; jalankan setelah
`../rev7-harness/run.sh` membangun database, dengan fungsi `sync_po_hpp_to_gl_as` (salinan AS) bila skrip membutuhkannya.

Temuan (ringkas; rinciannya di handoff §25):
- F1 MAJOR: PO yang diproduksi sebelum AY dipasang tidak punya state bahan → M-1 tetap terjadi (x2; WIP PO −3,50).
- F2 MAJOR (bila JIT aktif di hosted): perencana salah taksir → kompilasi JIT ±4 s di bawah lock global (x_perf_*).
- F3 MINOR: rantai relabel masih berayun lewat akun lainnya (x1).
- F4 MINOR: pengenceran kolam batch oleh grup yang dipotong sesudah penanda dicatat pada hari lot (x6); tidak membuat
  saldo negatif (FG terlalu rendah di awal, WIP terlalu tinggi).
Diperiksa OK: jalur non-invoice dan E tertutup identik dengan AS (x8, fuzz), total per akun = AS pada semua seed fuzz yang
diterima AS sendiri, dua bahan dalam satu statement (x5), data pinggir tanpa error (x7, x9), model kolam = rebuild_po_hpp,
aturan state segar dan penanda SYNC, keamanan tabel baru.

`fuzz_out_rev7_0bbfd55.txt`: fuzz pemeriksa pada rev7 (400 seed × 3 mode; 108 penolakan semuanya dari cek konsistensi AS).
`fuzz_out_rev7_1.txt`: fuzz yang sama pada rev7.1 (111 penolakan, semuanya dari AS; 0 error AY, 0 selisih total).
