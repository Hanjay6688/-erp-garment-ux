# CI writer pada kandidat alat `5db7c876` (bukan penerimaan auditor)

| Workflow | Run / job | Sumber | Penyimpanan | Hasil |
|---|---|---|---|---|
| `CP7 Offsite Backup` | 38392325940 / 115278895220 | Salinan ERP CP6 (`cp6_rollback`, PG 17.6) | Peniru S3 + folder | **11/11 × 2 PASS**, sumber tidak berubah |
| `CP7 Backup Kit Check` | 38392325954 / 115278907785 | Data buatan `proof_seed.sql` di database `postgres` image Supabase 17.6.1.165 (`proof.sh`) | Peniru S3 + folder (`proof-<run>`) | **11/11 × 2 PASS**, sumber tidak berubah |

Baris kasus run pertama ada di `offsite_backup_11_5db7c876_run38392325940_job115278895220.log`. Log job kedua terbuka
di Actions.

## Yang terukur (`OFB_VERIFIED_FROM_FETCHED_COPY`)

| | Salinan ERP CP6 | Data buatan (perlengkapan) |
|---|---|---|
| Tabel / baris / nomor urut | 265 / 1.410 / 10, semuanya sama | 8 / 2.207 / 3, semuanya sama |
| Galat pemulihan | 19, semuanya pg_cron (`by_category: CRON`) | 0 |
| Beda struktur ketat (`structure.differ`) | 0 | 0 |
| Dijelaskan (`structure.explained`) | `extension_initial_acls`: 2 (skema `graphql`, `graphql_public`) | `extension_initial_acls`: 2 |
| **Perbedaan asli tercatat (`structure.raw_differ`)** | schemas 4, relations 204, constraints 58, indexes 2, views 14, functions 18 | schemas 4, relations 2, constraints 4 |

Angka di `raw_differ` adalah jumlah baris yang beda di kedua sisi (satu objek = 2 baris). Semuanya berasal dari tiga
penyeragaman di `README.md`, dan rinciannya tersimpan di bagian terkunci (`structure_raw_differ`).

Kasus `OFB_STRUCTURE_DIFFERENCE_DETECTED` mengubah hak akses, aturan kolom, dan daftar `IN` varchar di hasil pulihan.
Ketiganya tetap tertangkap (`columns 2, constraints 2, relations 2`).

## Batas

- Penyimpanan yang dipakai di sini peniru S3 dan folder. **Google Drive belum dibuktikan** (D13-8d).
- Pemulihan berjalan sebagai admin penuh di server sementara. Lulus di sini belum membuktikan pemulihan hosted
  (D13-8b).
