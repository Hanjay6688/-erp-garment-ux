# CP6 AK — perbaikan preview import dan draft opening

Status terbaru: **Writer PASS untuk keluarga perbaikan terarah**; gate gabungan
dan keputusan global CP6 masih menunggu. Hasil awal yang gagal dicatat di bawah.
`production_go:false`; CP7 belum dimulai. Writer aktif adalah chat ini;
chat sebelah memeriksa successor dan mencari temuan lain secara independen.

Predecessor produk: `47671d9ba2cfb8d02658388adb364b2ae6b89e8d`,
tree `46f4f605444c72dc32282025b859ab66375178b3`.
Checkpoint masuk: `06203dcab15c7e222817f57f1e02bf34d1c7652c`,
tree `f0a7a642f60c04be045a4c952522c7af703b5c99`.
Audit pembanding: `2a6161ea77074725b4b928f4b7135ba3e0749f45`,
native35176804544, artifact10478726559,
SHA256 `e7c3927764be559a5af61af984f5b7e3937f6424d16442d0b3e046a1a55ef223`.

## Aturan edit yang dipertahankan

Owner mengingatkan bahwa draft harus mudah dikoreksi. Prepare opening hanya
membuat dokumen DRAFT; itu bukan alasan membekukan semua edit. Rancangan awal
untuk membekukan batch segera setelah prepare ditarik sebelum commit/pengujian.

AK mempertahankan header opening DRAFT saat staging diedit, membuang hanya
baris persiapan yang belum posted, lalu meminta validasi dan prepare terbaru.
Posting tidak boleh memakai baris lama setelah edit. Histori posted tidak
diubah/dihapus; koreksi posted tetap melalui jalur tertaut. Master yang sudah
diaplikasikan bukan lagi salinan staging bebas: baris tersebut tidak boleh
dipakai untuk menulis ulang master secara diam-diam. Opening draft dalam batch
yang masternya sudah diaplikasikan tetap dapat diperbaiki.

## Keluarga yang diperbaiki

| Producer/consumer | Perlakuan AK |
| --- | --- |
| Preview opening | Lookup material, model, contractor, customer, location, supplier, vendor, cash; product memakai identitas lengkap |
| Master/roll/open-PO | Lookup referensi yang dipakai consumer; parent staging harus VALID; urutan file tidak menentukan hasil |
| Brand/SKU/size | Duplikat master dalam batch ditolak; identitas dan histori produk tidak ditimpa |
| FG opening baru | Parent master dalam batch diperhitungkan tanpa membuat master saat preview; HPP persentase membutuhkan harga sah |
| Stage → prepare → post | Draft dapat diedit; persiapan lama menjadi kedaluwarsa; prepare ulang mempertahankan ID header |
| Retry apply/finalize | Master yang sudah diaplikasikan tidak dibuat lagi; finalize posted tidak menambah efek |
| Dua sesi edit/post | Kunci batch sebelum header pada kedua jalur; diuji commit dan abort di kedua arah |
| Posted → validate/stage | Tidak boleh turun lagi menjadi DRAFT |
| Runtime/pemulihan | Delapan fungsi diganti lewat migrasi baru; fungsi/owner/ACL/data/tabel/marker dikembalikan tepat ke AJ |

SQL AJ dan predecessor tetap byte-identik. Migrasi AK dibuat dengan
`supabase migration new` CLI2.116.0. Tidak ada tabel bisnis atau facade publik
baru; capsule rollback privat hanya menyimpan definisi dan checksum sintetis.

## Rencana bukti

1. Sepuluh probe native pada AJ asli: sembilan referensi opening dan edit draft
   10→20. Hasil masing-masing dikumpulkan, termasuk kegagalan fixture.
2. Dua puluh lima kasus pada AK: referensi opening/master, parent staging
   valid/tidak valid/duplikat, FG baru, edit draft, empat alur recovered sale.
3. Empat jadwal dua sesi edit/post dengan bukti blocking; delapan kontrol
   rollback refusal; restore AK→AJ→AI→AH dan cleanup.
4. Setelah keluarga stabil, jalankan230 kasus gabungan pada AK,28 jadwal
   bisnis,20 jadwal maintenance,4 clock, HTTP/UI/role dan gate frontend.

Grant USAGE sementara pada fixture native dicatat dan dipulihkan. Itu tidak
membuktikan CSV/HTTP import. HTTP/UI memakai layanan dan konfigurasi aslinya
pada lingkungan disposable. Matrix460 tetap bukti maintenance historis,
bukan460 kasus bisnis baru. Tidak ada target kosmetik500.

## Batas yang masih HOLD

Tanggal laporan historis dan kontrak CSV masih mengikuti catatan audit masuk.
Pencarian ulang konteks owner belum menemukan keputusan eksplisit tentang
tanggal seluruh recost pada periode terbuka atau penempatan UI CSV. AK tidak
mengubah kebijakan pembukuan agar tes menjadi hijau dan tidak memindahkan gap
ke CP7. Hasil repair sendiri paling tinggi Writer PASS; independent PASS harus
datang dari chat lain setelah menilai kandidat dan bukti yang sama.

Checkpoint lanjutan akan mencatat SHA/tree final, run, artifact/checksum,
hasil aktual, kegagalan yang tersisa, dan perintah melanjutkan.

## Percobaan terarah pertama

Native35179819526 pada06dd10d7 berhenti sebelum database dibuat: pemeriksa
checksum controller masih menyebut versi AJ80218 byte, sedangkan tambahan
target AK81056 byte sudah terpasang. Ini kegagalan integrasi gate; seluruh
tes transaksi AK pada run ini BELUM DIMULAI. Frontend237 dan parser34 selesai.
Perbaikan harness memperbarui pin serta membuktikan penghapusan hanya binding
AK menghasilkan controller AJ byte-identik. Body drain/rollback tetap utuh.

## Percobaan terarah kedua

Native35180025447 pada3635300e: sepuluh probe AJ selesai. Sembilan kode
referensi yang tidak ada dinyatakan VALID; prepare menolak atomik. Bug material
baru terbukti: edit opening draft qty10→20, revalidate dan prepare ulang tetap
memakai baris lama; posting menghasilkan10, bukan20. Ini transaksi biasa,
bukan kontrol yang sengaja merusak ledger.

AK percobaan ini:11 PASS,14 INCOMPLETE; tidak ada PASS keseluruhan. Sebelas
jalur gagal pada regresi writer alias SQL `h.migration_batch_id` ambigu (42702),
bukan penolakan bisnis yang benar. Tiga kasus lain tidak memulai transaksi
karena fixture belum memiliki gudang bahan. Empat jadwal dua sesi juga gagal
akibat alias yang sama. Alias diperjelas; fixture membuat gudang sintetisnya
sendiri. SQL AK masih draft repair yang belum diterima; revisi eksplisit ini
mengganti hash percobaan awal11011de8, sedangkan seluruh SQL sampai AJ tetap
utuh. Run dan artifact lama tetap dapat dibandingkan.

Delapan kontrol refusal rollback dan restore AK→AJ (533 fungsi/225 tabel),
AJ→AI (533/224), AI→AH berhasil pada percobaan ini. Seluruh boundary native
dan grant sementara kembali semula; database clone dibuang. CodeQL35180025515
berhasil, tetapi tidak menggantikan kegagalan transaksi native tadi.

## Perbaikan terarah lulus — lanjut gate gabungan

Produk AK:684b708dee785934fe5fe4fe567c454cba873ea9,
tree1f4c57517c0d4abd6612d4a8b36b2e9cbe437834. Native35180462134 SUCCESS,
CodeQL35180462117 SUCCESS empat bahasa. Artifact10480561465,3205631 byte,
SHA25654d7b528196cc0f12c6ca02f449368273b9f20bd0a9e6a8b959599165ebec916;
checksum ZIP, CRC, nama entry dan selected secret-pattern scan diperiksa lokal.

25/25 kasus AK PASS,0 incomplete;4/4 jadwal dua sesi PASS dengan blocking
teramati. Draft qty10→20 menghasilkan20 dan25.00; ID header dipertahankan,
prepare replay sama, master replay tidak menggandakan, finalize replay sama.
Posted menolak stage/revalidate. Delapan refusal rollback PASS; pemulihan
AK→AJ533/225, AJ→AI533/224, AI→AH533/223 tepat termasuk definisi,owner/ACL,
data/tabel dan marker. Auth/app users0, grant native dipulihkan, clone dibuang.

Sepuluh pembanding tetap memakai runtime AJ asli:9 GAP_PROVEN dan1 BUG_PROVEN,
semuanya selesai dan boundary kembali semula. Itu tidak dijumlahkan sebagai
kasus successor yang lulus. Hasil ini Writer PASS, bukan independent acceptance.

Gate berikutnya mengulang230 kasus bisnis pada AK karena post_opening_balance
dan alur import berubah. Tambahan28 jadwal bisnis,20 maintenance pada edge AK,
4 clock, HTTP/UI/role dijalankan bersama.460 historis tidak dihitung sebagai
460 bisnis fresh; schedule import baru memang diuji secara tersendiri.

## Gate gabungan dan tindak lanjut alat audit

Kandidat produk tetap `684b708dee785934fe5fe4fe567c454cba873ea9`, tree
`1f4c57517c0d4abd6612d4a8b36b2e9cbe437834`. Alat gabungan
`aa010fbecb512cccf03084e7adb8c426097873e7`, tree
`84383d56a69f0ce4be64937a3df09e276c5ba87e`, parent produk tersebut.
[Native 35180891327](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35180891327)
selesai FAILURE; [CodeQL 35180891317](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35180891317)
lulus empat bahasa. Artifact `10479904487`, 57.373.952 byte, 308 entry,
SHA-256 `ba89c74c015a44d5bbf40f3ad0f3a9c645786d9de5965a838230c5d0da51fbae`.
Digest/CRC, nama entry unik/aman, symlink, dan selected secret patterns diperiksa.

230 ID direncanakan dan dicoba: 169 PASS, 39 CONTROL_PASS, 12
DATE_POLICY_REVIEW_REQUIRED, 10 INCOMPLETE. Sepuluh incomplete adalah replay
opening IMPORT bahan/roll dalam lima zona: oracle lama mengharapkan pesan
`Opening balance must be DRAFT`; AK lebih dahulu menolak batch yang sudah
POSTED dengan `AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH`. Penolakan atomik
teramati, tetapi sisa oracle belum selesai dan tidak boleh dianggap PASS.
Selain itu, agregator mengharapkan label `PASS` untuk concurrency yang hasil
sahnya `PASS_REVIEWED_SCOPE`; pemeriksaan label diperbaiki tanpa mengubah tes.

25 tes import dan 4 jadwal edit/post tetap lulus. 28 jadwal bisnis (16+12),
20 maintenance, 4 clock, HTTP 95 assertion, UI 43+58, pemeriksaan nominal/role,
restore AK→AJ→AI→AH serta cleanup selesai. Rincian angka role berada dalam
artifact; assertion dan transaksi tidak dijumlahkan menjadi kasus unik palsu.

Tindak lanjut terarah memeriksa status header dan batch benar-benar POSTED,
lalu hanya menyesuaikan pesan penolakan replay tersebut. Nilai uang, stok,
tanggal, READY, boundary dan seluruh oracle lama tetap wajib cocok. Penghapusan
adapter harus mengembalikan source oracle gabungan byte-identik. Sepuluh alur
diulang penuh; 220 hasil lain dipertahankan dengan status asal, termasuk 12 HOLD.
Reuse hanya sah bila kandidat produk, seluruh dependensi runtime, konfigurasi,
source oracle di luar adapter, dan 690 objek terpasang tetap terverifikasi.

Tambahan enam alur positif saldo awal contractor/customer/supplier/vendor/cash
menguji nominal 14,25, arah jurnal, dan subledger. Total import terarah menjadi
31. Ini melengkapi bukti bahwa validator menerima referensi sah, bukan hanya
menolak referensi salah. Supabase security advisors dibandingkan AJ→AK secara
read-only; temuan baseline disimpan, bukan dihapus. Tambahan ini belum dinilai
PASS sampai run tindak lanjut selesai. Tidak ada perubahan SQL/src pada wave ini.
