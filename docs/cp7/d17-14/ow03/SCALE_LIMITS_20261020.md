# Skala aplikasi — hasil baru2ad, tetap belum memenuhi OW-12

Run39420750772 attempt1/job118620792724, kandidat2ad56e14, **5/5 PASS**
untuk kontrak pengukuran. SQLsourcehash3c0364ce…; pemulihan CP6/advisor PASS.
Receipt lengkap dan ringkasan angka: CI_39420750772_SCALE.json dan
SCALE_39420750772_SUMMARY.json. Ini bukti writer dari salinan Native sekali
pakai, bukan hasil pabrik/produksi, SLA, atau audit independen.

## Klik sampai server selesai dan halaman hasil pertama terlihat

| Target | Riwayat hari | Operasional langsung | Dengan keuangan langsung | Bertahap, keuangan DEFERRED |
|---:|---:|---|---|---|
| 100 | 1 /30 /100 | 1,70 /1,71 /2,12 dtk | 2,72 /2,73 /3,13 dtk | 2,20 /2,22 /2,69 dtk |
| 300 | 1 /30 /100 | 6,09 /6,42 /8,10 dtk | 9,44 /9,99 /11,15 dtk | 5,36 /5,64 /6,45 dtk |
| 1000 | 1 /30 /100 | timeout sekitar8 dtk | timeout sekitar8 dtk | 15,09 /16,78 /20,21 dtk |
| 5000 | 1 /30 /100 | ditolak batas1000 sumber | timeout sekitar8 dtk | 79,40 /88,22 /105,27 dtk |

Waktu ini perjalanan browser, bukan hanya SQL. Untuk5000, hasil server
memuat5000target, 26halaman, dan seluruh26 dibaca/diverifikasi tanpa potongan
sumber atau sampling. Timer pada tabel berhenti ketika hasil pertama tampil;
pengukuran baca halaman berikutnya terpisah, jangan menjumlahkannya secara
diam-diam atau mengklaim timer itu mencakup download seluruh26halaman.

Pada5000, perpindahan halaman berikutnya 0,596–0,834dtk; membuka kembali
hasil selesai 1,261–1,568dtk. Budget lama alat untuk page/open adalah3dtk,
tetapi owner meminta pembacaan rutin1dtk: buka ulang belum memenuhi1dtk.
Progres tahap nyata5000/30dan100hari mulai terlihat3,092/3,035dtk, melewati
3dtk; respons status awal sudah terlihat dalam beberapa milidetik. Jangan
menyamakan acknowledgement awal dengan progres terukur atau hasil lengkap.

**PASS pengukuran bukan bukti semua jalur selesai.** Penolakan yang benar
ditandai HONEST_CAP_REFUSAL; itu bukan COMPLETE_RESULT. Jalur bertahap pada
angka ini menunda keuangan. Belum ada bukti3600/5000 target dengan keuangan,
HPP, pembanding periode dan kecepatan target secara lengkap. OW-12 tetap
BELUM SELESAI. Pengecualian pekerjaan berat bernama tetap dibedakan dari
penerimaan latensi atau izin produksi.

## K6 terpisah

Job118620792566 gagal menyiapkan database/registry, sebelum kasus berjalan.
Permintaan ulang awal ditolak karena workflow skala belum selesai. Sesudah
skala selesai, GitHub menerima ulang **satu job K6 saja**, kode2ad tetap.
Kegagalan awal dipertahankan. Ulang tunggal K6 pada attempt2,
job118654098080 **10/10 PASS**, CP6 restored/advisor PASS, sourcehash
b4adfb3a3f60693427841adff357b65d6819cf51e3208a8bb00ba9f7d858044d
dan identitas produk tetap2ad. Receipt: `CI_39420750772_K6_RETRY.json`.
Status sukses job lain di daftar attempt2 dipakai kembali oleh GitHub;
tidak diklaim sebagai dua belas pengujian ulang baru. Angka skala di atas
tetap berasal dari job118620792724 attempt1.
