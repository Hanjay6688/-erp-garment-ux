# Uji ulang Sol — dfab13bf

Kandidat `dfab13bf62398a69a02bf6221c06d29075e5e40b`, tree `886f83312958b53781a450a4ea2a8fb2147b3be3`. Asal temuan lama: laporan Sol yang dikunci pada `10bfe3972bd310dbd8600cd18638a02f47d007f0`, produk lama `0b7049d9`. Putaran ini tidak menulis perbaikan produk.

## Tiga temuan lama

| ID lama | Hasil | Bukti independen dan batas |
|---|---|---|
| SOL-001: bank kosong membayar supplier | **DITUTUP dalam scope pengeluaran dan tanggal yang diuji** | Run 38785656146: bank 0 membayar 1 ditolak CP7_CASH_NEGATIVE; AP/bank unchanged. Kontrol pemasukan public 34,50 lalu bayar 1 → bank 33,50/AP 999. Backdate sebelum modal, prefix hari berikutnya, pembalik modal yang telah dipakai, dan CP17 race/vendor/payroll lulus. D14-3 tidak memakai pengecualian overdraft. **Temuan baru SOL-R1-001 berbeda:** guard sekarang menghalangi koreksi yang sah. |
| SOL-002: artifact BE hanya 4/16 | **DITUTUP** | Run 38785656260, artifact 11997303136: BE_CASES_AFTER tepat 16 ID PASS; RESULT_AFTER sama, mismatch kosong, full boundary pulih. OUT tidak berpindah saat impor AV dan artifact gate memeriksa himpunan/status akhir. |
| SOL-003: diagnosis pemasang hilang | **DITUTUP untuk penyimpanan diagnosis; sebab AZ lama tetap OPEN** | 38787131786 membuktikan owner/akun kerja non-superuser, 58 berkas tepat, seluruh 10 kontrol lulus. 38790510239 membuktikan real error P0001, primary/detail/hint/context, identitas sesi, metadata backend tanpa query text, SHA dan file 0600. Tidak ada klaim autovacuum pasti penyebab AZ pertama; diagnosis historis memang tidak tersedia. |

## Delta lain yang diperiksa

| Perubahan | Disposisi |
|---|---|
| D14-5/12 seri lusin/range | **PASS cakupan browser nyata DISPOSABLE desktop/phone.** CP17 D14_5: seluruh ukuran SKU yang tersedia, 1 lusin 4/4/4; manual 3/5/4 → 1 lusin; 4/5/4 → 1 lusin 1 PCS; satu ukuran 12; ukuran berdampingan di HP. Tidak mengaktifkan UAT yang masih demo. |
| D14-2 tanggal upah | CP17 FIN01 Native + HTTP dan regresi payroll F03 lulus; tanggal bayar sebelum hak lahir ditolak. |
| D14-3 kas tidak minus | Pengeluaran kosong, tepat nol, backdate, prefix lanjut, payroll/vendor dan race lulus. **Koreksi compound sah FAIL**, lihat SOL-R1-001. |
| D14-6 kasbon | CP17 give/deduct/release/replay + real HTTP dan browser lulus dalam kasus yang dideklarasikan. |
| D14-8 public-state comparator | Stdout asli 38785656146 membuktikan urutan stabil dan sensitivitas definisi/member/owner/ACL. Grant→revoke meninggalkan ACL eksplisit, perbedaan itu tetap dicatat. Dua root A2 lama tetap OPEN. |
| D14-9 82 EXECUTE | Exposure gate dan real HTTP ERP-writers-unreachable lulus; pencabutan tetap CP7C. Tidak direlabel sudah dicabut. |
| D14-10 retur kain cancel/correct | CP17 SG02 Native/replay dan browser correction lulus. Efek inverse sejak disimpan mengikuti keputusan owner; bukan restatement semua hari antara. |
| D14-11 upah rework OPEN/PARTIAL | Native RWK01 membayar bagian selesai sekali; belum selesai ditahan. Belum browser rework→Nota→bayar satu rantai. |
| G1 selesai jahit/upah | CP17 Native/race/real Auth HTTP/browser desktop/phone lulus jalur dasar. Oracle literal Sol 4+6 PCS dengan dua komponen membuktikan upah 16+24, mandor 30/obras 10, batal 4 menyisakan 6 PCS/upah 24. Wave BF belum didukung. |
| G2 selesai PO/HPP final | CP17 G2 Native/race/real Auth HTTP/browser lulus, WIP nol; tanggal selesai hari ini WIB sesuai kontrak. Belum satu browser QC→G2 penuh. |
| G3 51 workflow lama | Writer receipt diperiksa identitasnya. Sol sendiri menjalankan F03 8 bucket + CP17; tidak mengklaim mengeksekusi ulang semua 51 workflow writer. |
| D14-17 pengganti pre-U | Frozen capture dilakukan tepat sebelum U; count 208/207/1 dan names hash tetap dipin; X tidak dilonggarkan. **SOL-R1-003:** helper salah menuntut capture saat berhenti sebelum U. Adapter audit stop-aware mempertahankan semua guard Native. Equivalence byte-for-byte dengan arsip yang kedaluwarsa tidak diklaim. |

## Kualifikasi alat dan merah asli

Kasus koreksi pertama INCOMPLETE karena token generic dibaca dalam Asia/Jakarta, sementara writer correction fixed UTC. Qualification hanya memakai token/versi dari public workspace koreksi sebagaimana UI; angka, tanggal dan expected tetap. Hasil sesudahnya COUNTEREXAMPLE, ditambah dua saksi HTTP nyata, tidak dibuang.

Owner baseline pertama gagal sebelum kasus karena pending pre-U pada stop sebelum U. Diagnostik kecil pertama gagal sebelum kasus karena import memakai CWD parent. Kedua original tersimpan dan kualifikasi dijelaskan di JSON masing-masing. Tidak ada rerun identik kasus bisnis untuk mencari hijau.

`original_posted_facts_immutable=false` pada metadata spent HTTP adalah pembandingan timestamp lintas zona; bukan bukti mutasi. Snapshot UTC seluruh bisnis/privat membuktikan unchanged pada command yang ditolak. Data mentah dipertahankan.

## Putusan uji ulang

Perbaikan tiga temuan lama dapat ditutup **dengan batas di atas**. Kandidat gabungan tetap **HOLD** karena regresi koreksi baru dan celah aplikasi dalam `FINAL_SOL.md` / `WRITER_HANDOFF.md`. Penutupan temuan lama tidak berarti CP1–7 siap produksi atau root AZ lama diketahui.
