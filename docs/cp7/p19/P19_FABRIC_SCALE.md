# P19 — Skala sumber dan hitungan kain (cabang Claude)

Status: perbaikan kandidat di cabang `claude/new-session-deapao`, belum dikualifikasi Native. `full_P19_acceptance=false`, `independent_acceptance=false`, `production_go=false`. CP6 tetap HOLD. Semua angka waktu di bawah adalah LOCAL_PG16_DEV pada data sintetis. Angka ini bukan bukti kinerja dan bukan SLA. Volume nyata pemilik belum diketahui; titik uji di bawah dipilih sebagai grid, bukan perkiraan bisnis.

## Masalah yang ditemukan

`cp7_fabric_native.plan` dan `needs` jauh lebih lambat dari pertumbuhan datanya, padahal panggilan aplikasi lewat Supabase biasanya dibatasi 8 detik:

| Titik uji (target / bahan / roll berisi / draf / baris PO) | `plan` lama | `needs` lama (semua baris) |
|---|---|---|
| 1.200 / 100 / 3.000 / 40 / 300 | 1,4–1,7 detik | 0,5 detik |
| 2.500 / 200 / 10.000 / 200 / 2.000 | 11–12 detik | (tidak diukur terpisah) |
| 5.000 / 300 / 20.000 / 1.000 / 10.000 | 57 detik | (diperkirakan > 8 detik) |

Penyebabnya:
1. **Pool per bahan.** Fakta per bahan (stok bebas, stok tidak konsisten, draf manual, PO, hash) dihitung dengan subquery yang memindai semua roll dan sel stok untuk setiap bahan, sehingga waktunya tumbuh sebesar bahan × roll.
2. **Pemeriksaan draf.** Setiap draf terhubung memindai seluruh roll dan sel stok, sehingga waktunya tumbuh sebesar draf × roll. Bahan per target juga dicari ulang per target.
3. **Salinan objek besar per baris.**
   - `recipe_state` membaca `ix->'selected'->kunci`, yang menyalin seluruh objek resep di setiap baris.
   - `needs` memanggil `plan->'index'` dan `plan->'targets'`, yang menyalin seluruh indeks dan seluruh peta target di setiap baris.
   - Akibatnya waktunya tumbuh sebesar target².

Kegagalan ini tertutup: angkanya tidak salah, tetapi ambil analisis akan habis waktu dan ditolak. Pada volume besar, analisis jadi tidak bisa dipakai.

## Perbaikan (hasil wajib sama persis)

- **Pool per bahan.** Setiap fakta dihitung sekali dengan `group by`, lalu digabung ke daftar bahan.
- **Draf terhubung.** Setiap draf unik diperiksa sekali lewat hash join; bahan per target juga dikelompokkan sekali.
- **Pencarian tanpa salinan.** `recipe_state` memakai `#>` (jalan path tanpa menyalin isi).
- **Bentuk keluaran `plan`.** Keluarannya sekarang datar: kunci indeks (`selected`, `materials`, `patterns`) berada di tingkat atas, ditambah `physical_source` dan `targets`. Dengan begitu `needs` membaca path langsung tanpa menyalin indeks per baris. Keluaran `plan` hanya dipakai `needs` di `cp7_analysis_native.build`; tidak ada konsumen lain.
- **Yang tidak berubah.** Kontrak analisis, sidik jari, hak, nama dan signature fungsi, kode alasan, dan semua angka.

Waktu sesudah perbaikan (LOCAL, `plan` dan `needs` dihitung di memori seperti di produksi):

| Titik uji | `plan` | `needs` semua baris |
|---|---|---|
| 1.200 / 100 / 3.000 / 40 / 300 | 0,5 detik | 0,1 detik |
| 2.500 / 200 / 10.000 / 200 / 2.000 | 1,2 detik | — |
| 5.000 / 300 / 20.000 / 1.000 / 10.000 | 3,0–4,0 detik | 0,5 detik |

Sumber fisik (`physical_source`, dengan versi yang sudah membuang roll habis) dari tabel ERP sintetis:

| Data | Waktu |
|---|---|
| 20.000 roll historis, 3.000 berisi | 0,16–0,27 detik |
| 100.000 roll (190 ribu gerakan), 20.000 berisi | 0,9–1,4 detik |
| 20.001 roll berisi | menolak dengan `CP7_FABRIC_PHYSICAL_LIMIT` (1,2 detik), tanpa potongan diam-diam |

## Bukti kesetaraan (LOCAL)

Fungsi lama disalin ke skema sementara, lalu versi lama dan baru dijalankan pada data acak yang sama. Hasilnya dibandingkan:
- `targets` dari `plan`, persis sebagai teks JSON;
- indeks;
- `physical_source`;
- keluaran `needs` untuk setiap baris, persis sebagai teks.

Ada dua jenis data:
- **Data tepi:** resep tidak valid, bahan nonaktif, beda satuan, pola hilang, roll tidak konsisten, stok negatif, roll hilang, lokasi nonaktif atau bukan gudang, draf manual, draf multi-target, draf tanpa baris, PO lewat tanggal, tanpa tanggal, tanpa sisa, dan PO ke lokasi salah, kebijakan PAUSED/STOPPED/kosong, celah nol/kosong, identitas WIP belum pasti, dan sumber fisik tidak ada.
- **Data bersih:** dipakai untuk menjangkau jalur angka (stok cukup, satu pemakai, draf, PO tepat waktu).

Hasil: 3.300 set data (sekitar 18 ribu baris target), 0 beda. Semua kode alasan tambahan-dari-luar dan semua dasar sisa layak ikut terjangkau. Kontrol SQL Shell kain 28/28 juga lulus pada kode baru (LOCAL).

Kualifikasi wajib di CI pada head baru, karena SQL produk berubah: fabric-physical21, fabric13, analysis152, plan39, attention284, fabric-rule11, rule-lifecycle16, p18-e01-9, Shell S0 dan CodeQL.

## Sumber kondisi pengingat (`condition_rows`)

Masalahnya sama dengan hitungan kain:
- setiap baris menyalin seluruh analisis (`e->'analysis'->>'semantic_hash'`);
- setiap baris memindai semua label produk dan semua dokumen piutang;
- hasil digabung dengan `||`.

| Target (1 baris aksesori + 1 kain per target) | Sebelum | Sesudah |
|---|---|---|
| 300 (900 kondisi) | 1,3 detik | 0,08 detik |
| 1.200 (3.600 kondisi) | 17,3 detik | 0,23 detik |
| 2.500 | ditolak setelah 81 detik | ditolak setelah 0,44 detik |

Perbaikannya:
- `semantic_hash` dibaca sekali;
- label dan dokumen piutang dicari lewat peta kunci yang dibangun sekali, dengan aturan "kecocokan pertama yang dipakai", sama seperti `SELECT … INTO` lama;
- baris dikumpulkan ke larik `jsonb[]` lalu diubah sekali.

Kesetaraan dibuktikan pada 3.000 set data acak, membandingkan versi lama dan baru sebagai teks persis. Data acaknya mencakup label ganda, label tanpa SKU, label tanpa target, dokumen piutang ganda dan hilang, utang tanpa nama pemasok, kebijakan GLOBAL aktif/nonaktif dengan satuan berbeda, dan Original basi. Hasilnya 2.316 hasil sama dan 684 penolakan sama (`CP7_RULE_CONDITION_AR_INCOMPLETE`, `CP7_RULE_CONDITION_SCOPE_INCOMPLETE`), tanpa beda.

**Batas 8 MB tercapai lebih dulu daripada batas 15.000 kondisi:** sekitar 1.370 byte per kondisi, atau ±1.900 target dengan satu baris aksesori (lihat `P18_FABRIC_RULE.md`). Ini keputusan kapasitas untuk GPT/owner, bukan diubah di cabang ini.

## Temuan di luar kode kain (untuk GPT; tidak diubah di cabang ini)

1. **Loop `cp7_analysis_native.build` menggabungkan hasil per baris dengan `||`.**
   - Larik yang terkena: `recommendations`, `materials`, `metrics`, `actions`, `models` dan lain-lain.
   - Setiap penggabungan menyalin seluruh larik, sehingga waktunya tumbuh sebesar target².
   - Ukuran lokal hanya untuk pola penggabungan `materials`, dengan dua baris bahan ±1,1 KB per target:

     | Target | Waktu |
     |---|---|
     | 1.200 | 4 detik |
     | 2.500 | 17 detik |
     | 5.000 | 85 detik |

     Dengan agregasi (`jsonb_agg`), ukuran yang sama butuh 0,01–0,04 detik.
   - Pencarian per baris ke `c->'facts'->'products'` dan ke riwayat stok juga memindai seluruh larik setiap baris.
   - Usulan: kumpulkan ke larik PL/pgSQL (`jsonb[]`) lalu ubah sekali di akhir, atau bangun lewat agregasi. Bukti kesetaraannya dengan pola yang sama: versi lama lawan baru, dibandingkan byte-per-byte.
2. **Snapshot keuangan pemilik dihitung dua kali per ambil analisis.** Satu kali di `capture`, satu kali lagi di `serve` untuk cek basi. Di DB lokal, setiap snapshot butuh ±10–11 detik walaupun data GL sangat kecil (12 jurnal):
   - Hampir semuanya untuk mengompilasi query besar `erp.initial_prepayment_checks_v1` (CP6) lewat JIT PostgreSQL (`jit=on`, ambang biaya default). Satu panggilan butuh 1,5 detik dengan JIT, dan < 1 ms dengan `jit=off`. Fungsi ini dipanggil 5 kali per snapshot.
   - `book_signature` meng-hash setiap jurnal, baris jurnal dan saldo harian sejak awal. Waktunya tumbuh bersama riwayat GL, di setiap ambil dan setiap baca analisis.
   - Perlu dicek apakah `jit` aktif di Supabase hosted. Ini hanya baca pengaturan, tanpa mengubah apa pun.
   - Pilihan perbaikan (keputusan GPT/owner, menyentuh CP6 atau finance): `set jit=off` pada fungsi pemeriksaan tersebut, atau batas biaya JIT yang lebih tinggi, ditambah tanda tangan buku yang inkremental.

## Alat pembanding untuk auditor

`scripts/cp7_p19_equivalence.py DSN BASE_REF [N] [SEED]` membandingkan definisi lama dan baru sebagai teks JSON persis:
- definisi lama dari `BASE_REF`, misalnya `d443d8c4`, yaitu sebelum perubahan P19;
- definisi baru dari working tree;
- tiga kelompok data acak: kain tepi, kain bersih, dan `condition_rows`;
- semua berjalan di satu transaksi yang di-rollback.

Alat ini hanya untuk DB lokal yang sudah berisi bundel analisis dan pengingat CP7. Hasilnya LOCAL, bukan kualifikasi.

Hasil LOCAL pada 2ae1db92, dengan basis d443d8c4 dan 200 data per kelompok: PASS, 0 beda (kain tepi 200 sama, kain bersih 200 sama, kondisi 184 sama + 16 penolakan sama).

Kontrol negatif: alat yang sama menandai FAIL bila sengaja dibuat beda kecil.
- Label `condition_rows` diubah menjadi "kecocokan terakhir": 60 beda.
- Stok bebas kosong diubah menjadi `'1'`: 64 beda di data tepi dan 41 di data bersih.

Perubahan sengaja itu sudah dikembalikan.

## Riwayat CI

| Head | Hasil |
|---|---|
| a4ebb6a8 (perbaikan `plan`/`needs`) | Semua PASS: fabric-physical21 21/21, fabric13 13/13, analysis152 152/152, plan39 39/39, attention284 284/284 (run 37404829353); fabric-rule11 11/11, rule-lifecycle16 16/16, p18-e01-9 9/9 (run 37404835115); Shell S0, CodeQL dan receipt-correction PASS. |
| 882fc40a/2ae1db92 (perbaikan `condition_rows`) | **Semua PASS.** P18 di 882fc40a (run 37406898697): fabric-rule11 11/11, rule-lifecycle16 16/16, p18-e01-9 9/9. P08 di 2ae1db92 (run 37408720092): fabric-physical21 21/21, fabric13 13/13, analysis152 152/152, plan39 39/39, attention284 284/284. Shell S0, CodeQL dan receipt-correction PASS. Hash sumber bundel pengingat sama di kedua run (`18043e14…`); 2ae1db92 hanya menambah dokumen. |

## Batas

Belum ada uji beban multi-pengguna, pemulihan setelah hak dicabut, atau uji ambil analisis penuh pada volume besar dengan data Native. Uji ambil analisis penuh tertahan oleh temuan 1 dan 2 di atas.
