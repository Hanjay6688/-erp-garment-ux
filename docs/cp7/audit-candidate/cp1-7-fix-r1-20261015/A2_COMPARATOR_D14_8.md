# A2 — pembanding skema `public` dengan urutan stabil (keputusan owner D14-8)

Keputusan owner (15 Okt 2026, persis): "Ya, betulkan pembanding lama. Gunakan urutan yang stabil, dengan seluruh
anggota, duplikat, definisi, owner, dan hak akses tetap dibandingkan. Simpan bukti sebelum/sesudah. Penyebab dua
kegagalan lama tetap OPEN sampai benar-benar terbukti."

## Cacat pembanding lama

`scripts/cp6_auditor_runner.py` membaca keadaan skema `public` sebelum dan sesudah tiap kasus. Daftar fungsinya disusun
dengan `jsonb_agg(... order by 1)`. Di dalam `jsonb_agg`, `order by 1` mengurutkan dengan **angka tetap 1**, bukan
dengan kolom pertama, jadi urutan daftar mengikuti cara PostgreSQL membaca katalog (rencana query). Dua bacaan atas isi
yang sama bisa berbeda urutan. Pembanding lama juga tidak memuat owner dan hak akses.

## Perubahan

- `PUBLIC_STATE` (yang dipakai sekarang): relasi dan fungsi diurutkan dengan kolasi `"C"` atas nama, lalu jenis /
  hash definisi, lalu seluruh entri, sehingga urutannya tidak bergantung rencana query. Tiap entri berisi:
  - relasi: nama, jenis, owner, daftar hak akses (ACL) yang diurutkan;
  - fungsi: tanda tangan lengkap (nama + tipe argumen, jadi overload terpisah), hash definisi, owner, ACL yang diurutkan.
  Semua anggota tetap ada (tidak ada `distinct`), jadi duplikat tetap terhitung.
- `PUBLIC_STATE_BEFORE_D14_8`: query lama disimpan apa adanya, hanya untuk bukti sebelum/sesudah.
- `catalog_observation` di laporan menjelaskan bentuk entri baru.

## Bukti sebelum/sesudah

`scripts/cp6_auditor_public_state_test.py`, dijalankan di workflow `CP7 CP17 Fixes` (langkah "Prove the stable
public-schema comparator") pada database sekali pakai: 240 fungsi dibuat dengan urutan nama terbalik, ditambah dua
fungsi bernama sama (`same_name(int)`, `same_name(text)`) dan satu tabel. Hasil lokal (PostgreSQL 16, PASS):

| Pemeriksaan | Pembanding lama | Pembanding baru |
|---|---|---|
| Sama urutan di bawah rencana sequential scan dan index scan | **Tidak** (tiga pertama `f_239, f_238, f_237` vs `f_000, f_001, f_002`; selisih dilaporkan `ORDER_ONLY`) | **Ya**, identik |
| Jumlah anggota (katalog 242) | 242 | 242, pasangan tanda tangan + hash definisi sama dengan lama, 2 overload terhitung |
| Definisi fungsi diganti | Terlihat (isi) | Terlihat |
| Fungsi dihapus | Terlihat (isi) | Terlihat |
| Owner fungsi diganti | Tidak terlihat isinya (hanya `ORDER_ONLY` karena baris katalog berpindah) | Terlihat |
| Hak akses fungsi ditambah | Tidak terlihat isinya (hanya `ORDER_ONLY`) | Terlihat |
| Hak akses tabel ditambah | Tidak terlihat isinya | Terlihat |

Catatan yang direkam, tidak disembunyikan: sesudah hak akses diberikan lalu dicabut lagi, PostgreSQL menyimpan daftar
hak akses yang tertulis (mis. `=X/postgres`) di tempat yang semula kosong (`NULL`). Haknya sama, tapi yang tersimpan
berbeda; pembanding baru membandingkan yang tersimpan apa adanya, jadi melaporkannya (`after_undo`).

## Yang belum terbukti

**Penyebab dua kegagalan A2 lama tetap OPEN (D13-10).** Pengamatan di atas (pembanding lama melaporkan `ORDER_ONLY`
sesudah baris katalog ditulis ulang, misalnya oleh `ALTER` atau `GRANT` lalu dibalik) adalah mekanisme yang mungkin,
bukan bukti bahwa itulah yang terjadi pada dua run lama. Bukti asli kedua kegagalan itu tetap disimpan dan tidak diubah.

## Kegagalan pertama perubahan ini (disimpan)

Versi pertama (`c2141e47`/`a3cb1beb`) menulis `x->>0 collate "C"`. `COLLATE` mengikat lebih kuat daripada `->>`, jadi
PostgreSQL menempelkannya ke angka `0` dan menolak: "collations are not supported by type integer". Semua workflow yang
memakai pembanding ini gagal di awal (CP17 run 38665623424; Owning Receipt Correction, Supplier Payment Create, P18 Full
Cycle, P21 Rehearsal pada `a3cb1beb`). Dibetulkan di `59fc7baf` dengan tanda kurung `(x->>0) collate "C"`. Log gagal
tersimpan di run-run itu.

Run CI pertama alat bukti ini (CP17 run 38667277783 di `4daee0e1` dan 38667389165 di `a0cd5782`, log disimpan) gagal
sebelum membandingkan apa pun: di CI pengguna database bukan superuser, dan PostgreSQL hanya mengizinkan ganti owner
fungsi bila owner barunya punya hak CREATE di skema itu ("permission denied for schema public"). Di database sekali
pakai itu peran uji sekarang diberi hak tersebut sebelum pengukuran; hak skema bukan bagian dari kedua pembanding.
Diuji lokal sebagai superuser dan sebagai pengguna biasa (CREATEDB, CREATEROLE): keduanya PASS. Kasus CP17 sendiri di
kedua run itu lulus 48/48.
