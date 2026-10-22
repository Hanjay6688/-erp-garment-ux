# OW14b — minimum lama sebagai referensi dan pilihan satu aturan

23 Oktober2026 WIB. **Checkpoint implementasi; belum selesai dan belum siap digabung.**

Pilihan eksplisit per kain pada panel lama kirim: pertahankan aturan aktif, pilih rumus, atau pilih angka minimum
lama yang diperiksa. Angka lama tidak bisa diketik ulang di panel ini. Pilihan minimum lama menyalin nilai sumber
ke revisi privat yang tetap; perubahan metadata lama berikutnya tidak mengganti pilihan itu. Pilihan rumus tidak
menghapus referensinya dan tidak menjalankan pengingat minimum lama kedua. Sebelum pilihan eksplisit, aturan yang
sudah ada tetap berlaku. Minimum0 yang dipilih adalah0 yang diketahui, bukan angka hilang.

Sumber angka tetap compute_materials. material_source serta gabungan fabric_kind_source memakai pilihan yang sama,
termasuk ketika pembacaan sibuk; kunci fisik sama tidak membuat dua pengingat. Daftar minimum di facade Ringkasan
Gudang tetap fakta Native lama dan ditampilkan terpisah sebagai referensi netral, bukan peringatan kedua.
Ringkasan kain yang dibuka di atasnya menampilkan aturan aktif dari sumber yang sama dengan panel/pengingat.

Kontrak publik workspace cp7.material-reorder.v2, endpoint tetap. Row menambah legacy_minimum_qty dan fabric_rule;
legacy_minimum_qty/point/manual_point berbentuk teks desimal tepat. Klien tetap membaca arsip v1 bernomor JSON.
Payload pilihan menambah pasangan fabric_rule + expected_legacy_minimum_qty. Server memeriksa nilai sumber, revisi,
UUID/isi yang sama, hak sesudah lock dan hak sebelum selesai. Klien lama yang hanya mengubah lama kirim tidak
mengosongkan aturan yang sudah dipilih. Tiga kolom privat bertambah, tidak ada fungsi/role/endpoint baru.

Bukti saat checkpoint: enam kelompok SQL aktual pada adapter ERP/identitas terkendali lulus;44 uji klien/DOM dan
TypeScript/CSS lulus. Bukti lokal bukan Native/login/race nyata. Kegagalan pertama UI lama serta skala serialisasi
tetap disimpan. Nilai800/60/900/1000 adalah fixture, bukan keputusan owner atau angka Enteng.

Permintaan simpan sekarang disimpan sebelum pengiriman dengan satu key per UUID. Dua tab tidak menimpa catatan
masing-masing. Balasan hilang pulih dengan UUID/isi sama setelah remount; pilihan lain atas bahan yang sama ditahan.
Isian baru yang belum dikirim tetap ada ketika permintaan lama diperiksa. Penolakan hak saat ini menyembunyikan fakta
dan nama bahan, tetapi tidak membuang permintaan yang mungkin sudah tersimpan. Data lokal rusak tidak ditimpa;
catatan yang gagal disimpan tidak mengirim RPC. Hanya penolakan pasti sesudah pemeriksaan replay/sebelum INSERT
yang mengizinkan permintaan ditutup sebagai tidak tersimpan. Tidak mengarang kepastian dari jaringan/403.

Sisa sebelum kualifikasi: kontrol Native/HTTP/browser/pasang-pulih dan konflik akses harus dijalankan pada satu
kandidat.44 uji lokal tidak memberikan izin memakai kode ini pada produksi.

A/integrator: inventaris minimum lama saat pemasangan, cocokkan identitas/satuan dan tampilkan aturan aktif; jangan
menghapus atau memindahkan nilai Enteng otomatis. Tambahkan kolom ke pemasang/upgrade/rollback/pemulihan sesuai sumber
ini. Label fakta minimum pada ConnectedMasterPage.tsx ("Stok minimum") perlu menjadi "Referensi minimum lama";
berkas di luar scope B itu tidak diubah sepihak. Pemasangan bersama, registry OW16 dan modul angka A tetap milik A.


Kandidat kualifikasi berikutnya menambahkan113 kasus: semua99 kontrol sebelumnya tetap dipanggil tanpa diubah,
ditambah6 Native,4 dua sesi/tunggu akses,2 HTTP dan2 perjalanan browser. Kontrak tertutup ada di CONTRACT.json;
entry point cp7_ow14b_rule_probe.py. Workflow OW14 memakai satu pekerjaan113, pemasang/pemeriksa/pemulih milik A
berjalan sebagaimana sebelumnya; tidak ada pelonggaran katalog, batas waktu, oracle lama atau izin.

Dua perjalanan komputer/HP menyimpan pilihan rumus, sengaja menghilangkan balasan sesudah server menjawab200,
memuat ulang aplikasi, menolak pilihan berbeda selama hasil belum jelas, mengirim ulang UUID/isi sama, lalu memilih
minimum lama. Balasan kedua juga dihilangkan; akses akun dicabut nyata, fakta disembunyikan dan intent dipertahankan,
kemudian akses dipulihkan untuk mengambil hasil lama. Pemeriksaan Native memisahkan minimum0 dari unknown,
membuktikan pin tidak mengikuti perubahan referensi, dan membandingkan stok fisik saja saat sumber sedang sibuk.
Ini rencana kasus yang sudah ditulis, belum klaim hasil Native113 sampai Original lengkap dibaca.

Pesan pengingat untuk minimum lama yang dipilih kini menyebut aturan itu, tanpa menyebut minimum rumus atau
mengurangi dengan PO yang belum diterima. Kontrol panjang nama memangkas label, mempertahankan angka/aturan;
label panjang bersifat SYNTHETIC_LABEL_ONLY. Kegagalan pertama sebelum perbaikan disimpan di
local-first-wa-wording-failure.json. Enam kelompok SQL lokal kembali lulus;44 uji klien/DOM, TypeScript/CSS lulus.
Assertion teks lama tetap dipertahankan; kegagalan wording penjelasan singkat juga disimpan sebelum diperbaiki.
