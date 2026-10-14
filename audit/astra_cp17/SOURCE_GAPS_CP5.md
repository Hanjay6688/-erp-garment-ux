# Penutupan pemeriksaan sumber CP5: tiga alur yang belum lengkap

Kandidat `0b7049d9`. Asal petunjuk Fable R3-06/R3-09/R3-12; penelusuran Astra atas sumber kandidat. Kelas bukti **INDEPENDENT_SOURCE_REVIEW / STATIC**. Dokumen ini membuktikan kontrak/penghubung yang tersedia pada kode yang disebut, bukan menjalankan tiga alur baru di browser atau menyatakan salah saji nominal yang belum diukur.

## SG-01 — Koreksi Bagi Potongan yang sudah POSTED belum mempunyai jalur selesai

Prioritas **S1, kekurangan fitur koreksi** (SKN-27, §16.5). `src/ConnectedPickupPage.tsx` memakai satu writer `erp_save_cutting_pickup_v1`; tindakan SAVE_DRAFT/POST/DELETE dan kontrol edit/delete tunduk pada DRAFT. `guard_cutting_pickup_lifecycle` dalam migrasi v2.6.18 menolak DELETE non-DRAFT dan perubahan non-DRAFT selain transisi DRAFT→POSTED. Penulis CP7 `scripts/cp7-src/cutting-correction/reopen.sql` menolak pickup DRAFT/POSTED sebagai dependency, tanpa menyediakan inverse pickup.

Jangan salah memakai `REVERSE_PICKUP` BB sebagai jawabannya: `bb_manage_opening_wip_v1` dalam rilis BB mengoperasikan pickup saldo awal di tabel BB, bukan `erp.cutting_pickups` produksi ini. Pembaca WIP, laundry, dan source panel menggunakan pickup asli beserta batch/allocation-nya. Menemukan action bernama mirip belum menyelesaikan salah Mandor/tanggal/alokasi pada pickup biasa.

Kesimpulan statis: sambungan koreksi yang tersedia berakhir pada penghalang pickup; belum memenuhi arahan owner agar transaksi stok/uang memiliki jalur koreksi dengan petunjuk penyelesaian. Guard immutability itu benar dan harus dipertahankan. Bukti runtime Astra `CP7_CUTTING_REOPEN_PICKUP_DOWNSTREAM` pada ledger hanya membuktikan refusal yang aman; tidak menutup fitur koreksi pickup.

Tugas penulis: sediakan owner-native inverse/replacement dan navigasi dependency, atau minta keputusan scope eksplisit owner. Jangan menyuruh operator UPDATE/DELETE database. Uji salah Mandor/tanggal/batch sebelum dan sesudah sewing/laundry/QC, jalur melepas dependency sampai selesai, WIP/upah/HPP, replay, race, dan browser. Status **OPEN**, bukan angka uang rusak yang sudah direproduksi.

## SG-02 — Sisa kain tercatat belum berarti kembali ke stok gudang

Prioritas **S1, kekurangan alur fisik** (INV-S01, INV-H02, §16.5). Form `src/ConnectedCuttingPage.tsx` menyusun issued/consumed/reported_remaining. Writer potong menulis `qty_physically_returned=0, return_destination='NONE'` pada pembuatan detail. `erp.post_cutting_material_returns` dalam rilis AC baru membukukan `CUTTING_RETURN` dan jurnal bila physical-return quantity >0, tujuan WAREHOUSE, dan returned_at terisi. Caller normal memang memanggil poster tersebut; syarat fisiknya tidak bisa diisi oleh payload form/writer potong yang tersedia.

Reader koreksi penerimaan mengikutkan qty_physically_returned untuk mendeteksi dependency, bukan menyediakan command pengembalian. YIELD_ANALYZER juga secara eksplisit membedakan reported remaining dari sisa fisik terukur. Karena itu angka sisa pada form tidak boleh dijanjikan menjadi saldo kain yang bisa dipilih potongan berikutnya.

Kesimpulan statis: jalur input→writer untuk pengembalian sisa fisik pada permukaan yang ditelusuri belum tersambung. Tidak mengklaim semua kain nyata telah hilang atau nominal WIP tertentu salah; tidak ada observasi pabrik. Tugas penulis: nyatakan alur return terukur per roll/lokasi/waktu dengan Native owner, kapasitas dan biaya yang benar, lalu buktikan stok kembali, dapat dipakai lagi, inverse/replay, dan browser. Jika memang alur ini ditunda, owner harus mengesahkan batasnya secara eksplisit; nilai reported remaining tidak boleh digunakan sebagai bukti return.

## SG-03 — Rewash berbayar tanpa ganti SKU belum mempunyai sumber tagihan yang terbukti

Prioritas **S2, kontrak/alur belum lengkap** (INV-L03, INV-H02). BD/BE memang mempunyai `rework_service_id`, sehingga klaim “tidak ada tagihan rework sama sekali” salah. Tetapi FK itu menunjuk `be_redye_services_v1`. SAVE_REDYE memanggil `be_save_rework_v1(...,true)`, yang mensyaratkan **SKU tujuan berbeda**; invoice native menerima sumber jasa tersebut dan kontrol redye240 sudah ada. Itu tidak membuktikan rewash biasa dengan SKU yang sama.

Order LAUNDRY biasa menilai komponen upah LAUNDRY_ZERO dan tidak otomatis membuat row jasa redye. Unknown harga jasa dan FREE/WAIVED adalah hal berbeda. Dari sumber ini belum terbukti apakah rewash biasa harus selalu gratis karena tanggung jawab vendor atau boleh ditagih sebagai jasa baru. Jangan menutupnya dengan PASS redye, mengarang receipt biasa, atau memaksa ganti SKU palsu.

Rekomendasi keputusan owner: rewash yang benar-benar berbayar harus mempunyai sumber jasa tersendiri yang tetap menunjuk order/PCS aslinya; gratis harus eksplisit. Penulis menunjukkan rute sah yang ada atau menambahkan rute sesuai keputusan, lalu menguji same-SKU paid/free/unknown, invoice/correction, AP/HPP dan larangan double billing. Sampai bukti itu ada, **OPEN_CONTRACT_AND_ROUTE**, bukan bukti runtime kerugian tertentu.

## Batas

Ketiga butir ini diteruskan bersama lima akar cacat yang sudah dibuktikan runtime. Label sumber statis tidak dipakai untuk menutup gate runtime. Tidak ada produk, migrasi lama, hak akses, atau keputusan bisnis yang diubah oleh auditor. Laporan Fable tetap diberi kredit; penelusuran ini memperjelas bagian yang nyata tersedia dan bagian yang masih kurang.
