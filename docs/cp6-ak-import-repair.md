# CP6 AK — perbaikan preview import dan draft opening

Status awal: **WRITER INCOMPLETE**, belum ada klaim PASS untuk AK.
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
