# V7 — volume Native lulus; paket31 masih30/31

**Hasil aktual df6bd877/tree55ee4091:** run39945772181/job120387939390,
volume2000 produk/202000 gerakan7589/2831/2851ms PASS, batas8s dan kedua
hangat≤3000ms tetap. Native15/15, race8/8, Auth4/4 dan browser3/4;
paket INCOMPLETE30/31 karena pesan layar desktop, bukan volume.
[Receipt](../ow13c/df6bd87-native31-30.json). Perbaikan pesan5b6ca459,
16a0aeb0/run39993639712 selesai28/31 karena3 jam fixture OW10; seluruh
checked-save baru dan volume7710/2952/2943ms PASS. Contoh positif hari ini
08:00 masih masa depan pada00:23WIB; kini00:00 tanpa mengganti tanggal atau
penjaga Native. Kandidat a15054c2/run39996465132 sedang diuji31. Semua angka melekat
pada kandidatnya; tidak ada klaim SLA hosted atau seluruh pabrik.

**Riwayat alasan dan pembanding V7:**

Native31 pertama44afe80b/run39941715921 memberi volume7409/3150/3122ms,
dua hangat melewati≤3000ms. Native19 dan25 padaa3bf8842 memang pernah
lulus, tetapi hasil itu tidak membuktikan SLA umum atau versi baru ini.

V7 menyatukan total stok dan saldo awal dalam satu agregat. Hubungan invers
reservasi memakai left join terhadap ID unik gerakan, dengan aturan filter
persis yang sama. Availability tanpa known_at untuk hash dibuat satu kali;
ref produk, established_at dan jam capture dihitung satu kali, lalu dipakai
untuk seluruh hari produk. Set identitas caller dibuat sekali (duplicate/
full scope tetap ditolak), dan statistik historis diambil sekali.

Tidak ada rumus, scope, stock sample/cap, aturan, angka kebijakan, hash input
atau batas yang dihilangkan. Perubahan badan mesin memang mengganti engine
hash sehingga cache lama invalid; nilai dan kedua hash stock_summary tetap
harus persis sama. Tidak ada body Native/frozen SOURCE atau berkas bersama A
yang diubah. Modul input9 fungsi tetap; tidak menambah objek/grant/endpoint.

35/35 inputs/cache/evaluate dan9/9 actual caller SQL lokal PASS; seluruh
202000 gerakan,2000 produk dan60000 hari utuh. Perbandingan SQL v6 dari
commit a3bf8842 pada fixture lengkap meminta seluruh JSON beserta kedua hash
identik. API/admission/invers22/reapply/afteruse lokal dan scanner dua fungsi
PASS. Nilai waktu PGlite tidak diklaim sebagai Native SLA. [Receipt lokal](v7-local-preflight.json).

Browser31 diperbaiki tanpa mengubah produk: desktop mengharapkan tepat
HTTP500/code40001/pesan sumber berubah dan no orphan; HP menunggu hasil
commit aktual sebelum memutus jawaban lalu membuka ulang rencana biasa.
Race diberi timeout8s/lock5s dan holder selalu dilepas di finally; pertama
sudah8/8PASS, jadi ini bukan penghambat yang teramati.

Langkah berikut: jalankan Native31 pada satu kandidat baru dengan batas8s/
hangat3s utuh. Simpan seluruh Original, terutama bila gagal; jangan mengubah
status31 pertama28/31. Rantai A, caller afteruse backuprestore, factory3600,
checkedSAVE2000-scale, audit dan production_go tetap OPEN; parent5/16.
