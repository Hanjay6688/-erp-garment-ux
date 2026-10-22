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

Bukti saat checkpoint: enam kelompok SQL aktual pada adapter ERP/identitas terkendali lulus;31 uji klien/DOM dan
TypeScript/CSS lulus. Bukti lokal bukan Native/login/race nyata. Kegagalan pertama UI lama serta skala serialisasi
tetap disimpan. Nilai800/60/900/1000 adalah fixture, bukan keputusan owner atau angka Enteng.

Sisa sebelum kualifikasi: permintaan simpan harus pulih dengan UUID/isi sama sesudah remount, ditahan bila hasilnya
belum diketahui, lalu kontrol Native/HTTP/browser/pasang-pulih dan konflik akses harus dijalankan. Sumber SQL dan
klien sudah berubah;31 uji lokal tidak memberikan izin memakai kode ini pada produksi.

A/integrator: inventaris minimum lama saat pemasangan, cocokkan identitas/satuan dan tampilkan aturan aktif; jangan
menghapus atau memindahkan nilai Enteng otomatis. Tambahkan kolom ke pemasang/upgrade/rollback/pemulihan sesuai sumber
ini. Label fakta minimum pada ConnectedMasterPage.tsx ("Stok minimum") perlu menjadi "Referensi minimum lama";
berkas di luar scope B itu tidak diubah sepihak. Pemasangan bersama, registry OW16 dan modul angka A tetap milik A.
