# Review jadwal dari sumber bertahap — B, DRAFT, belum Native-qualified

Native5/WIP2 sudah lulus. Upaya SAVE2000/202000 pertama berhenti sebelum SAVE
karena setup membutuhkan capture supply v1 lama (1000 produk/50000 gerakan).
Lihat `docs/cp7/d17-14/ow13c/fa3375e-scale2-first-incomplete.json`.

Modul ini menambahkan jalur review **metadata pekerjaan dan kalender** dari
referensi asli job bertahap. Tidak mengubah fungsi Native lama, validator,
batas history atau sumber SQL beku. Belum dipasang default/hosted dan belum
boleh dianggap menyelesaikan SAVE2000, analisis besar atau OW13c.

- GET `erp_cp7_get_staged_production_schedule_v1(p_source_request uuid)`
  menerima UUID permintaan analisis bertahap asli milik pengguna, bukan UUID
  run yang baru terlihat setelah analisis selesai. RUNNING/DONE diterima;
  DONE tetap harus lolos penjaga retensi. FAILED/asing tidak diterima.
- GET menampilkan referensi waktu, hash dan kebutuhan pekerjaan dari snapshot
  yang diperiksa, keadaan sumber terkini, `history_capture_state` dan
  `production_capture_state`. Mengambil formulir tidak menulis apa pun.
- SAVE menerima `source_run` nyata yang dikembalikan GET, `source_hash`,
  `expected_revision`, `config`, `reason`, dan `staged_review_contract` tepat
  `cp7.schedule-staged-review.v1`. Permission, request/global lock, UUID/revisi,
  validator kalender/global WIP/target-bound asli dan riwayat append-only sama.
  Sumber/akses diperiksa sesudah wait, sumber kerja/akses kembali sesudah
  metadata ditulis; penolakan harus atomik.
- RUNNING dapat dipakai untuk menyiapkan jadwal sebelum analisis dihitung.
  Kelayakan produksi dan kuantitas **tidak** diperoleh dari keadaan ini.
  Riwayat besar yang INCOMPLETE tetap ditampilkan demikian; jalur analisis/
  checked-save tidak dibuka dengan mengubah completeness/hash atau menambah
  baris run/proof palsu. Batas raw history50000 masih perlu ditangani oleh
  engine bertahap untuk fixture padat202000; modul metadata ini sendiri tidak
  membuktikan atau menyelesaikannya.
- 1 schema privat/3 fungsi privat/2 facade publik,0 tabel baru/0 penggantian
  badan Native. Hanya `cp7_capture` memiliki akses privat; authenticated boleh
  memanggil facade dengan validasi akun/hak saat ini. anon/service_role ditolak.
- `install_delta`, `verify`, `admit_catalog`, `rollback_preuse` tidak membuka
  koneksi/commit. A menyediakan transaksi/envelope/global census/default.
  Invers sebelum pakai harus tepat22 kelompok; setelah command bertag ada,
  invers menolak sebelum DDL. Tidak ada CASCADE.

`render.py` menurunkan dua badan baru dari Native workspace/save dengan anchor
tepat dan pin7 helper; `review.sql` harus tepat hasil render. Bagian validasi
pekerjaan/target/calendar dan penyimpanan metadata bukan salinan rumus stok,
uang/HPP atau pembentukan hasil analisis.

Pemeriksaan lokal baru: render/pin/kompilasi Python/scanner SQL. Masih wajib:
Native pasang/invers22/otoritas, RUNNING/DONE/asing/retensi, SAVE/replay/revisi,
current-source/current-access setelah wait, atomic fault, metadata besar,
Auth/browser/layar dengan UUID tahan putus, dan pemasangan A. Generator tipe/
source registry/default installer milik A; panel produksi/perencanaan milik B.

Rujukan: panduan fungsi database Supabase dan transaksi PostgreSQL, dicek
24 Oktober2026. Schema/fungsi privat memakai search_path kosong, pembatasan
EXECUTE eksplisit; metadata tidak mengubah fakta ERP/uang/stok/HPP.
