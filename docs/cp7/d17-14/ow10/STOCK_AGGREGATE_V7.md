# V7 — optimasi identik; Native ulang belum tersedia

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
