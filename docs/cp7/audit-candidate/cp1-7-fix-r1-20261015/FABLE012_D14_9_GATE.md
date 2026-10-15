# FABLE-012 — pencabutan hak panggil langsung ditunda ke CP7C, dengan gerbang (keputusan owner D14-9)

Keputusan owner (15 Okt 2026, persis): "Ya, pencabutan 82 fungsi boleh ditunda ke CP7C, berdasarkan bukti auditor
bahwa jalur tersebut tidak dapat dijangkau dari internet. Catat sebagai pekerjaan keamanan yang belum selesai. Jika
konfigurasi akses berubah sehingga fungsi itu bisa dijangkau, pencabutannya menjadi prasyarat sebelum jalur tersebut
diaktifkan."

## Status

**Pekerjaan keamanan yang belum selesai (CP7C).** Peran `authenticated` masih bisa menjalankan (EXECUTE) 82 fungsi
penulis di skema `erp` yang tidak dirujuk oleh kode apa pun yang berjalan dengan hak pemanggil (inventaris
`scripts/cp7_access_inventory.py`, dicatat di laporan CP17 sebagai `fable012_erp_execute_inventory`). Hak itu
**belum dicabut**.

Alasan aman untuk sementara (bukti, bukan anggapan):

- `CP17_HTTP_ERP_WRITERS_NOT_REACHABLE`: dengan login Auth nyata, ke-82 fungsi itu dipanggil satu per satu lewat Data
  API dengan profil `erp`; semuanya ditolak `406 PGRST106` (skema tidak dibuka) sebelum SQL apa pun berjalan, dan batas
  bisnis tidak berubah.
- Runbook pemasangan meminta skema yang dibuka Data API tetap `public` dan `graphql_public` saja, tanpa `erp`, dan
  melarang menimpa PostgREST dengan `ALTER ROLE` (`docs/runbooks/erp_enteng_v2_6_11a_preconnect.md`, bagian "Data API
  acceptance").
- Setelan Data API di hosted dibaca oleh Fable (D14-7), bukan oleh penulis.

## Gerbang: pencabutan dulu, baru jalur dibuka

`exposure_gate(cur, declared_schemas, declared_extra_search_path)` di `scripts/cp7_access_inventory.py` (hanya
membaca, tidak mengubah apa pun). Gerbang **menolak** dengan `CP7_FABLE012_REVOKE_BEFORE_EXPOSING_ERP` dan
menyebut fungsi yang harus dicabut dulu (`revoke_first`) bila skema `erp` akan terjangkau lewat salah satu jalan ini,
sementara `authenticated` masih bisa menjalankan penulis tanpa rujukan tadi:

| Jalan | Dari mana gerbang tahu |
|---|---|
| `erp` dimasukkan ke skema yang dibuka Data API (Dashboard / konfigurasi PostgREST) | Dinyatakan pemanggil (`--schemas`); database tidak bisa melihat setelan Dashboard |
| `erp` dimasukkan ke "extra search path" Data API (nama tanpa skema dan refleksi GraphQL ikut jalur ini) | Dinyatakan pemanggil (`--extra-search-path`) |
| Penimpaan yang disimpan di database pada peran `authenticator` (`pgrst.db_schemas`, `pgrst.db_extra_search_path`) | Dibaca langsung dari `pg_db_role_setting` (global dan per database), tanpa perlu dinyatakan |

Cara pakai sebelum setelan Data API diubah (autentikasi lokal; alamat database dari variabel lingkungan, tidak pernah
ditulis di chat atau di repo):

```bash
CP7_ACCESS_GATE_PGURL=... python3 scripts/cp7_access_inventory.py --schemas public,graphql_public,erp
# keluar 0 = boleh; keluar 3 = DITOLAK, daftar revoke_first harus dicabut dulu
```

Tanpa argumen, gerbang memeriksa setelan runbook (`public,graphql_public` / `public,extensions`) ditambah penimpaan
yang tersimpan di database.

## Bukti

`CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST` (kasus native CP17, deklarasi dibuat sebelum dijalankan):

1. Setelan runbook: lolos; tidak ada penimpaan tersimpan; jumlah penulis tanpa rujukan ≥ 60 (82 di stack terpasang).
2. `erp` di skema yang dibuka: ditolak, `revoke_first` = seluruh penulis itu.
3. `erp` di extra search path: ditolak, daftar sama.
4. Penimpaan tersimpan `ALTER ROLE authenticator SET pgrst.db_schemas='public, graphql_public, erp'` tanpa
   dinyatakan: ditolak.
5. Sesudah EXECUTE dicabut dari `authenticated` dan `PUBLIC` tepat pada fungsi `revoke_first`: gerbang lolos walau
   `erp` dibuka.

Langkah 4–5 berjalan di savepoint yang dibatalkan; sesudahnya gerbang memberi hasil yang sama persis dengan langkah 1.
Laporan CP17 juga mencatat hasil gerbang pada setelan runbook (`fable012_exposure_gate`).

## Pekerjaan CP7C yang tersisa (tidak dikerjakan sekarang)

1. Pindahkan sekitar 700 pemanggilan langsung di 194 berkas alat uji lama ke peran admin/pemasang, supaya pencabutan
   tidak mematahkan alat uji.
2. Cabut EXECUTE dari `authenticated` (dan `PUBLIC`) pada fungsi `revoke_first`; panggilan langsung harus ditolak
   `42501`; seluruh suite fasad tetap lulus.
3. Jalankan gerbang lagi; hasilnya harus lolos sebelum setelan Data API apa pun yang menyentuh `erp` diaktifkan.

## Batas

- Gerbang tidak bisa membaca setelan Dashboard hosted; setelan itu harus dinyatakan oleh yang akan mengubahnya.
- Gerbang tidak menilai apakah membuka `erp` itu bijak; runbook tetap melarangnya. Gerbang hanya memastikan urutannya:
  cabut dulu, baru buka.
- Gerbang mengikuti keputusan D14-9, yaitu 82 fungsi penulis. Inventaris yang sama mencatat bahwa `authenticated` juga
  punya hak atas 157 tabel/view `erp` (dibatasi RLS) dan bisa menjalankan 160 fungsi `erp` seluruhnya (run 38666407687,
  `fable012_erp_execute_inventory`). Bila `erp` suatu saat dibuka, hak-hak itu juga harus ditinjau di CP7C; gerbang ini
  tidak menggantikan peninjauan itu.
