# Astra — uji ulang temuan CP1–CP7

Kandidat `dfab13bf62398a69a02bf6221c06d29075e5e40b`, tree `886f83312958b53781a450a4ea2a8fb2147b3be3`. Laporan lama `0b7049d9` beserta addendum terkunci tetap disimpan; keputusan owner D14-2 sampai D14-17 dipakai tanpa dibuka ulang. Produk/cabang writer tidak diubah.

**Lima akar cacat runtime Astra lama dapat ditutup pada kandidat ini untuk kontrak yang diuji. Penerimaan seluruh produk tetap TAHAN karena temuan integrasi/UX baru pada laporan FINAL.** Penutupan akar lama tidak berarti setiap variasi/browser di daftar permintaan lama sudah memperoleh bukti baru.

## Eksekusi independen

Run **38784698219**, job **116593582678**, control commit `1e8b3df248ed4d1fa06abf381b44c03f96a94117`; checkout produk dipin ke dfab13bf. **61/61 case ID persis sesuai manifest PASS**: native41, race4, real Auth/HTTP6, Chromium10. Bukti restorasi CP6, public schema, ACL/definition delta dan advisor gate lulus; tidak ada kasus hilang. Satu kasus tambahan `CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER` PASS dan enam kontrol drain dibaca terpisah, tidak dimasukkan ke angka61.

Label `INDEPENDENT_NATIVE_RERUN`/`INDEPENDENT_HTTP_RERUN`/`INDEPENDENT_BROWSER_RERUN`; fixture dan oracle61 berasal dari penulis, sumber oracle ditelaah Astra. Oracle tambahan buatan Astra (3native+4DOM) disimpan tersendiri beserta asalnya. `INDEPENDENT_CASE_DETAILS.json` memuat nilai/penolakan, bukan hanya warna job. Semua jumlah dan tanggal uang dibandingkan sesuai D14-2/3; label runtime instalasi internal T3_PREP bukan izin rilis.

## Disposisi per temuan lama

| Temuan | Disposisi | Bukti dan batas |
|---|---|---|
| FIN01: payroll sebelum akrual | **DITUTUP** | `CP17_FIN01_FULL_PAY_BEFORE_ATTENDANCE_REFUSED`, `WORK_ONLY_BEFORE_COMPLETION_REFUSED`, `INSTALLMENT_BEFORE_ACCRUAL_REFUSED`, `DIRECT_NATIVE_PAYMENT_REFUSED`, HTTP early dan detector PASS. `payment_floor` menghitung sumber kewajiban; trigger PAID melindungi Native, bukan UI saja. Jalur kasbon tetap terpisah. Kasus browser CP17 menguji kasbon/payroll sah, bukan semua tampilan pesan tanggal salah. |
| FIN02: klaim laundry sebelum sumber/AP | **DITUTUP** | Tiga `CP17_FIN02_*` PASS: kontrol same-day, sebelum sumber, AP pada tanggal belum tersedia. Trigger Native memeriksa lantai sumber dan AP per tanggal. Tidak menganggap kredit lintas invoice D12 dilarang. MISSING/STUCK/DAMAGE seluruh variasi race/browser bukan cakupan tiga kasus ini. |
| STK01: stok negatif setelah REOPEN/rePOST | **DITUTUP** | `CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE` PASS; pasangan riwayat asli/reversal tidak lagi dihitung sebagai dua pemakaian aktif. Bukti ini Native reader, bukan sertifikasi semua layar/history cutoff. |
| RWK01: upah hilang setelah SCRAP | **DITUTUP** | `CP17_RWK01_ALL_SCRAP_REWORK_PAYABLE_ONCE`, `GOOD_CONTROL`, `OPEN_CASE_FINISHED_PART_PAID_ONCE` PASS. View+validator mengakui order selesai dengan biaya posted pada status kasus yang disetujui D14-11; pekerjaan belum selesai tetap tertahan. Tidak membayar sumber dua kali setelah kasus ditutup. |
| HPP01: pool ACTIVE basi setelah policy berubah | **DITUTUP** | `CP17_HPP01_EXCLUDED_CONTRACTOR_POLICY_REFUSED`, `UNRELATED_POLICY_CONTROL`, `CANCEL_POLICY_REPLACEMENT_POOL` PASS. Guard menyertakan peserta lama/baru dan rentang efektif yang menyentuh pool, jalur batal→pengganti sah. Race policy/pool khusus dan seluruh UI pool belum baru diuji. |
| SG-01: batal pickup produksi | **DITUTUP untuk batas yang disetujui** | Native/desktop A61 membalik pickup sebelum sewing; state PO/mandor pulih, bahan/jurnal tidak berubah, riwayat tetap, repost sah. Direct UPDATE tetap ditolak. Setelah jahit/laundry tetap diblokir dengan dependency, bukan fitur pembatalan seluruh tahap. |
| SG-02: sisa kain fisik kembali | **DITUTUP termasuk D14-10** | Return/replay/over/date/cancel/correct/later-use/stale8kasus dan mobile+desktop PASS. Stock/value/WIP kembali tepat, AP supplier tidak berubah. Koreksi berlebih batal seluruh transaksi. Batal/koreksi berlaku sejak disimpan sesuai keputusan yang diterima, bukan penulisan ulang tanggal lama. |
| SG-03: rewash produk sama | **DITUTUP menurut D06** | `CP17_SG03_REWASH_SAME_PRODUCT_NO_VENDOR_BILL` PASS: produk sama kembali2pcs, vendor AP/journal tidak bertambah. Owner telah menetapkan jalur ini tanpa tagihan; auditor tidak meminta jalur berbayar baru. |
| RBAC/FABLE-012 | **MASIH TERBUKA, ditunda sah ke CP7C** | Exposure gate dan real HTTP ERP writers unreachable PASS; 82 writer masih memiliki EXECUTE sebagaimana inventaris. HTTP tidak terjangkau ≠ hak SQL sudah dicabut. D14-9 tetap berlaku: cabut dan verifikasi sebelum ERP diekspos, termasuk stored override/search path. Tidak mengaudit ulang setelan hosted. |
| FABLE-007 overlap payroll | **Tidak dibuka sebagai cacat baru** | `CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS` PASS, satu payroll menang dan duplikasi absensi nol. Tidak mempromosikan ketiadaan counterexample menjadi bukti semua kombinasi concurrency. |
| CP1/CP2 dokumen tidak di pohon | **DITUTUP untuk ketersediaan salinan; CP2 penuh MASIH TERBUKA** | Tujuh berkas cocok hash+ukuran manifest. G01 Astra sendiri kembali menghasilkan15kategori cocok dan satu beda metadata ledger platform70entri yang telah dijelaskan. Laporan hosted Fable putaran lama16/16 tetap REUSED_AUDITOR_REPORT. CP2 restore PG16/stub putaran lama tetap REUSED_AUDITOR_LOCAL_RESTORE_REPORT; image asli, definisi/owner/ACL dan Storage belum dipulihkan Astra. CP7C HOLD; kunci lama yang dilaporkan terpapar tidak digunakan ulang. |
| A2 comparator | **Perubahan pembanding DITUTUP; akar dua kegagalan lama MASIH TERBUKA** | Stable-order before/after PASS; anggota/duplikat, definition, owner, ACL tetap dibandingkan; query lama tersimpan. D13-10 menerima root OPEN sebagai non-blocker. Penyebab lama tidak ditebak. |
| A6/SALES_MANUAL_13 dan lusin baru D14-5 | **Contoh owner terverifikasi; temuan baru terpisah** | Browser desktop/HP A61: 3ukuran4/4/4, manual3/5/4→1lusin, satu ukuran12, simpan/reread, no overflow PASS. Ini menutup kekurangan bukti browser contoh tersebut. Identitas seri lintas merek dan simpan saat load adalah akar baru, tidak menghapus bukti PASS sebelumnya. Enteng masih membuka demo. |
| Backup A1/F-OPS-05/ASR-OPS | **Tetap DITUTUP dalam scope lama** | Tidak diubah di kandidat ini; hasil penulis offsite/cleanup dibaca dengan origin REUSED_WRITER_EVIDENCE. Rerun Astra seluruh backup tidak dilakukan pada putaran ini. Batas operator/admin yang telah diterima tidak dibuka ulang. |
| Release copy / migration history | **DITUTUP untuk masalah dua salinan** | `cp7_release_copy_check.py` dijalankan Astra:30berkas byte-reproducible, perubahan hanya guard pins yang dideklarasikan. `supabase/` identik0b7049d9→dfab13bf; tidak mengubah migrasi historis. |
| SOL-003/AZ first-failure | **Mitigasi terverifikasi; akar log pertama MASIH TERBUKA** | Enam kontrol drain independen PASS; menunggu backend sementara dan mengulang hanya exact drained refusal. Penolakan lain tetap stop. Autovacuum sebagai penyebab lama belum terbukti. |

## Perubahan alat uji

D14-17: di chain Astra, snapshot sebelum U berisi208tabel (207erp+1platform), digest nama `eb7f121d3b5fe5a6fc3c920fb88ddbcd64242580f0689f0459a1cb29cc169069`; X tetap menjalankan pemeriksaan aslinya. Ini rekonstruksi input yang disetujui, bukan pemulihan byte-identik arsip10392910720 atau pengulangan semua tes sejarah di dalam arsip itu.

`cp7_catalog_state` mempertahankan signature/definition dan memeriksa owner, field/ACL lama tetap ada. AV hanya menunggu exact drained refusal sebelum operasi; error post-use yang menjadi oracle tetap diperiksa. Timeout F05 hanya batas proses pembanding; bukan perubahan assertion atau fungsi produk. Kekurangan rollout pengganti arsip ke entry point G01/T2 menjadi temuan alat baru pada FINAL, dengan log pertama tetap disimpan.

## Batas penerimaan

Tidak ada hosted/Drive/deploy atau cabang produk yang disentuh. CP2/CP7C/FABLE-012 yang ditunda tidak diberi status “lulus penuh”. `feature_complete=false`, `production_go=false`. Kelengkapan pemeriksaan putaran ini dan temuan integrasi akhir dijelaskan di `FINAL_ASTRA.md`, `CHAIN_REVIEW.md`, `SCREEN_REVIEW.md`, dan `FINDINGS.json`.
