# Paket uji silang: alat backup ke penyimpanan luar (versi 2) — 13 Okt 2026

Dasar: keputusan owner D13-5..D13-8 (`docs/cp7/OWNER_DECISIONS_20261008.md`). D13-8e berbunyi: "Kirim paket versi yang
sama ke Astra dan Fable untuk uji silang. Penyeragaman constraint/ACL dan perlakuan skema GraphQL harus ikut
diperiksa, dengan perbedaan aslinya tetap tercatat."

Paket ini terpisah dari putaran silang 1 CP7 (`../crosscheck-r1-20261013/`, kandidat `ae0214ad`). Kedua auditor
menerima **paket yang sama**. `production_go:false`. Belum ada yang dipasang. Enteng, Google Drive dan hosted belum
disentuh.

## Identitas

- **Kandidat alat: `5db7c8763a651304b2fd37b8eadb9616d0afe151`**, cabang `claude/new-session-deapao`.
- Workflow repo privat (`ops/backup-repo/workflows/`) mengambil alat pada commit itu. Uji dan baca pada commit itu, atau
  pada HEAD cabang untuk berkas `ops/backup-repo/workflows/*` dan dokumen.
- Kode produk ERP (`supabase/`, `src/`, `scripts/cp7-src/`) tidak berubah. Buktinya:
  `git diff --name-only ae0214ad 5db7c876 -- supabase src scripts/cp7-src` kosong.

## Isi paket (di luar `docs/`)

| Berkas | Isi |
|---|---|
| `scripts/cp7_offsite_backup.py` | Alat. Satu potret waktu (dump, hash data, nomor urut, sidik struktur) → enkripsi gpg AES256 → unggah rclone → unduh kembali → cek SHA-256 file terkunci dan dump → pulihkan di server sementara di mesin yang sama (versi mayor sama, bukan server sumber, harus lokal) → bandingkan data, nomor urut, struktur, pemilik, hak akses → tanda terima biasa (kode dan angka) dan rincian terkunci → simpan 14 malam terverifikasi di penyimpanan. Aturan database sementara memakai `cp7_nightly_backup.py` (kepemilikan per OID, ASR-OPS-01). |
| `scripts/cp7_offsite_backup_cases.py` | 11 kasus (daftar di bawah). Hanya menerima folder penyimpanan bernama `cases` atau `proof-<id>`, karena kasus mengosongkan folder itu. |
| `.github/workflows/cp7-offsite-backup.yml` | 11 kasus × 2 penyimpanan (peniru S3 dan folder). Sumbernya salinan ERP CP6 di CI, dan server pemulihannya kontainer kedua dengan image Supabase yang sama. |
| `ops/backup-repo/proof.sh`, `proof_seed.sql` | Uji untuk repo privat: dua kontainer Supabase Postgres, data buatan, lalu 11 kasus ke folder `proof-<id>`. |
| `.github/workflows/cp7-backup-kit-check.yml` | Menjalankan `proof.sh` dengan peniru S3 dan folder, untuk memeriksa mekanik perlengkapan. |
| `ops/backup-repo/workflows/drive-proof.yml`, `nightly-backup.yml`, `README.md` | Untuk repo privat owner (D13-8c): uji Drive sungguhan, backup awal, lalu backup malam. Isinya runner standar, satu job sekali jalan, batas waktu, tanpa cache dan artifact, rahasia lewat Secrets. |
| `.github/workflows/cp7-nightly-backup.yml` | Templat di repo ini, tetap nonaktif. |

## Penyeragaman pembanding (wajib diperiksa auditor, D13-8e)

Keputusan "terverifikasi" memakai sidik **yang diseragamkan**. Sidik **mentah** dibandingkan juga, dan setiap
perbedaannya dicatat: jumlahnya di `structure.raw_differ` (tanda terima), rinciannya di `structure_raw_differ`
(rincian terkunci).

| Penyeragaman | Alasan | Pembatas supaya tidak melonggarkan |
|---|---|---|
| Bentuk `(ARRAY['A'::character varying, …])::text[]` → `ARRAY[('A'::character varying)::text, …]` di kedua sisi | PostgreSQL menulis ulang bentuk ini saat definisi lewat pg_dump. Direproduksi di PG16 lokal (`CHECK (col IN (...))` pada kolom varchar). Pola lain yang diuji (bigint, text, bpchar, numeric, `NOT IN`, `ANY('{..}'::text[])`) tidak berubah. | Hanya pola persis itu (literal bertipe dalam ARRAY yang di-cast utuh). Kasus `OFB_STRUCTURE_DIFFERENCE_DETECTED` mengubah daftar `IN` di hasil pulihan, dan perubahan itu tetap tertangkap. |
| ACL kosong (NULL) = ACL bawaan (`acldefault`), dan ACL dibandingkan sebagai himpunan | pg_dump tidak menulis ACL yang sama dengan bawaan, sehingga hasil pulihan NULL. Urutan isi ACL bisa berbeda. | Arti tetap dibandingkan. Mencabut hak akses tetap tertangkap (kasus yang sama). |
| Objek yang di sumber punya `pg_init_privs` jenis ekstensi (`privtype='e'`): ACL-nya dibandingkan di kategori `extension_initial_acls` (**dijelaskan, tidak menggagalkan**) | Di image Supabase, skema `graphql` dan `graphql_public` mendapat hak akses dari event trigger saat pg_graphql dibuat. pg_dump tidak menuliskannya, sehingga hasil pulihan tanpa hak akses itu. | Hanya untuk objek yang di sumber tercatat sebagai hak awal ekstensi. Objek ERP tidak termasuk. Jumlahnya ada di `structure.explained` setiap malam. |
| Urutan peran di kebijakan RLS dan urutan tabel di publikasi diurutkan menurut nilai | Sebelumnya `string_agg … order by 1`: angka 1 adalah konstanta, jadi urutannya mengikuti baris fisik (jebakan yang sama dengan CAT-01). | — |

Hasil CI di sumber ERP CP6 (run 38385679082, sebelum pencatatan mentah ditambahkan):
- data 265 tabel dan 10 nomor urut sama persis;
- 19 galat pemulihan, semuanya pg_cron;
- `structure.explained` = {`extension_initial_acls`: 2}.

Run di kandidat ini ada di `CI_RECEIPT.md` (diisi setelah selesai).

## 11 kasus

`OFB_VERIFIED_FROM_FETCHED_COPY`, `OFB_NO_CONTENT_OUTSIDE_THE_REMOTE`, `OFB_TAMPERED_REMOTE_COPY_UNVERIFIED`,
`OFB_DATA_DIFFERENCE_DETECTED`, `OFB_STRUCTURE_DIFFERENCE_DETECTED`, `OFB_SEQUENCE_DIFFERENCE_DETECTED`,
`OFB_VERIFIED_UNDER_WRITES`, `OFB_REMOTE_RETENTION_14_VERIFIED`, `OFB_NAME_COLLISION_REFUSED`,
`OFB_SCRATCH_SERVER_GUARDS`, `OFB_FOREIGN_SCRATCH_NAME_REFUSED`. Penjelasan per kasus ada di `docs/cp7/OFFSITE_BACKUP.md`.

## Batas yang dinyatakan (bukan dianggap disetujui)

- **Google Drive belum dibuktikan.** Butuh akun owner (`ops/backup-repo/README.md` langkah D). Kelulusan peniru S3 dan
  folder tidak dihitung (D13-8d).
- Pemulihan malam berjalan di Supabase Postgres sementara di runner, sebagai admin penuh yang dibuat di server sementara
  itu. Lulus di sana belum membuktikan pemulihan ke Supabase hosted (D13-8b).
- **Uji pemulihan dengan batas hak akses seperti hosted** (pulih sebagai `postgres` yang bukan admin penuh, ke Supabase
  lokal lengkap, D13-8b) **belum dibuat**. Itu paket berikutnya.
- Hosted belum pernah dibaca. Hak baca peran `postgres` atas semua tabel baru ketahuan saat backup awal.
- File Supabase Storage tidak ikut. ERP tidak memakainya.
