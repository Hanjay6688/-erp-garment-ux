# BE / ALL-C04 — rancangan adapter cutover kain kantong

Status: desain writer, implementasi belum selesai. Bukan perubahan kontrak atau oracle auditor.

Dasar: M:466–511 / P:406–439, konsep dan errata auditor pada audit `9aa7c76`. Sumber native: AP `pocket_period_*`, `initial_import_source_value_v1`, `refresh_initial_import_fg_cost_v1`; BD adalah predecessor. Tidak ada akses hosted.

## Fakta yang harus dipisah

1. Sisa kain yang benar-benar di gudang: impor MATERIAL_ROLL / saldo bahan existing.
2. Kain yang telah keluar sebelum cutover: rincian dokumen/lembar sumber dan baris, tanggal fisik, bahan/qty/nilai. Tidak membuat gerakan stok baru.
3. Bagian yang sudah dialokasikan: referensi saja; nilai sudah berada di opening WIP/FG/COGS. Tidak ikut pool baru, tidak dibukukan lagi.
4. Bagian yang belum dialokasikan: sumber expense opening yang eksplisit, dipakai satu kali pada pengesahan periode. Pengesahan mereklasifikasi nilai tanpa pengeluaran kain kedua.
5. Denominator hasil SELESAI_DIJAHIT historis yang terbukti, termasuk Afui, digabung dengan event native sesudah cutover. Data historis tetap bertipe sumber impor; jangan membuat work completion/sewing event palsu.

## Integrasi yang direncanakan

- Dua entity impor dengan validation/apply/revision/workspace: OPENING_POCKET_USAGE dan OPENING_POCKET_SEWING; guard identitas lintas batch berbasis dokumen + baris, bukan request key saja. Draft boleh diedit lewat alur impor yang sah; posted fact immutable.
- Pemakaian historis menyatakan ALLOCATED / UNALLOCATED, provenance, cutoff, qty/nilai. Nilai yang sudah termasuk opening tidak menjadi expense tambahan. Pool unallocated harus direkonsiliasi dengan total kontrolnya sendiri dan tidak diduplikasi dalam saldo pembuka lain.
- Denominator historis wajib rujukan lembar hasil + baris, waktu < cutover, mandor, qty, dan target terbukti: opening WIP/BS, opening FG, atau hasil yang sudah terjual sebelum cutover (COGS). Tanpa basis pembagian lengkap, posting alokasi ditolak; tidak mengarang denominator.
- Perluasan tabel pocket_period_sources/destinations memakai sumber alternatif FK impor yang eksplisit (exactly one native/historical); bukan insert adjustment/event palsu. Primary/unique lama disesuaikan dan dibawa ke capsule rollback.
- Manifest menyatukan native dan historis, menjaga urutan deterministik dan revision. ALLOCATED historis tidak ikut biaya pool baru. Native overlap/inverse/denominator locks tetap berlaku; impor sumber historis ke periode aktif juga ditolak.
- Target opening WIP: append event biaya pada opening item; `initial_import_source_value_v1` membaca tambahan itu. Rebuild/propagate/sync native meneruskan biaya ke hasil/BS/penjualan kemudian. Jangan sekaligus menambah sumber yang sama pada pocket_lot_cost native.
- Target opening FG: `refresh_initial_import_fg_cost_v1` membuat versi HPP; reclass offset OPENING_EQUITY ke expense pool. Non-PO conversion BE harus ikut recost. Histori harga/qty opening tidak ditimpa.
- COGS historis: jurnal koreksi biaya bersumber alokasi dan provenance hasil terjual, tanpa menciptakan penjualan/AR/kas fiktif.
- Cancel alokasi membalik reklasifikasi/versi biaya, tidak mutasi stok. Koreksi nilai sumber memakai event dan tanggal ekonomi; periode tertutup memakai posting canonical. Bila receipt supplier belum ditagih menjadi asal biaya, qty consumed harus masuk rekonsiliasi receipt dan invoice recost harus tersambung; jangan diam-diam mengaku sudah didukung bila belum.
- Detector pocket membership, jumlah/biaya, GL dan HPP wajib mencakup kedua jenis sumber. Tidak ada pengecualian STALE/skip detector.

## Expected numerik utama (dari kontrak)

10 PCS denominator: 5 WIP, 3 FG tersedia, 2 terjual. Biaya 11,25 → WIP5,62 / FG3,38 / COGS2,25. Setelah koreksi menjadi15,00 → 7,50 / 4,50 / 3,00. Seluruh sen dialokasikan; posisi deterministic dan residual WIP mengikuti native target, bukan pembulatan terpisah yang membuat11,26. Kain sisa tidak berubah oleh allocate/recost/cancel.

## Gate writer yang masih harus dikerjakan

Impor → preview → post → lanjut WIP/sale/retur/konversi → correction → cancel; replay dan duplicate lintas batch; sumber/denominator tidak lengkap; ALLOCATED tidak double; mandor khusus termasuk; period overlap/closed/as-of; race; HTTP Auth; UI impor dan periode; T2; package BE + capsule structural rollback. Jangan tandai C04 selesai dari keberadaan berkas desain ini.
