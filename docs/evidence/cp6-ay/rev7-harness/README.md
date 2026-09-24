# Harness stub AY rev7 (T1_FAMILY, bukan bukti rilis)

Tujuan: menguji `erp.sync_po_hpp_to_gl` hasil `scripts/cp6_ay_build.py` dengan angka, di PostgreSQL lokal sekali pakai,
sebelum CI. Skema di `schema.sql` hanya stub minimal (tabel/kolom yang dibaca fungsi; `post_journal` stub mencatat
tanggal apa adanya). `targets_fn.sql` adalah `erp.compute_po_hpp_gl_targets_v2620d` apa adanya dari definisi terakhirnya (migration v2.6.20f).
Harness ini **tidak** menggantikan uji native (AZ/AY T1 di CI); ia menangkap salah hitung dan error runtime lebih awal.

Jalankan: `PGHOST=127.0.0.1 PGUSER=postgres bash docs/evidence/cp6-ay/rev7-harness/run.sh [nama_db]`

Skenario (tanggal relatif hari ini d; E = tanggal invoice):
| File | Yang diuji | Harapan |
| --- | --- | --- |
| r1_return | M-1: retur bahan potong sesudah lot | FG −17,50 pada hari lot, +3,50 pada hari retur; WIP PO + AZ = 0 tiap hari |
| r2_contractor | M-1: bahan kontraktor sesudah lot; header 22, gerakan 23 | −2,00 pada hari gerakan (23), bukan hari lot/header |
| r3_pool_po | M-1: lot tanpa grup (kolam PO) | sama dengan r1 |
| r4_relabel_reversed | F6: relabel dibatalkan | tidak ada baris akun lainnya |
| r4b_relabel_posted | relabel diposting, anak ikut di-recost | hanya FG −17,50 pada hari lot |
| r5_voided | lot VOIDED tanpa lot hidup | −17,50 lalu +17,50 pada hari pembatalan |
| r6_batch_sale | batch lintas hari lalu dijual; state lama/baru | +2,80 / +4,20 pada hari potong, HPP 1,91 pada hari jual |
| r7_writeoff | write-off dan penyesuaian + | total per akun = target (OTHER_INCOME netto −5,25) |
| r8_rounding | pembulatan hari jual | WIP 0 pada hari jual |
| r9_batch_two_pos | batch berisi grup dua PO | +2,80 lalu +2,29 (bahan PO lain masuk kolam pada harinya) |
| r10_contractor_new | fakta kontraktor sesudah penanda SYNC / tanpa penanda | +8,00 pada harinya / konstan (data sebelum AY) |
| r12_fresh_state | state ditulis hanya bila HPP baru di-rebuild pada statement yang sama | state C:/M:/SYNC tertulis |
| r13_no_state_derived | F1 pemeriksaan rev7: PO dari sebelum AY (tanpa state/penanda), nilai lama dari revaluasi sesudah rebuild terakhir | sama dengan r1; state ditulis |
| r14_relabel_chain | F3 pemeriksaan rev7: rantai relabel dua tingkat | tidak ada baris akun lainnya; −35,00 lalu +3,50 |
| r15_batch_dilution | F4 pemeriksaan rev7: grup baru dalam batch sesudah sync terakhir | −7,00 pada hari lot, +37,69 pada hari potong grup baru |
| r16_queued_recost | recost non-invoice yang masih mengantre saat invoice diproses | −7,50 pada hari lot (bagian invoice), −10,00 pada hari recost tertunda |
| r17_pocket_part | bagian kain kantong di HPP lot | −10,00 pada akhir periode kantong, bukan hari lot |
| f1, m2, f1_noninv, f1_closed | skenario dasar rev6 | tidak berubah; E tertutup dan jalur non-invoice tetap satu jurnal |
| perf.sql | M-4 | lihat `perf.txt` |

Output: `output_rev7_0bbfd55.txt` (rev7), `output_rev7_1.txt` (rev7.1) dan `output_rev7_2.txt` (rev7.2, putaran ketujuh).
