# V6 sudah lulus Native25 dan Native19

Pada kandidat a3bf8842/tree68c6d2b8, dua run aktual selesai PASS:
Native25 run39939451330/job120367011308:25/25, waktu sintetis2000/202000
6133/2663/2679ms; Native19 run39939451231/job120367010911:19/19,
6305/2697/2733ms. Dua hangat masing-masing tetap≤3000ms; statement8detik
tidak berubah. Seluruh ID/status/deklarasi, sumber24/28 berkas, invers22,
6 salinan authority masing-masing, restore/advisor/lima gate paket tepat.
[Receipt caller](a3bf884-native19-pass.json),
[receipt checked25](../ow13c/a3bf884-native25-pass.json).
Ini uji sintetis kandidat tersebut, bukan jaminan waktu umum/factory3600/
checked-save skala2000/rantai A/audit. Kegagalan pertama24/25 tetap disimpan.

# V6: buang pekerjaan berulang, bukan stok atau pemeriksaan

Native25 pertama bf98947e:24/25, termasuk6 checked-save baru PASS. Kontrol
ROP2000/202000 gagal statement8detik. Hasil pertama/Original/log dipertahankan
di receipt ow13c/bf98947-first-native25-24.json; batas tidak dinaikkan.

Sumber Native lama membentuk JSON untuk50001 pergerakan, lalu adapter overflow
membuang seluruh prefix itu dan memakai ringkasan SQL yang membaca202000 baris.
V6 menurunkan2 fungsi privat dari badan Native yang dipin. Count memakai FROM,
JOIN, WHERE, jam dan scope produk yang persis sama, berhenti pada50001. Hanya
bila terbukti melewati50000, JSON prefix tidak dibentuk. Ringkasan SQL tetap
membaca seluruh pergerakan. Stock raw kosong diberi bukti eksplisit
stock_raw_omitted=true/stock_rows_at_least=50001, bukan stok0. Tanpa bukti atau
ringkasan lengkap yang cocok, compile dan current-stock menolak.

Native function asli tidak diubah. Semua query/field/predicate nonstok pada
turunan tetap byte-derived; predicate COMPLETE juga memperhitungkan overflow
yang terbukti. Native tetap INCOMPLETE ketika batas stoknya tercapai, sedangkan
jalur summary membaca lengkap. Tidak ada sentinel/demand/gerakan palsu,
kenaikan cap, potongan data, perubahan rumus atau penundaan cek stok hari ini.
Generator memeriksa bentuk sumber;12 pin dependensi Native sebelumnya tetap tepat.

Modul inputs v6:9 fungsi privat (sebelumnya7),0 hook/endpoint/DML baru. API
install/admit/inverse22 lokal lulus, termasuk dependensi caller dan guard
setelah pakai.35 inputs/cache/evaluate,9 caller/RPC SQL,65 klien lulus.
35 kontrol mempertahankan expected lama; fault injection mengikuti helper
turunan yang kini dipakai. Oracle raw50001 tetap diuji pada fungsi Native asli;
turunan dibuktikan identik penuh pada nonstok, status dan hasil akhir.
Guard ditambah untuk bukti overflow hilang atau hanya50000. Local32/35 pertama
dan kesalahan urutan pemasangan awal tetap tersimpan, tidak dinyatakan hijau.

Lokal PGlite2000:60.000 hari/202000 baris/seluruh target dan point tetap; stok
450 tepat. Cache dingin13,5detik/hangat4,8detik pada runtime lokal, **bukan SLA
Native**. Perubahan di luar prefix lama tetap mengubah hash; stok hari ini
berubah tanpa mengulang histori. Hash engine/context memang berganti karena
implementasi baru; angka target/ROP tetap. Status V6 Native masih belum diuji.

A tetap menggabungkan inputs→reader→caller. Installer, frozen9, registry,
generator tipe, uang/HPP dan jadwal bawaan tidak diubah B. Full A/restore setelah
pakai/factory3600/checked-save race dan browser tetap terbuka. Parent5/16.
