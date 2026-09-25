# Lampiran C6 (D06) — Daftar acceptance per fitur aksesori dan laundry

**Status: USULAN WRITER, 25 September 2026.** Lampiran ini belum ditinjau auditor dan belum disahkan owner. Addendum
induknya adalah `ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` (bagian 8).

Batas pengetahuan writer: writer tidak memegang teks M:1691–1699, M:1753–1757, dan M:4448–4479. Pembagian di bawah
disusun dari:
- kandidat (kode dan migration di branch ini);
- handoff writer (`docs/cp6-au-r1-handoff.md`);
- dokumen auditor (`AUDIT_WRITER_HANDOFF_CP6.md` bagian D, dan `OWNER_DECISIONS_CP6_DRAFT.md` D06).

**Auditor diminta mencocokkan setiap baris dengan ketiga rentang kontrak itu.** Baris yang tidak cocok dipindah atau
dihapus.

Arti kolom "Kelompok":
- **BASELINE** — kewajiban CP6. Harus lulus sebelum GATE-16 dapat ACCEPT.
- **CR-MASUK** — CR yang sudah ada di kandidat. Owner memilih salah satu: diuji tuntas di CP6, atau kandidat direvisi
  secara eksplisit.
- **CR-TUNDA** — CR yang belum ada di kandidat. Dikerjakan sebagai kelanjutan sebelum consumer CP7 yang memerlukannya.
- **CP7-DEP** — dibutuhkan oleh consumer CP7.

## Aksesori

| ID | Fitur | Kelompok (usulan) | Bukti penerimaan yang sudah ada | Catatan |
|---|---|---|---|---|
| ACC-01 | Pengeluaran aksesori ke mandor per PCS utuh, harga eceran manual yang valid (7 PCS tetap 7) | BASELINE (M:44, M:1023, M:1066–1071) | Oracle auditor "aksesori 7 PCS eceran persis M:94" lulus (bagian D); workspace/facade `erp_get_accessory_issue_workspace_v1` dan `erp_save_accessory_issue_action_v1` | Tidak perlu memilih prorata/eceran lagi (sudah diputus kontrak) |
| ACC-02 | Hak reimbursement aksesori per lot FG (akrual, BOM, pilihan default dari hak yang belum dibayar) | BASELINE (warisan CP5 19a/19b) | Tes batas CP5 (`check-cp5-boundary.mjs`), DOM BS Resolution "defaults only server-proven unpaid items…" | — |
| ACC-03 | Recost HPP aksesori setelah koreksi harga bahan (`refresh_accessory_hpp_after_material_recost`, jurnal `ACCESSORY_HPP_RECOST`) | BASELINE (kebenaran nilai) | Probe T1 AZ rev2 | Dibatalkan bersama akrualnya (AZ rev2) |
| ACC-04 | Pemakaian aksesori internal dan retur aksesori | CR-TUNDA (usulan) | — | Tercatat "belum ditinjau" di handoff writer §10 |

## Laundry

| ID | Fitur | Kelompok (usulan) | Bukti penerimaan yang sudah ada | Catatan |
|---|---|---|---|---|
| LAU-01 | Kirim/terima laundry, QC, FG authoritative | BASELINE | T2 (AR/regresi), T3 alur browser | Migration v2.6.20 |
| LAU-02 | Claim laundry STUCK/MISSING/DAMAGE dan kompensasi | BASELINE (warisan CP5) | Tes batas CP5; DOM claim; A5 (selector semua sumber yang masih bisa diklaim) | BA A5 |
| LAU-03 | Identitas produk BS laundry pada penerimaan fisik | BASELINE | Probe AV (CUTOFF:LAUNDRY_BS) | — |
| LAU-04 | Tarif laundry kosong: estimasi owner dan blokir tutup buku (`LAUNDRY_PRICE_UNKNOWN`, `erp_set_laundry_rate_owner_estimate_v1`) | BASELINE (keputusan §14 no. 3; LAU-DEC04) | Probe T1 AW (P-02) | Blokir sesuai tanggal |
| LAU-05 | Paket/komponen laundry dan invoice laundry susulan | CR-TUNDA (usulan) | — | Tercatat "belum ditinjau" di handoff writer §10 |
| LAU-06 | Celup ulang BS menjadi warna/SKU baru | CR-TUNDA | — | Owner: CR prioritas rendah, successor tersendiri (handoff writer, keputusan 2b); biaya celup nol yang diketahui ("gratis") |
| LAU-07 | Tarif/vendor/retur/servis laundry yang belum diputus | CR-TUNDA; hanya menahan fitur terkait (D06) | — | — |

## Yang diminta

1. **Auditor:** mencocokkan setiap baris dengan M:1691–1699, M:1753–1757, dan M:4448–4479, lalu menambah fitur yang
   terlewat, terutama butir CR yang sudah masuk kandidat (CR-MASUK). Writer tidak menemukan butir CR-MASUK yang pasti
   tanpa teks kontrak.
2. **Owner:** memilih untuk setiap baris CR-MASUK: diuji tuntas di CP6, atau kandidat direvisi. Owner juga mengesahkan
   lampiran ini lewat bagian 9 addendum induk.
