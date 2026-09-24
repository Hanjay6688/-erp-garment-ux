# AZ rev2.1: gerakan yang dibalik (uji logika stub; T1_FAMILY, bukan bukti rilis)

Temuan native: kasus `AY:PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER`, run AY T1 35998326956 pada `769abfe`.
- Invoice terlambat dengan harga lebih rendah untuk bahan yang sebagian pengeluaran potongnya dibatalkan sebelum jahit membuat MATERIAL_INVENTORY −10,50 antara hari potong dan hari pembatalan.
- Engine tutup buku menandainya `GL_INVENTORY_NEGATIVE_ASOF` CRITICAL.
- Penyebab: mesin biaya (`_recalculate_material_cost_core`) memutar ulang riwayat tanpa gerakan yang dibalik dan tanpa pembaliknya, dan revaluasi gerakan yang dibalik ditargetkan nol. Unit yang secara fisik ada di WIP tetap tercatat keluar pada harga lama, sementara stok asalnya sudah dinilai ulang.

Perbaikan (`sync_material_cost_revaluation`, AZ rev2.1):
- Gerakan yang dibalik dinilai ulang dengan biaya yang akan diberikan pemutaran ulang: rata-rata sebelum gerakan itu untuk gerakan keluar, atau biaya pengeluaran potongnya untuk retur potong. Nilai ini dicatat pada hari gerakan itu.
- Setiap pembalik mengambilnya kembali pada hari pembalik. State dicatat per gerakan, dan hasil bersihnya nol sesudah pembalikan.
- Bila kedua kaki jatuh pada hari yang sama (E tertutup, recost tanpa invoice terlambat), nilai interim gerakan asal dipertahankan dan pembaliknya menetralkan pasangan pada hari itu, sama dengan posting tunggal sebelumnya. Nilai interim tidak dinolkan, jadi invoice terbuka berikutnya hanya menambah selisihnya (tidak ada interim ganda).
- Penghapusan bahan (item keluar penyesuaian bahan, termasuk pemakaian kain kantong sejak audit GPT AB-01) yang dibalik diperlakukan sama, melawan akun penghapusan (OTHER_EXPENSE). Event dan state-nya dicatat pada gerakan pembalik supaya berada di luar buku kumulatif dokumen penyesuaian.

`run.sh` memasang fungsi apa adanya dari `supabase/dev/cp6_az_t1_family.sql` ke stub `schema.sql`, lalu menjalankan `scenario.sql`, `writeoff.sql` dan `pocket.sql` pada tiga mode, serta `sequence.sql`. Hasilnya ada di `output_rev21.txt`:
- **Terbuka:** M1 +7,00 dan M2 +10,50 pada hari potong (d−2), pembalik −10,50 hari ini. Sync kedua tidak menambah event.
- **Tertutup:** M1 +7,00 pada E. M2 dan pembaliknya 0.
- **Tanpa invoice:** M1 +7,00 hari ini. M2 dan pembaliknya 0.
- **Penghapusan bahan yang dibalik, terbuka:** +17,50 pada hari penyesuaian dan −17,50 hari ini (persediaan melawan OTHER_EXPENSE). Tanpa kaki ini persediaan −17,50 di antara kedua hari. Tertutup dan tanpa invoice: tidak ada.
- **Urutan** invoice terbuka → recost tanpa invoice → invoice terbuka lagi dengan rata-rata 8,00: recost tanpa invoice tidak menambah apa pun untuk M2 dan pembaliknya; invoice kedua hanya menambah M2 +1,50 / pembalik −1,50 (dan M1 +1,00).

Fixture native: `AZ:PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER` dan `AZ:WRITE_OFF_REVERSED_THEN_LATE_INVOICE_LOWER`.
- **Pemakaian kain kantong yang dibalik (`pocket.sql`, audit GPT AB-01), terbuka:** sama dengan penghapusan bahan, +17,50 / −17,50. Sebelum perbaikan, pemakaian kantong dikecualikan. Reproduksi native pada AZ yang belum diubah (run 36009699973, `b746153`): persediaan −17,50 pada 22–23 Sep dengan 0 unit di tangan, dan AW CRITICAL.
