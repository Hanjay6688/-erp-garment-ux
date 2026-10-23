# Layar OW-09 yang ditahan

Tahap `scripts/cp7_ow09_lists/` lulus Native8 8/8 (run 39885622953, `559ac537`). Bagian layar (8 daftar mengirim kunci urut,
status/jenis dan cari ke pembaca, menampilkan jumlah dan total dari server) belum digabung ke `claude/d17-14-uang`: layar itu
hanya bekerja bila tahap OW-09 terpasang, dan alur browser lama di integrasi (p11 sales, f03 cash, p10, transaction-source, dll.)
memasang CP7 tanpa tahap itu sampai rantai OW-15 memasangnya. Menggabung sekarang akan mematahkan alur-alur itu.

Isi (dibuat dengan `git format-patch`, berlaku bersih di atas cabang ini):
- `0001-…`: tujuh layar, kontrak, uji DOM, RecordTools/recordList, fixture keuangan, oracle browser (asal commit `d8cd1960`).
- `0004-…`: Nota Ambil Aksesori (asal commit `2a0a6fb4`).

Pasang bersama tahap OW-09 di rantai OW-15: `git am docs/cp7/d17-14/ow09/screens/0001-*.patch docs/cp7/d17-14/ow09/screens/0004-*.patch`,
lalu jalankan ulang alur browser yang pinnya berubah.
