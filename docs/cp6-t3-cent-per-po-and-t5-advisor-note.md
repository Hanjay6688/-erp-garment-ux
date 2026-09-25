# CP6: penjelasan sen per PO pada stok bertumpuk (handoff T3) dan catatan advisor paket rilis (handoff T5)

Penulis: writer. Label `WRITER_EXPLANATION`, bukan bukti independen. CP6 tetap HOLD, `audit_complete=false`,
`production_go=false`. Dokumen ini tidak mengubah hasil beku mana pun: dua `COUNTEREXAMPLE` Fable (xaudit_8, run
36123155393) dan tiga `PASS` GPT (run 36132246344) tetap seperti tercatat.

## T3. Sen per PO pada stok bertumpuk

### Kasus

Kasus Fable `XA8:W8_THREE_RECEIPTS_INVOICE_UP`:

- Tiga penerimaan bahan yang sama, masing-masing 1 unit, semuanya pada hari d pukul 10.00, dalam tiga dokumen terpisah.
- Harga taksiran 10,00. Setelah invoice, harganya 10,005.
- Pada hari d+1, tiga potong untuk tiga PO dilakukan pukul 08.00, 09.00, dan 10.00. Saat itu stok masih bercampur dari tiga dokumen.
- Invoice datang pada hari d+2.

Hasil:

- WIP per PO: 10,02 / 10,00 / 10,01.
- Total 30,03, bahan 0, tidak ada nilai harian negatif.

Pasangannya, `XA8:W8_THREE_RECEIPTS_DIRECT_DOWN` (10,01 lalu dikoreksi ke 10,004), menghasilkan 9,99 / 10,01 / 10,00 dengan total 30,00.

### Deterministik

Kedua kasus dijalankan ulang secara lokal (PG16 lokal, `LOCAL_PG16_DEV`, bukan bukti) dengan skenario Fable apa adanya (`audit/scenarios/xaudit_8.py`, fungsi `multi_receipt`, n=3). Pengujian memakai dua isi BA:

- isi sebelum perbaikan T4;
- isi sesudah perbaikan T4 (commit 4cd2171).

Pada keduanya hasil per PO **identik** dengan run Fable, dan jejak gerakan di bawah juga identik. Perbaikan T4 hanya menyentuh dokumen multi-bahan dan penilaian pertama sebuah gerakan, dan tidak ada yang mengubah kasus ini.

### Jejak `erp.sync_material_cost_revaluation` (kasus UP, harga akhir 10,005)

Aturan BA (`scripts/cp6_ba_build.py`, blok "BA W8"; di `supabase/dev/cp6_ba_t1_family.sql` pada fungsi yang sama) terdiri dari dua bagian:

- **Nilai sebuah pemakaian** = perubahan nilai stok yang sudah dibulatkan, yaitu `round(stok_sesudah × rata2) − round(stok_sebelum × rata2)`. Rata-rata bergerak per bahan (M:4735, M:5021).
- **Selisih sen dokumen** = total dokumen dibulatkan per dokumen (M:835) dikurangi perubahan nilai rata-rata yang diterima dari dokumen itu. Selisih ini dibawa ke **pemakaian berikutnya**, sehingga jumlah semua pemakaian sama dengan jumlah dokumen dan stok nol bernilai nol.

| Langkah | Stok | Nilai stok dibulatkan | Perubahan | Dokumen dibulatkan | Selisih dokumen |
|---|---:|---:|---:|---:|---:|
| Penerimaan 1 | 0 → 1 | 0,00 → 10,01 | +10,01 | 10,01 | 0,00 |
| Penerimaan 2 | 1 → 2 | 10,01 → 20,01 | +10,00 | 10,01 | +0,01 |
| Penerimaan 3 | 2 → 3 | 20,01 → 30,02 | +10,01 | 10,01 | 0,00 |
| Potong 08.00 (PO 1) | 3 → 2 | 30,02 → 20,01 | −10,01 | — | +0,01 dibawa ke sini |
| Potong 09.00 (PO 2) | 2 → 1 | 20,01 → 10,01 | −10,00 | — | — |
| Potong 10.00 (PO 3) | 1 → 0 | 10,01 → 0,00 | −10,01 | — | — |

Hasilnya:

- PO 1 = 10,01 + 0,01 = **10,02**, PO 2 = **10,00**, PO 3 = **10,01**. Jumlahnya **30,03**, sama dengan tiga dokumen yang masing-masing dibulatkan (3 × 10,01).
- Nilai bahan kembali 0,00 tepat saat stok habis.
- Koreksi untuk ketiga PO bertanggal hari invoice (aturan AZ: tanggal yang lebih akhir antara invoice dan pemakaian, pada periode terbuka).

Kasus DOWN (10,004): nilai stok berturut-turut 10,00 / 20,01 / 30,01. Dokumen 3 × 10,00 = 30,00, sehingga selisih −0,01 jatuh ke pemakaian pertama. Hasilnya 9,99 / 10,01 / 10,00.

Kasus bertahap GPT (stok nol di antara penerimaan) menghasilkan 10,01 × 3. Alasannya, setiap pemakaian hanya menghabiskan satu dokumen. Tidak ada rata-rata lintas dokumen dan tidak ada selisih yang pindah.

### Apa yang dijamin kontrak, dan apa yang belum

- **Dijamin dan terbukti:** total nilai, nilai per tanggal, dan jejak sumber (M:6632), nilai stok nol saat stok habis, dan pembulatan kewajiban per dokumen (M:835).
- **Tidak diatur kontrak:** apakah **setiap PO** harus memikul persis sen dokumen yang "dipakainya". Pada rata-rata bergerak, unit di stok campuran tidak punya identitas dokumen. Karena itu, pembagian sen per PO bergantung pada urutan pemakaian dan paritas pembulatan stok. M:485 hanya membahas pembagian satu biaya kain kantong. Klasifikasi auditor tetap **UNVERIFIED P3**, bukan blocker gate.

### Permintaan keputusan owner (satu pertanyaan, tidak menghambat gate)

Pada stok bahan campuran dari beberapa nota, bolehkah HPP per PO berbeda paling banyak 1 sen per dokumen dari notanya, selama total, tanggal, dan jejaknya tepat?

- **A. Boleh (usulan writer, tanpa perubahan kode).** Aturan sekarang tetap: rata-rata bergerak, dan selisih sen dokumen dibawa ke pemakaian berikutnya.
- **B. Tidak boleh.** Setiap pemakaian dinilai `round(qty × rata2)`, dan sisa sen masuk ke pemakaian yang menghabiskan stok. Pada kasus ini hasilnya 10,01 × 3, tetapi PO terakhir tetap bisa berbeda 1 sen pada pola lain. Satu-satunya cara agar setiap PO selalu sama dengan notanya adalah penilaian per roll (identifikasi khusus). Itu mengganti metode biaya kontrak (rata-rata bergerak) dan perlu CR.

Sampai owner memilih, yang berlaku adalah A (keadaan sekarang). Tidak ada kode yang diubah untuk T3.

## T5. Catatan rilis: advisor keamanan INFO `rls_enabled_no_policy` (disengaja)

Run T3 install terakhir (c793d51, job 108076155383) memasang paket 25 berkas (AC..BA) di baseline yang setara hosted. Hasil advisor: sebelum 73, sesudah 129, bertambah **56**, dihapus 0. Semua tambahan berjenis `INFO rls_enabled_no_policy` pada schema `erp`:

- 26 tabel `cp6_v2620*_rollback_capsule` (termasuk `relation_rollback_capsule` AC): salinan rollback.
- 14 tabel `initial_import_*`: sumber dan riwayat impor saldo awal.
- 6 tabel `pocket_*`: periode, event, sumber, tujuan, bahan, dan pemakaian kain kantong.
- `po_hpp_gl_lot_state_v1`, `po_hpp_gl_material_state_v1`.
- `accounting_close_filings_v1`, `bs_case_manual_origins_v1`, `fg_unsourced_receipts_v1`, `fg_unsourced_repair_wages_v1`.
- `laundry_rate_owner_estimates_v1`, `invoice_recost_execution_context`, `pocket_fabric_execution_context`, `product_identity_mutation_context_v1`.

Mengapa ini disengaja (fail-closed, bukan celah):

- Setiap tabel itu `ENABLE ROW LEVEL SECURITY` **tanpa policy**, dan semua hak dicabut dari `public`, `anon`, `authenticated`, dan `service_role`. Tanpa policy, RLS menolak semua baris untuk peran klien.
- Aksesnya hanya lewat fungsi `SECURITY DEFINER` yang memeriksa peran di dalamnya (`erp.require_internal()` atau pemeriksaan peran pada facade publik).
- Menambah policy justru akan membuka jalur baca atau tulis langsung.

Paket 26 berkas (dengan BB) menambah 16 tabel `bb_*` dan satu rollback capsule BB dengan pola yang sama: RLS aktif dan semua hak dicabut (lihat `scripts/cp6_bb_objects_*.sql`). Angka pastinya diambil dari run install paket 26 berkas berikutnya. Gate advisor paket (`scripts/cp6_t3_package_run.py`, `ACCEPTED_NEW_ADVISOR`) tetap menolak tambahan apa pun selain `INFO rls_enabled_no_policy` pada schema `erp`.
