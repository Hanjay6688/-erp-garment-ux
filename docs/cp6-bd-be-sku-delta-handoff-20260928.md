# Audit delta BD–BE–SKU setelah revisi, 28 September 2026

Untuk writer utama. CP6 tetap HOLD. Dokumen ini hanya melaporkan jalur yang tidak tercakup oleh hasil BF/BE writer yang sudah ada. Audit pesaing tidak dibaca, dan enam temuan SR pada PR #29 tidak diulang.

## Identitas dan batas bukti

- Kandidat: branch claude/new-session-deapao, sesudah kandidat produk BE 231d29064b8ccf7221ad004cd8ef0017598242fc. Ketika diverifikasi, branch telah menambah perbaikan FREE/WAIVED BF; tiga fungsi yang menjadi dasar delta di bawah tetap sama persis dengan BF awal.
- Blob source yang diperiksa: router BF f8c26fd141991d7d36ec8ebec9cd88500f4756c4, work BF 63235b69ad802c0f2798db1b51b45bd45c470f1b, laundry BF 0ce08738e8babaa3191c39ff183a860db9b3dfc8, master BF bbbba848f407d366ee59bca8f140b09a818ab4f7, SQL gabungan BF terbaru 3bcdcddb95e9fa2b768e8a3dab1826fbc7b10556.
- Uji auditor yang dijalankan: tiga pemeriksaan jalur source pada source SQL gabungan dan fungsi komponennya; 3/3 mendukung prediksi di bawah. Ini adalah bukti alur kode, bukan eksekusi PostgreSQL/HTTP. Lingkungan audit tidak memiliki Postgres disposable atau cabang database BF; database live tidak dipakai sebagai fixture.
- Bukti writer yang sengaja dilewati: BF temporal move tanpa stok, BF dua SKU satu wave dengan semua harga SKU terisi, BD DEC05 tanpa wave BF, BE 63 native/race/HTTP/browser dan enam SR pada PR #29. Kasus baru di bawah menggabungkan kondisi yang tidak muncul bersamaan pada bukti tersebut.

## D-01 — Wave SKU tanpa override melewati tarif khusus BD dan aturan REFUSE

**Prioritas tinggi; prediksi dari source, menunggu native.** Ketika satu ukuran memiliki binding BF, cabang RATE pada bd_compute_pricing_v1 langsung memanggil bf_laundry_rate_v1(PROCESS). Fungsi BF ini mengembalikan tarif dasar vendor/proses bila SKU tidak memiliki override. Cabang bd_scoped_rate_at_v1 dan pemeriksaan LAU_DEC05 fallback REFUSE hanya berjalan bila ukuran *tidak* memiliki binding BF. Label charge bahkan menyebut Tarif bersama SKU pada kasus fallback tersebut.

Sumber: [pricing BF, baris 40–62](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/supabase/dev/cp6_bf_t1_family.sql) (cari definisi bd_compute_pricing_v1); [fallback BF, baris 9–28](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/scripts/cp6_bf_objects_laundry.sql#L9-L28).

**Fixture native minimum:** vendor V/proses P punya tarif dasar 6,00; LAU_DEC05 mengizinkan MODEL_SIZE, tarif khusus model M/ukuran 31 sebesar 17,00, fallback REFUSE. Buat SKU A beranggota ukuran 31 dengan laundry_rates kosong; ikat ukuran 31 pada wave W ke A. Kirim 2 PCS lewat POST_PRICED_DELIVERY dengan mode RATE.

**Oracle:** tarif khusus 17,00 menghasilkan biaya 34,00 dan provenance scoped. Apabila tarif khusus dihapus dengan fallback REFUSE, posting wajib menolak BD_SCOPED_RATE_MISSING. Source saat ini memilih tarif dasar 6,00, biaya 12,00 pada kedua varian; walaupun SKU tidak mengatur PROCESS, charge berlabel tarif SKU. Bandingkan baris charge, alokasi penerimaan, HPP, dan accrual; rollback seluruh fixture.

**Saran:** kembalikan “tidak ada override PROCESS” secara terpisah dari “ada override SKU”; jalankan pemilihan scoped BD dan fallback policy pada kasus pertama. Hanya snapshot override sungguhan yang membawa versi BF. Tambahkan dua varian di atas ke tes native BF_REG_BD, termasuk tarif scoped yang aktif dan fallback REFUSE.

## D-02 — Wave yang belum dipakai tetap menunjuk SKU lama setelah ukuran dipindah

**Prioritas tinggi; prediksi dari source, menunggu native.** BIND_WAVE memeriksa keanggotaan pada statement_timestamp ketika binding dibuat. SAVE_GROUPS membolehkan perpindahan atomik ukuran setelah itu bila belum ada snapshot kerja/charge/rework, tanpa merevisi atau membatalkan bf_wave_skus_v1. Pada penggunaan pertama setelah waktu perpindahan, bf_laundry_rate_v1 memilih versi berdasarkan SKU lama yang tersimpan di wave, tetapi tidak memeriksa apakah ukuran masih anggota versi tersebut. bf_ensure_work_v1 juga memilih snapshot berdasarkan SKU binding dan waktu kerja, bukan keanggotaan ukuran.

Sumber: [validasi dan penyimpanan binding](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/scripts/cp6_bf_objects_work.sql#L13-L42), [pemilihan tarif kerja](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/scripts/cp6_bf_objects_work.sql#L75-L97), [tarif laundry](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/scripts/cp6_bf_objects_laundry.sql#L9-L16), [guard revisi grup](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/scripts/cp6_bf_objects_master.sql#L127-L143).

**Fixture native minimum:** A memiliki ukuran 31–33, B memiliki 34, dengan tarif kerja/laundry berlainan. Ikat wave W ukuran 34 ke B; belum ada penyelesaian kerja, kiriman, lot, atau snapshot SKU. Revisi A dan B atomik efektif T: A menerima 34, B menjadi kosong. Pada T+1, buat snapshot kerja dan kiriman laundry W untuk 34.

**Oracle:** produk 34 memiliki bf_version_at_v1 = A pada T+1. Pemakaian pertama W tidak boleh menagih tarif B. Jalur yang diharapkan adalah menolak binding usang dengan pesan yang meminta rebind ke A, atau mengganti binding secara eksplisit sebelum dipakai. Source saat ini masih dapat menemukan versi B kosong dan memilih tarif B. Jika posting lanjut hingga FG, periksa HPP kerja/laundry versus SKU fisik A, lalu inverse dan replay. Jangan terapkan larangan retroaktif yang mengubah harga pekerjaan PO yang memang sudah terpin sebelum T.

**Saran:** validasi kesesuaian (wave, ukuran, SKU, versi berlaku) pada penggunaan finansial pertama untuk kerja dan laundry; rebind wave yang masih kosong atau tolak dengan alasan jelas. Tambahkan tes untuk pergeseran sebelum pin, dan kontrol tersendiri untuk PO yang sudah terpin sebelum pergeseran.

## D-03 — Workspace master mencampur tanggal historis dengan versi grup terbaru

**Prioritas sedang; mismatch deterministik pada source.** get_sku_workspace_v1 membaca p_filters.at ke at_time. products.group_id memakai interval versi pada at_time, tetapi groups dan related_groups memilih revision terbesar. Filter waktu versi hanya berlaku bila wave_id diisi, dan memakai statement_timestamp, bukan at_time. Halaman ConnectedSkuMasterPage memakai workspace dengan parameter at dan roots tanpa wave_id saat pratinjau perubahan; akibatnya daftar anggota serta pengaturan grup dapat berisi keadaan mendatang sementara group_id produk masih keadaan sekarang.

Sumber: [workspace](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/scripts/cp6_bf_objects_router.sql#L25-L57), [dua pembacaan pratinjau](https://github.com/Hanjay6688/-erp-garment-ux/blob/231d29064b8ccf7221ad004cd8ef0017598242fc/src/ConnectedSkuMasterPage.tsx#L47-L64). Uji writer NEW_MEMBER_AND_FUTURE_WAVE_TARIFF memasukkan wave_id sehingga memang memilih revisi saat ini; panggilan master tidak memasukkannya.

**Fixture native minimum:** A = 31–33, B = 34 pada T0; jadwalkan perpindahan 34 dari B ke A pada T1 besok. Panggil workspace dengan at=T1−1 menit dan roots=[34], tanpa wave_id.

**Oracle:** products[34].group_id = B, groups A beranggotakan 31–33, related_groups memuat B beranggota 34, tarif yang ditampilkan adalah tarif T0. Source saat ini menghasilkan group_id B tetapi groups A beranggotakan 31–34, related_groups memuat A dan kehilangan B. Ulang untuk at=T1+1 menit; versi dan anggota A yang baru harus muncul. Jalankan juga browser preview master tanpa wave_id.

**Saran:** untuk semua daftar group pada request dengan at, pilih versi yang berlaku pada at_time. Biarkan wave selector memakai waktu kini secara eksplisit jika memang kontraknya demikian. Sertakan uji API dan browser untuk jadwal yang belum berlaku.

## Status BE dan keputusan retest

BE conversion, non-PO ledger, rework, redye, dan pocket pada source kandidat ditinjau untuk jalur baru. Tidak ada temuan BE tambahan yang cukup kuat untuk dilaporkan sebagai bug baru tanpa native. Override SKU pada celup ulang BE dan beberapa sambungan yang masih terbuka sudah dicatat dalam handoff writer BF/BE; sengaja tidak digandakan di sini.

Urutan retest yang efisien pada disposable writer: D-01 (satu vendor dan satu wave), D-02 (dua grup, perpindahan lalu jasa pertama), D-03 (dua query tanggal dan browser). Catat hasil sebagai PASS/FAIL/INCOMPLETE per oracle, termasuk nilai charge dan versi yang dipilih. Setelah perbaikan, ulang regresi BD DEC05 tanpa SKU serta BF dua SKU satu wave dengan override; ketiganya harus tetap tepat.
