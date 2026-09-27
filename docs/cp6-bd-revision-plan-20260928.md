# BD — revisi sesudah audit independen, 28 September 2026 WIB

Mandat owner: revisi seluruh temuan pada handoff gabungan terbaru. Writer tetap tunggal pada `claude/new-session-deapao`; baseline revisi `2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b`, sudah memuat BE. Kandidat yang diaudit `08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec`. Auditor independen menguji ulang sebelum temuan ditutup. CP6 HOLD; production_go=false. CP7 belum diimplementasikan.

Sumber intake: `Handoff_Writer_BD_20260927.md`, versi 1, diperbarui 2026-09-27T18:51:39.999901Z; audit `507931ddf31aed44f449176646e3a44dc0481ec2`, run36341741346. Penelitian silang dalam handoff tetap dibedakan dari kasus awal buta. Branch audit tidak menjadi target penulisan. Tidak ada mutasi hosted/UAT/legacy atau deployment.

## Kontrak perbaikan dan expected sebelum kode

| ID | Perubahan | Expected dan kontrol |
|---|---|---|
| X-01 | Coverage jasa mengikat ukuran sumber dan qty yang benar-benar dilayani; snapshot coverage dipertahankan saat harga UNKNOWN diisi | Kirim7+6 PCS: wash13×4321.09=56174.17, finish5×678.91=3394.55 hanya pada ukuran kedua. Laundry ukuran pertama30247.63; kedua29321.09; total59568.72. Dengan labor700/600: HPP30947.63/29921.09. Coverage hilang pada beberapa ukuran, berlebih, duplicate/asing ditolak atomik; partial receipt, QC, sale/return dan resync tetap conserve. |
| X-02 | Bobot uang untuk pembagian diskon tidak dibatasi integer32 | 21474836.47/48 dan28123456.78 dapat diposting tepat pada source sah; diskon multi-line/residual tepat; source capacity/atomicity tetap. |
| X-03 | Otorisasi aksi terbaru sebelum cache/replay pada seluruh facade BD | Request sah/replay satu efek; revoke menolak fresh maupun replay tanpa nominal; restore memungkinkan replay sah tanpa write ulang; request berbeda payload/aktor tetap ditolak. |
| X-04 | Input extra paket dengan coverage per ukuran dan alasan | Paket+extra sah mengirim payload tepat; included component tidak ditagih lagi; kebijakan extra tetap wajib; form tidak hilang saat error/refetch. |
| X-05 | Semua invoice dan receipt yang sah dapat dijangkau lewat paging/search | 55 invoice dan201 receipt dapat diambil/dipilih, tanpa duplikasi/hilang; filter vendor dan otorisasi tetap; draft yang sedang diedit tidak dibuang saat pindah halaman. |
| X-06 | Jalur tarif celup konsisten dengan extension BE | Verifikasi runtime BD+BE dan pemanggilan facade yang benar; BD-only tetap tidak mengaku mempunyai BE. |
| X-07 | Build resmi dan ownership | Jalankan gate resmi tanpa melewati security; enam ownership BE sudah pernah diperbaiki pada baseline, buktikan status aktual dahulu. |
| OWN-01 | Respons estimated_cost mengikuti jumlah exact snapshot | 13 PCS memberi59568.72, bukan59568.73; ledger yang sudah tepat tidak diubah. |
| OWN-02 | Konfigurasi eksplisit FREE/WAIVED untuk komponen, serta penyelesaian harga UNKNOWN dengan alasan sah | Gratis/waiver0 berbeda dari UNKNOWN/null; KNOWN0 tetap ditolak; versi/scope/actor/reason tersimpan; tidak membuat payable atau biaya fiktif. Operator tanpa izin ditolak; snapshot historis dan free rewash legacy terjaga. Ini gap acceptance yang disediakan writer, belum temuan tertutup. |

## Urutan dan bukti

1. Simpan intake/expected dan cek baseline; cek official build serta seam BE sebelum atribusi.
2. Perbaiki satu keluarga coverage/price, integer uang, dan auth; bentuk probe native dari expected di atas sebelum menjalankannya.
3. Sambungkan UI coverage/extra/free dan paging; parser fail-closed; tes browser/Auth serta kontrol negatif.
4. T1 keluarga pada disposable runtime yang dipin, lalu regresi BD+BE terdampak. Kandidat rilis/paket/rollback dikualifikasi setelah source stabil, sesuai A+B.
5. Serahkan exact SHA, per-case results, kegagalan lama, source dependencies dan batas bukti. Writer tidak menutup temuan auditor atau memberi production GO.

Coverage per ukuran adalah aggregate qty jasa pada source batch/size yang sama, bukan serial per PCS. Partial receipt mengambil bagian dari biaya ukuran itu dengan residual terakhir, mengikuti mekanisme existing yang diuji; ukuran tanpa jasa tidak mendapat alokasi. Tidak menebak penerima saat input parsial ambigu.

Setiap push asing pada writer branch menghentikan penulisan dan dilaporkan. Branch yang tidak bergerak hanya membuktikan belum ada push terlihat, bukan editor lain pasti berhenti.

## Hasil putaran awal (bukan penutupan audit)

- `e2b33f9`, T1 run36344158914: seluruh35 kasus existing PASS; enam kasus revisi: FREE/WAIVED, nominal besar, izin replay, dan paging PASS. Coverage dan response tepat, tetapi dua assertion HPP writer FAIL karena membandingkan per-PCS sesudah pembagian pecahan berulang7/6 secara exact. Fixture kain10×10=100 (sumber `cp6_aa_invoice_partial_audit.estimated_receipt`) dialokasikan pada HPP enam desimal:53.846154 dan46.153846. Oracle diperbaiki menjadi **nilai tiap lot exact** dan total exact, tanpa toleransi; produk tidak diubah karena kegagalan assertion itu. Hasil awal tetap FAIL, tidak dilabel ulang.
- Reader native232 berkas (14 BD,205 import,13 Laundry) diterima parser halaman, nol penolakan.
- T3 run36344158905 masih memakai paket lama; gate menolak `BD_T1_FUNCTION_NOT_CURRENT`. Paket source perlu regenerasi, capture pin, kemudian install/compare/rollback ulang.

Review lanjutan X-02: pembagi uang memakai quotient/remainder integer numeric (`div`/`mod`), agar pembagian desimal tidak membulatkan quotient18 digit sebelum `floor`. Expected batas helper9999999999999999.99 dengan bobot1:1 adalah5000000000000000.00 +4999999999999999.99, exact; kasus ini menguji helper, bukan mengklaim journal end-to-end pada batas tersebut. Kontrol invoice end-to-end tetap memakai angka audit21474836.47/48 dan28123456.78.

Gabungan BD+BE run36344627210:6 native revisi,18 race,6 HTTP PASS. Browser INCOMPLETE sebelum satu kasus dijalankan: `ERR_MODULE_NOT_FOUND`, entrypoint disalin keRUNNER_TEMP sedangkan import relatif mengarah ke folder itu. Loader skenario diperbaiki ke path repository yang menjadi cwd host; aturan host dan verdict tidak berubah.

Run36345520659 pada0133b16:6 native revisi,18 race,6 HTTP kembali PASS; browser9 PASS/6 INCOMPLETE. Satu locator lama belum menyebut ukuran; lima kasus baru berhenti di read-back fixture karena `as_owner` memanggil helper role pada schema privat. Locator diperbarui menjadi per-ukuran. Read-back menggunakan grant transaksi fixture yang sama dengan create, dicabut lalu rollback sebelum kembali; tidak ada grant produk/Auth yang diubah dan tidak ada transaksi HTTP yang melihat grant itu. Hasil lama tetap INCOMPLETE. T1 run36345520728 pada source0133b16:41/41 PASS, reader232 berkas diterima tanpa penolakan.
