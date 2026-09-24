# AZ rev2: uji logika stub (T1_FAMILY, bukan bukti rilis)

Fungsi AZ rev2 diambil apa adanya dari `supabase/dev/cp6_az_t1_family.sql` dan dijalankan pada skema stub minimal di PostgreSQL
lokal sekali pakai. Tiap fungsi diuji pada tiga mode: E terbuka, E tertutup, dan tanpa invoice. Hasilnya ada di `output_rev2.txt`.

| Skenario | Fungsi | Harapan |
| --- | --- | --- |
| nonpo | `sync_non_po_product_hpp_to_gl_v2620f` | E terbuka: lainnya −2 (21 Sep), HPP −3 (22 Sep), HPP +1 (23 Sep); tertutup/tanpa invoice: satu jurnal |
| bsv | `sync_initial_import_bs_value_v1` | E terbuka: −2 pada hari 2 pcs keluar, −3 pada hari 3 pcs keluar; tertutup: satu jurnal pada E |
| acc | `refresh_accessory_hpp_after_material_recost` | WIP +2 / selisih penggantian −2 pada hari lot (terbuka), E (tertutup), hari ini (tanpa invoice) |
| pocket | `guard_pocket_period_v1` | RECOST pada akhir periode (terbuka), E (tertutup), hari ini (tanpa invoice) |

Uji native di CI: fixture `AZ:BATCH_PARTNER_PO` (PO pasangan batch) di `scripts/cp6_az_probe.py`.
