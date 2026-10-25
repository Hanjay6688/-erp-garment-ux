# Peta kualifikasi current — inventaris, bukan penerimaan

## Pembaruan 25 Oktober 2026 — kandidat performa `88f36937`

[Inventaris sumber terbaru](workflow-inventory-performance-88f36937-summary.json)
memuat 351 workflow dan 117 deklarasi sumber. Dibandingkan integrasi resmi
`a255e48f`, ada 2.291 berkas berubah; 61 workflow cocok dengan filter cabang/path
lokal. Dari 61 itu, 47 mempunyai setidaknya satu deklarasi lama yang berbeda
dari sumber kandidat, sedangkan 14 hanya cocok pada byte sumber yang terpetakan.
Angka ini tidak berarti 61 suite wajib, 14 kelulusan runtime, atau kegagalan
bisnis pada 47 suite. Pemetaan penerus per kasus tetap diperlukan sebelum
kualifikasi satu kandidat; deklarasi historis tidak diubah agar terlihat cocok.

Pada seluruh 117 deklarasi, 83 memuat perbedaan pin. Deklarasi current Native36
(3.475 berkas) dan performance Native36 (3.569 berkas) sama persis dengan sumber
kandidat. Pemeriksaan lengkap performance Native36 beserta tujuh Original
prasyarat juga lulus secara terpisah; [run aktual](performance-native36-running-88f36937.json)
masih berjalan. Enam kelompok current sudah mempunyai hasil aktual yang
diverifikasi di [status gabungan](CURRENT_MODEL_TARGET_STATUS_20261024.md).

Inventaris ini tidak mengubah pemicu, pin atau cabang, dan tidak memberikan
kredit kasus. Hasil historis di bawah mempertahankan kandidat, tanggal, cakupan
dan batas awalnya.

## Inventaris awal 24 Oktober 2026


Pada kandidat `a17b34cf3402eea8996028345fcf6d715367e684`, repo mempunyai **238 berkas workflow**.
Angka ini bukan 238 suite wajib atau 238 pengujian lulus. Dibandingkan integrasi
resmi `a255e48f`, ada 420 commit dan 956 berkas berubah. Inventaris seluruh diff
mendapat 33 workflow yang cocok dengan filter cabang integrasi/path lokal.
Pemeriksaan 58 deklarasi `SOURCE.json` menemukan 16 deklarasi dengan setidaknya
satu pin berbeda; hasil lengkap ada di `workflow-inventory-a17b34cf.json`.

`scripts/cp7_current_qualification_inventory.py` membaca blob Git dari commit
eksplisit. Tidak mengubah pin, menjalankan DB, memicu CI atau memajukan cabang.
Pencocokan pin tidak menjalankan admission impor/dependensi. Entrypoint yang
belum dapat dipetakan dicatat tersendiri; tidak diberi kredit lulus.

Dokumentasi GitHub.com yang diperiksa 24 Oktober 2026 menyebut batas diff
**3.000 berkas**, bukan 300 pada dokumentasi Enterprise Server lama. Diff956
di bawah batas tersebut. Tetap cocokkan daftar run aktual setelah dispatch;
hasil lokal tidak membuktikan job benar-benar dijalankan. Sumber:
[GitHub — Git diff comparisons](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons).

## Bukti current yang sudah diperiksa

| Workflow | Bukti Original | Lingkup yang benar-benar terbukti |
|---|---|---|
| `cp7-current-installation` | `current-install-28abdeef-used-restore-pass.json` | Inventory wajib, generated types aktual, sembilan langkah backup/restore, enam kontrol negatif |
| `cp7-current-runner` | `current-runner-28abdeef-cron-used-restore-pass.json` | Cron menit asli tanpa tick manual; angka resmi; sembilan langkah restore |
| `cp7-ab-owner-families` | `owner62-28abdeef-pass.json` | 62 ID Native lama pada delapan keluarga A; bukan OW05 Native28/OW05b Native6 |
| `cp7-ab-owner-auth` | `owner-auth8-28abdeef-pass.json` | Delapan kasus Auth nyata OW05/06, dua pengguna, hak sesudah wait/replay |
| `cp7-ab-owner-browser` | `owner-browser19-7b26351f-pass.json` | 13 perjalanan daftar/retur dan enam mandor/transfer; bukan semua semantik lintas halaman OW09 |
| `cp7-ab-bounded-native` | `ab-bounded-28abdeef-native12-pass.json` | Lima kasus angka resmi, enam bounded, satu isolasi UUID/metode |
| `cp7-ab-bounded-browser` | `ab-bounded-browser4-28abdeef-pass.json` | Empat perjalanan bounded desktop/HP dengan Auth nyata |
| `cp7-ow14b-installation` | `ow14b-28abdeef-native4-pass.json` | Empat kasus inventaris minimum lama, identitas/satuan/enam desimal/UNKNOWN |
| `cp7-ab-bounded-restore` | `ab-bounded-28abdeef-used-restore-pass.json` | Sembilan langkah gabungan bounded sebelum successor inventory/types |

Semua baris itu mempunyai CP6/advisor dan lima gate paket PASS serta verifikasi
ZIP/Original byte+SHA. Delapan di head28abdeef; Browser19 di7b26351f. Perubahan
setelahnya menambah qualifier/dokumen, tidak mengganti sumber produk. Bukti tetap
berlabel **REUSED_WRITER_EVIDENCE**, bukan audit independen atau izin produksi.

## Arti label historis Native286

Factory dan perhitungan Original diperiksa ulang: label lama **Native286**
sebenarnya menjumlahkan **180 kasus Native satu sesi +106 kasus mode lain**
(transaksi bersamaan, HTTP/Auth dan browser), bukan286Native satu sesi.
Inventaris `retained-286-mode-inventory.json` memuat semua180ID asli; pembuatan
daftar dilakukan tanpa eksekusi kasus dan menolak koneksi database.

| Suite historis | Total semua mode | Native satu sesi | Mode lain |
|---|---:|---:|---:|
| OW14b rules |113|61|52|
| OW16 status |16|10|6|
| OW13b history |20|14|6|
| F04 baseline |38|27|11|
| P19 staged |15|7|8|
| F04 netting |84|61|23|
| Total |286|180|106|

Label lama dan Original tetap utuh. Native180 saja kelak tidak boleh menutup
286;106kasus mode lain harus punya bukti masing-masing. Ini koreksi cakupan
dan rencana uji, bukan hasil runtime atau penerimaan tambahan.

## Pemetaan historis yang sudah mempunyai penerus

| Entry point historis | Penerus dan batas pemetaan |
|---|---|
| `ab-quote-browser-qualification` dan `ow09-chain-browser-qualification` Browser13 | Browser19 menjalankan 13 ID yang sama. Adapter retur memakai settlement quote current sambil mempertahankan oracle uang/stok/inverse; kegagalan awal tetap tersimpan. |
| `ow05b-browser-qualification` Browser2 | Dua ID panduan asli termasuk Browser19 tanpa perubahan modul perjalanan. |
| `ow06-browser-qualification` Browser2 | Dua ID transfer asli termasuk Browser19 tanpa perubahan modul perjalanan. |
| `finance-bridge-chain-qualification` Native5 | Lima ID asli merupakan lima kasus pertama Native12; bukan klaim factory3600. |
| `production-chain-qualification`, `b-extension-chain-qualification`, `ab-quote-chain-qualification` restore | Current installer menguji sembilan langkah pada seluruh gabungan dan enam kontrol negatif. Ini penerus preflight komposisi/restore, bukan pengganti Native286, perjalanan P21 seluruh uang, atau seluruh kasus B. |
| `cp7_contractor_guidance` Native6 | Native34 current headc99ca612/run40059271805 telah PASS28+6 ID asli; Original dan lima gate terverifikasi di mandor34-c99ca612-pass.json. |

Peta ini tidak menghapus workflow/pin historis. Mengganti trigger atau menyatakan
workflow lama selesai memerlukan pemetaan kasus/expected/observed per lingkup,
bukan hanya kesamaan nama atau katalog22. Workflow root yang tidak memiliki
ancestor SOURCE tetap memerlukan penelusuran admission dan bukti masing-masing.

## Bukti tambahan yang sudah diperiksa

| Lingkup | Kandidat/run | Status saat catatan ditulis |
|---|---|---|
| Group transfer400+600 sesudah current full restore, empat koreksi dan inverse | `aea44fa9`, run40058216568/job120765815354 | PASS9langkah+6kontrol; seluruh group read/replay/empat koreksi/inverse tepat; CP6/advisor/lima gate PASS |
| Transfer alokasi31penerimaan lintas25+6, desktop/390px | `535c97af`, run40061613739/job120776139818 | PASS2uang/aksi/paging dan tampilan akhir sudah dibalik/aksi baru siap; PNG halaman2/akhir diperiksa; Auth/DB/CP6/advisor/lima gate PASS; receipt transfer-pages-535c97af-final-ui-pass.json, bukti28f73c0f tetap |
| Riwayat pembayaran/retur31 dokumen:25+6 dan filter30:25+5, desktop/390px | `6c3e5a9e`, run40059653484/job120770175605 | PASS2; dua riwayat25+6/filter25+5; Native/DOM tepat,0writer; Auth/DB/CP6/advisor/lima gate PASS; firstfailurea17 tetap |
| Mandor correction14 +edge3 +rate11 +guidance6 | `c99ca612`, run40059271805 | PASS34 ID lama, boundary utuh/CP6/advisor/lima gate PASS; Original8561436byte SHA84b45470c44be16befd387a019399f4a311236991bbc32d480156e7bba59ca7c |
| Seluruh komposisi UI lama +dua connected draft successors | `5681edbd`, run40061341301/job120775316058 | PASS31 ID lama tanpa perubahan modul; Auth0000/DB0/console0/CP6/advisor/lima gate; receipt legacy-ui31-5681edbd-pass.json. Bukan31kasus baru atau penerimaan pensiun D13-9c/D13-12. |
| Nota/FG/hitung fisik/aksesori/kartuFG, desktop+HP | `fefb20f3`, run40062079889/job120777559166 | PASS10; halaman nyata25+6,50+6,25+7; filter tetap lintas halaman, Native/DOM dan saldo prefix tepat,0writerRPC; Auth/DB/CP6/advisor/lima gate PASS. Firstfailure23ec tetap; receipt owner-lists-fefb20f3-pass.json. |
| P21 seluruh uang A pada current A/B dan bounded work/draft | `bc4dd575`, run40063578444/job120782028070 | PASS6langkah restore+7chain+3mandor+4siklusP21,5kontrol negatif, dua readback tepat, goldP1000/P900/undo/inverse tetap; CP6/advisor/lima gate PASS. Receipt full-money-bc4dd575-pass.json. Status seluruh cutting group ditambahkan pada penerus8langkah, belum dikreditkan pada run ini. |
| P21 seluruh uang +status produksi B | `d18f5d26`, run40064922630/job120786031258 | PASS6restore+8chain+3mandor+4siklusP21,5kontrol; semua15status cutting group tepat,30jendela clock raw divalidasi ulang, pembaca tidak mengubah data/sequence/full22; CP6/advisor/lima gate PASS. Receipt full-money-d18f5d26-status-pass.json. |

Ketiga run Browser31/Transfer2/OwnerLists10 telah terminal dan Original diperiksa;
tidak ada lagi run aktif dari kelompok ini. Delapan daftar OW09 kini mempunyai
bukti lintas halaman dari Browser19, InvoiceHistory2 dan OwnerLists10.
Peta12batas CP6 ada di CP6_CURRENT_BOUNDARIES_20261024.md. Target berikut:
penerimaan pemetaan pengganti
layar CP6 yang dipensiunkan, dan daftar
kualifikasi satu kandidat beserta pembanding CP6 lengkap. **21 kegagalan CP6
dan empat kasus browser baseline tetap ditampilkan sesuai hasil asli**;
tidak ada kredit PASS karena tidak dijalankan. Formal parent tetap5/16,
`production_go=false`, kandidat audit lama tetap beku.
