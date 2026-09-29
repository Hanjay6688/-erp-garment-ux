# Checkpoint keluarga 2 — P03–P04

**29 September independent update: F02 HOLD.** The historical writer passes below remain valid within their tests, but the combined independent handoff found F02-01 (cancelled BS after source reversal) and F02-02/X06 (unbound matching labels). See [current repair handoff](F02_FIX_HANDOFF.md). The repair is writer-qualified on `ee86998` with53 cases plus one smoke; no independent closure is claimed.

**Untuk Sol / auditor independen.** Implementasi dengan batas di bawah lulus tes writer. Independent acceptance **BELUM**; keluarga belum diterima auditor. CP6 tetap CLOSED_CONTRACT_SCOPE, R10 tetap P11, `production_go=false`.

## Kode dan bukti yang dikunci

| Bagian | Kandidat dan hasil |
|---|---|
| P03 status produksi dan identitas | `c56c3bb9b84a8d24e8dbe7a3b22bbd98b4d39111`; [run 36509688817](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36509688817): 10 database + 4 race + 1 Auth/HTTP PASS; smoke terpisah |
| P04 gabungan akhir | `17e85404c9c5f088875099d7875be6342ca6b266`, tree `2f5ab50a24ef82b84a48364994a5927bb39149e3`; [run 36515586854](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36515586854): **17 kernel + 17 sumber transaksi + 3 race + 2 Auth/HTTP = 39 PASS**, satu smoke berulang tidak dihitung lagi |
| Aplikasi pada kode P04 | [36515590677](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36515590677) dan [36515586861](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36515586861) SUCCESS. Ini regresi/build/browser cangkang, bukan bukti UI P04 tersambung |
| Bundle perkembangan | SHA256 `b50edbb4f45c6e1282a3744096c5a74fbc2487a1442211307ac9d1ab45eb76cc`; bukan paket rilis CP7 |

[Receipt P03](evidence/p03-policy/VERIFICATION.json), [receipt P04 akhir](evidence/p04-production/VERIFICATION.json), [laporan asli P04](evidence/p04-production/CP7_P04_KERNEL.json.gz), [peta sumber aktif](source-map.json). Semua memiliki hash sumber/test/workflow. P03 tidak diklaim diuji ulang seluruhnya oleh run P04; modulnya tidak berubah dan hash dapat dicocokkan. Commit dokumentasi checkpoint tidak memindahkan hasil tes ke kode berbeda.

## Yang sudah dibuat dan dibuktikan

- **P03:** status ACTIVE/PAUSED/STOPPED terpisah dari harga dan izin jual SKU. Perubahan anggota membatalkan hasil review anggota lama; perubahan harga saja tidak. Bulk command atomik, revisi bigint tepat, urutan lock konsisten, stale member dan pencabutan akses saat antre/replay ditolak. Identitas dokumen lama disimpan; restatement saat ini ditampilkan terpisah. Tanggal review terlewat tidak mengaktifkan produksi otomatis.
- **P04:** satu pool input per sumber asli, ukuran tepat dan kepemilikan. Rework/rewash/redispatch bukan input tambahan. Negative prefix, ukuran silang dan asal ganda ditolak; sumber ambigu tetap UNKNOWN. Parent group adalah kontrol, bukan supply tambahan.
- Capture cutting, opening dan BS tanpa PO memakai **satu pernyataan MVCC dan satu waktu capture**, setelah request lock. Hasil per aktor immutable; request duplikat satu run; perubahan sumber membuat stale tanpa menulis ulang arsip. Ops tidak menerima kolom uang.
- Actual posting cutting/pickup/sewing/laundry/QC memberi **100 input = 80 WIP + 15 FG + 5 BS**. Cucian tanpa harga tetap UNKNOWN pada predicate resmi dan valuasi publik. Partial rework tetap WIP; completion 3 GOOD + 2 BS memberi 100 = 80 + 18 + 2.
- Return-unprocessed → redispatch → dua retry tidak menggandakan PCS. MISSING/STUCK menahan kuantitas sekali; rejection mengembalikan klasifikasi outstanding, bukan FG. HOLD/release/scrap/reversal menjaga pool. BS case punya slice sendiri agar tidak mengunci seluruh receipt bersama.
- Opening 8 → pickup → 3 FG → 2 BS → reverse FG, claim/recovery/write-off, serta non-PO BS 5 → 3 FG + 2 BS → reversal dibuktikan lewat writer ERP yang diterima. Gabungan cutting 100 + opening 8 memberi **108 = 88 WIP + 15 FG + 5 BS**.
- Race cross-origin hanya menangkap pasangan utuh (cut receipt 29, opening 8) atau (30,9), 12 capture saat writer aktif. Race lain membuktikan header/size receipt konsisten dan satu run untuk request sama. Real Auth/HTTP memeriksa pemilik/aktor lain/anon/pencabutan token yang sama.
- Kernel matching memisahkan tujuan terkonfirmasi dari referensi tarif SKU, hard mismatch dari metadata opsional, dan edge berbeda meskipun total sama. Yield eksplisit **100 input / 100 eligible / 90 projected GOOD** menolak output 91 maupun input 101. Loss perkiraan tidak diposting sebagai BS. Shared input 60 boleh 42+18, menolak 42+30. Kalender hanya menghitung pekerjaan tersisa dan jam kerja terpilih; tanpa kalender/yield tetap UNKNOWN.
- Instalasi di clone sementara, restore batas CP6, cleanup dan advisor delta lulus. Tidak ada pemasangan hosted atau klaim zero-finding universal.

## Batas dan kewajiban yang tetap terbuka

| Oracle/charter | Bukti keluarga ini | Pemilik lanjutan |
|---|---|---|
| O15 | Conservation kernel + transaksi asli PASS | Full lifecycle browser P18 |
| E02 | Seam cutting/opening/BS/rework/rewash/claims PASS | Rangkaian menyeluruh P18 |
| E23/X03, O17 | Status/membership/bulk/auth PASS | STOP target100−FG10−WIP20 = gap70, start_new0 dan UI: P06/P08/P14 |
| X01 | Identitas tercatat versus current membership PASS | Konsumsi planning/report, bukan klaim semua konversi diuji ulang |
| X06/X08 | Edge berbeda dan batas yield/input/output kernel PASS | Join target/policy sumber otoritatif dalam satu capture P06/P07 |
| O04 | Shared source 60, 42+18; kekurangan B12 | Demand bertanggal dan seluruh scenario P06/P08 |
| O03/O05 | Bukan closure dari capture WIP | Dated netting: early gap tetap walau supply datang kemudian; target100−FG10−directed60 = base gap30: P06 |
| M07 | Remaining calendar/UNKNOWN kernel PASS | Kebijakan berversi, stale, kapasitas dan tanggal demand P06/P07 |

Scope dipilih eksplisit, maksimal 50 origin dan 2.000 baris per domain. Ini CURRENT knowledge, belum arbitrary AS_KNOWN atau skala global P19. FG di sini **production disposition**, bukan on-hand setelah penjualan/konversi; P10 wajib memakai ledger stok. Sewing group-only tidak dibagi proporsional menjadi ukuran/batch palsu. Klaim header ambigu menghasilkan UNKNOWN. Tidak ada kalender, tarif SKU atau yield default yang diciptakan.

Kernels matching/yield/ETA tetap private. Belum ada planner lengkap atau browser P04 tersambung. Planner kelak harus menggabungkan source, status, target dan asumsi secara atomik; **dilarang menjumlahkan run P02/P03/P04 yang capture-nya terpisah**. Otorisasi P03/P04 bukan pembuktian seluruh role/browser ERP. Paket gabungan, T2/P20/P21 dan izin produksi tetap terpisah.

**Carry ke F03/P13:** jalur failed-wash yang diuji memakai tarif vendor/process 5.00. Backend diterima menolak failed-wash tanpa effective rate. Cocokkan jalur khusus itu dengan keputusan owner boleh harga menyusul; jangan mengklaim sudah qualified. Laundry biasa tanpa harga sudah PASS UNKNOWN, bukan Rp0.

## Kegagalan dan perbaikan yang tidak disembunyikan

1. Adapter pertama: alias SQL `y` berbenturan dengan variabel PL/pgSQL. **Bug produk adapter**, diganti alias; sumber kasus sebelum gate tidak dijalankan. Receipt `evidence/p04-kernel/ADAPTER_FAILURE_1.json`.
2. Assertion internal `actual_cost IS NULL` tidak cocok kontrak CP6. Oracle diperbaiki ke predicate unknown resmi + valuasi publik UNKNOWN, bukan menerima KNOWN(0). Receipt failure 2 tetap ada.
3. Fixture failed-wash tidak menyiapkan vendor rate. Rate 5.00 dibuat lewat master yang diterima; batas kasus dicatat seperti di atas. Receipt failure 3 tetap ada.
4. QC seluruh 20 PCS salah dideklarasikan PARTIAL_SELECTION; fixture memakai ALL_READY, guard dan oracle tidak dilonggarkan. Receipt failure 4 tetap ada.
5. Pemeriksaan silang charter menemukan batas physical input belum cukup untuk yield 90%. Kernel yield eksplisit ditambahkan dan X08 diuji pada kandidat akhir. Tidak mengklaim kandidat sebelumnya sudah memenuhi X08.

## Cara audit dan kriteria penyerahan

Kunci oracle dari `framework-v2` terlebih dahulu. Periksa kandidat SHA, hash bundle, ACL principal dan source adapter. Workflow `.github/workflows/cp7-p03-identity.yml` / `cp7-p04-wip.yml` menjalankan probe Python dengan PostgreSQL/Supabase sementara; log memuat planned cases, actual dan restore. Gunakan oracle dan eksekusi sendiri, jangan menerima hanya karena angka writer hijau.

Fokus retest: conservation saat reversal/dependent consumption, satu-snapshot lintas origin, larangan alias input, stale/current auth/replay, UNKNOWN tanpa nol palsu, claim/rework double count, yield rasional dekat bilangan bulat, filter/shared capacity dan leak uang. Laporkan ACCEPT/HOLD/INCOMPLETE **dengan cakupan**, expected/actual, SHA dan bukti. Temuan material pada dependency wajib diperbaiki sebelum dipakai.

Writer melanjutkan keluarga 3 P09–P13 sesuai instruksi owner. Checkpoint ini siap diteruskan owner kepada Sol; belum dikirim sebagai pesan ke pihak lain dan belum ada penerimaan auditor yang diklaim.
