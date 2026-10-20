# Expected pengiriman per jenis — sebelum tambahan transport

Sumber: OW-01 pada OPEN_WORK_D17_14_20261020.md mewajibkan setiap jenis yang tampil di Pengingat sampai ke server WA palsu. Candidate ff587d89/tree96d2cbe0, run39453357551/job118733713404 lulus86/86, sourcehash59eb4d1a3f898dc37fc63a677781043be3faf008c038dd61d6a49ce8beb1d0fe. Kelulusan itu tetap sah dalam cakupannya; bukan pengganti syarat selesai. Root dan dua helper memetakan bukti sendiri sebelum bertukar hasil, dan menemukan celah bukti yang sama.

| Jenis | Bukti yang sudah ada pada ff587d89 | Tambahan yang wajib |
| --- | --- | --- |
| FABRIC_BELOW_MINIMUM | Sumber Native, antrean, real pg_net worker dan fake provider receipt; browser Owner | Tidak perlu mengulang tanpa alasan |
| ACCESSORY_NEED | Native UNKNOWN, real worker/fake receipt, Auth dan desktop/HP | Tidak perlu mengulang tanpa alasan |
| MANUAL_REMINDER | pg_cron dan real fake provider receipt | Tidak perlu mengulang tanpa alasan |
| FG_AT_REORDER_POINT | Native sumber/antrean; browser pengaturan/formula | Receipt nyata per jenis |
| ACCESSORY_AT_REORDER_POINT | Native sumber/antrean; browser pengaturan/formula | Receipt nyata per jenis |
| AR_DUE | Saldo sumber dan collector/episode | Receipt nyata per jenis |
| AP_DUE | Saldo sumber dan collector/episode | Receipt nyata per jenis |
| PRODUCTION_GAP | Snapshot, recheck, antrean/body dan resolusi | Receipt nyata per jenis |
| FABRIC_NEED | Uji WA tanpa aturan menolak; positif sumber/claim lokal pada suite reminder | Positif Native aturan eksplisit dan receipt nyata |
| OPENING_AR | Native saldo70 dan antrean/body | Receipt nyata per jenis |
| OPENING_AP | Native saldo65 dan antrean/body | Receipt nyata per jenis |
| PAYROLL_AP | Native1000→400→0→600 dan antrean/body | Receipt nyata per jenis |
| ACCESSORY_AP | Native kredit12, alokasi bukan pembayaran, antrean/body | Receipt nyata per jenis |
| LAUNDRY_AP | Native17312.90, bayar/inverse, antrean/body | Receipt nyata per jenis |
| LAUNDRY_RECEIPT | Native sumber dan nilai belum diketahui, antrean/body | Receipt nyata per jenis |
| LAUNDRY_OPENING_UNINVOICED | Dua penerimaan Native belum ditagih, antrean/body | Receipt nyata per jenis |

`cp7_wa_obligation_cases.sent()` memeriksa net.http_request_queue sebelum commit. Label historis fake_message=true pada beberapa hasilnya tidak membuktikan HTTP ke provider. Kasus payroll/aksesori juga mengubah bisnis lagi sesudah assertion antrean dalam transaksi yang sama; jangan menjalankan closure itu lalu commit sebagai bukti pengiriman keadaan tersebut. Bukti Native lama dipertahankan, label baru harus menjelaskan antrean dan provider_delivery_proven_here=false.

Expected tambahan:13 ID race baru, satu copy sekali pakai per jenis, seluruh86 ID lama tetap. Rencana count99=55Native/30races/5HTTP/9browser; wiring aktual harus memverifikasi itu sebelum runtime. Setiap positif memakai penulis sumber yang diterima, aturan/setting fixture eksplisit, detail sumber yang dicocokkan, dan satu dispatch/outbox yang benar. Setelah send, commit tanpa mutasi bisnis susulan; real pg_net worker mengirim ke fake CallMeBot saja. Cocokkan nomor uji, key_ok, body tersimpan, HTTP200 dan ACCEPTED; tick ulang tidak membuat dispatch atau receipt kedua. Jangan membuat body/render/source row sintetis atau provider answer sintetis untuk menutup butir ini. Pulihkan worker dan periksa cleanup/residue.

FABRIC_NEED memakai physical.bound + staged analysis + policy publik yang sudah dipakai fabric_held pada suite reminder: sumber snapshot ACTIVE176 dari penulis nyata, bukan menulis angka176 ke sumber. Analisis dan policy memakai actor WA yang sama. Tidak menjalankan receipt_of sesudah snapshot sebelum pengiriman; perubahan sumber memang harus menahan notice pada uji negatif yang terpisah.

Ini scope bukti tambahan, bukan temuan bahwa produk gagal mengirim13jenis. OW-01 tetap BELUM SELESAI sampai kriteria owner dan pemetaan receipt ini terbukti. Hosted/nomor nyata tetap tidak disentuh; production_go:false.
