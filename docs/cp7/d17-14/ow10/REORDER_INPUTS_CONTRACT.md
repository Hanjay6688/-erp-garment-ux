# OW10 — sumber riwayat yang sama untuk ROP (23 Oktober2026 WIB)

`scripts/cp7_reorder_inputs/history.sql` menyiapkan input ROP lewat fungsi
histori dan target Native yang sebenarnya. Tidak mengulang rumus penjualan,
ketersediaan, permintaan, lead, cadangan atau target. Ini helper privat murni;
**belum mengganti compute/pemanggil ROP atau dipasang oleh bundle A**.

Satu tangkapan Native lengkap +query tanggal/pengelompokan tertutup masuk ke
history_prep/events_validate/history_validate. Batas targets/history-cells/
events dan penolakan sumber tetap milik mesin lama. Ketersediaan dan riwayat
diproses per chunk dari batas asli12.500 sel; seluruh baris stok dibaca oleh
history_stock, target disusun baseline_rows yang sama. Tidak membuat job,
menulis ERP, menyaring scope alokasi atau menjalankan analisis keuangan.

Hasil `cp7.reorder-native-inputs.v1` memuat query, waktu dan hash sumber,
produk/identitas, seluruh riwayat, stok kini dan target. Unknown/censored, inverse jurnal,
retur sebagai informasi terpisah dari permintaan bruto, pilihan profil manual
serta nol yang diketahui mengikuti Native. SQL immutable invoker, owner
cp7_capture, search_path kosong/UTC; role luar tidak mempunyai akses.

Enam kelompok awal SQL lokal lulus; pembandingnya **history_build utuh yang lama**,
bukan salinan orkestrasi helper. Seluruh JSON riwayat/stok dan target dari
baseline_rows cocok. Fixture420 produk/12.600 hari memaksa dua chunk dengan
semua produk/hari tetap ada; ini bukan ukuran pabrik atau SLA. Kasus stok90
→0→90 di hari sama menjadi STOCKOUT; perhitungan ROP lama yang hanya melihat
stok awal hari akan menganggap hari itu tersedia. Profil manual, mean0,
retur4/gross10, pembatalan dan perubahan periode/profil juga diperiksa.

Setup pertama berhenti sebelum kasus karena harness ikut memuat reader Native
yang memerlukan tabel run. Kini hanya dua fungsi murni yang diambil lengkap;
kode produk/oracle tidak dilonggarkan. Receipt kecil
`local-reorder-inputs-first-setup-failure.json` tetap disimpan.

## Kompilasi titik dan API privat

`points(native_inputs,defaults,leads,manuals)` sekarang tersedia. Profil Native
yang ditinjau mempertahankan **seluruh target JSON persis**, termasuk pilihan
mean manual/nol, lead dan satu cadangan. Titik ROP mengambil reorder_point_pcs
dari hasil itu. Lead terukur tidak diam-diam mengganti pilihan lead profil.

Produk tanpa profil memakai aturan ROP yang sudah ada (14 hari tersedia,
service90/95/99%, lead terukur dari≥3 grup), dengan **riwayat Native yang sama**
dan kernel target yang sama. Review0 di jalur ini hanya horizon ROP; bukan
asumsi periode tinjau produksi. Full target Native yang belum ditinjau tetap
unknown. Nol yang terbukti tetap0. Identitas/profil yang berubah tidak diam-diam
beralih ke aturan default. Angka lead wajib berasal dari tangkapan server yang
baru; helper murni tidak membuktikan keaslian input caller.

Override manual mengganti titik, bukan menambah cadangan.0 aktif berarti tidak
memicu; null berarti hapus override. Versi/ukuran produk berubah membuat titik
unknown dengan referensi manual lama tetap tersedia. Target produksi tidak
diubah diam-diam untuk mengikuti override; alokasi WIP harus diikat eksplisit.
Pemilih memberi `supply_alignment=NATIVE_TARGET` hanya untuk target profil tanpa
override. Nilai default/manual tidak mendapat klaim keserasian tersebut.

Selection_hash mencakup sumber Native, query, default, seluruh lead/manual dan
versi compiler. Ini identitas pemilihan, **bukan bukti sumber masih segar**;
caller masih wajib mengambil sumber baru, memeriksa hak sebelum/sesudah dan
engine/dependensi sebelum memakai cache. JSON privat tidak boleh disalurkan
mentah ke facade gudang.

API `install_delta/verify/admit_catalog/rollback_preuse` tahap v4 menambah1 schema dan
6 fungsi invoker (3 immutable,3 stable), tanpa body lama/tabel/kolom/Native DML/RPC/cron.
Dua belas badan Native yang dipanggil dipin; owner/ACL/body/config baru diperiksa.
A tetap memegang transaksi/envelope/global after-use guard. Helper stateless
tidak menyimpan bisnis; invers menolak sebelum DDL bila masih ada pemanggil
SQL terpasang. Balikkan lapisan caller dahulu sesuai guard/rantai A; tidak
menghapus evaluasi/riwayat agar invers diizinkan.

Bukti kini **22/22 kelompok lokal PASS**, termasuk pemasang aktual/katalog22
apply/admit/inverse/reapply dan penolakan saat caller SQL fixture masih ada.
Ini kontrol dependensi caller, bukan klaim pemakaian Native telah dikualifikasi.
Perubahan yang akan tampak sesudah caller dipasang: hari stok habis di tengah
hari dikeluarkan dari latihan; mean manual dan nol dari profil benar dipakai;
lead profil yang dipilih sama dengan Native. Default lama hanya untuk produk
tanpa profil, dengan labelnya sendiri. Caller hidup **belum berubah**.

## Sumber server dengan satu waktu tangkap

`source_within(bound)` kini membaca sumber baseline Native, setting yang aktif,
lead terukur dan override manual dalam satu pernyataan/snapshot. Query AS_SOLD
berakhir kemarin WIB dan memakai window aktif dari setting. Lead memakai
median lot PRODUCTION/QC posted/grup issued dalam365 hari, minimal3 grup;
angka tersebut menjadi null jika belum terbukti. Profil tetap pilihan utama
compiler. Manual mengambil revisi terakhir yang tercatat pada waktu capture,
bukan nilai yang diberikan klien atau revisi masa depan.

Engine_hash meliputi badan fungsi perencanaan/target/penghitungan/pembaca;
context_hash meliputi fakta/profil/policy, query/default, lead/manual dan engine.
Kode atau data berubah membuat konteks berubah. INCOMPLETE dipertahankan;
batas produk1..5000, tidak dipotong agar tampak lengkap. Helper privat ini
belum memeriksa hak seorang pengguna gudang: facade masih wajib memeriksa
akses sebelum/sesudah dan menyalurkan agregat yang diizinkan.

Tiga kelompok sumber baru menjalankan **badan source baseline Native yang
sebenarnya**, fungsi setting sebenarnya dan SQL lead/manual sebenarnya di
tabel fixture. Adapter di bawah sumber Native tetap terkontrol. Median4 hari
dari5 lot/3 grup, pengecualian QC draft/reversed/lot masa depan/nonproduction,
manual as-of capture, lead kurang3 grup dan perubahan kode/hash diuji; role
cp7_capture non-superuser membaca hasil sama. Ini belum bukti Native/Auth
atau waktu pabrik. Setup/API22 kini lulus dengan empat fungsi tahap v3.

## Seluruh pergerakan stok, tanpa batas array mentah

`stock_summary(products,captured_at,query)` membaca seluruh pergerakan yang
terlihat pada kedua sumbu waktu, mengelompokkan stok awal, perubahan harian dan
saldo minimum di dalam hari. Aturan, urutan physical_at/book_order/id, grade,
waktu pendirian produk dan refs sama dengan history_availability Native.
Stok fisik membuang reserve dan inversenya; stok bebas memasukkan keduanya
seperti sumber Native. Helper ini tidak memanggil penulis atau rumus uang.

Ini diperlukan karena sumber Native lama membatasi array mentah50.000, sedangkan
kontrol SS1_VOLUME mempunyai202.000 pergerakan. Agregasi SQL membaca semuanya;
cap target5.000 dan grid500.000 tetap. Native capture yang INCOMPLETE **tidak
diubah menjadi COMPLETE** oleh helper ini. Caller berikut harus membuktikan
kelengkapan sumber lain/identitas sebelum memakai ringkasan tersebut untuk ROP.

Empat kelompok stok baru lulus. Seluruh JSON ketersediaan dan kedua angka stok
cocok dengan fungsi Native utuh pada fixture kecil, termasuk reserve/inverse,
dua sumbu waktu dan intraday UNKNOWN. Fixture SQL202.000 pergerakan/2.000 produk
memberi60.000 hari lengkap, seluruh stok bebas450; tidak ada sampling atau
perubahan flag capture Native. Angka waktu lokal tersimpan hanya sebagai
pengukuran PGlite, bukan Native/Auth atau SLA pabrik. Data_hash membuang hanya
label known_at dari identitas ringkasan agar jam bergerak sendiri tidak dianggap
perubahan angka; stok yang benar berubah tetap mengubah hash.

Pemasang pertama tahap ini menolak tanda tangan yang memakai singkatan
timestamptz, sedangkan katalog PostgreSQL menulis timestamp with time zone.
Nama katalog kini tepat;22 grup tidak dikecualikan. Kegagalan pertama disimpan
di local-reorder-stock-first-installer-failure.json.

Berikutnya: lengkapi adapter stok ringkas ke riwayat/target Native tanpa
mengubah status capture mentah, lalu sambungan compute ROP, cache perubahan
yang aman, proyeksi WIP yang serasi, label waktu/kandidat serta Native/performa. Pengingat stok bebas harus
tetap tiap menit tanpa menunggu job analisis besar. Parent5/16, OW10 OPEN.


## Pembacaan lengkap dan snapshot untuk cache

`read_points(bound)` sekarang menyambung sumber server →riwayat →target →titik.
`compile(source_snapshot)` bersifat immutable agar caller dapat mengambil satu
snapshot, mencocokkan context_hash cache lalu menghitung hanya ketika berubah.
Compiler tidak membaca database kedua kali. Caller tetap bertanggung jawab
atas sumber server baru/hak saat baca; mengompilasi snapshot lama bukan bukti
kesegaran. Belum ada tabel/cache/caller ROP yang dipasang oleh tahap ini.

Sumber COMPLETE kecil menghasilkan seluruh JSON input/titik sama persis dengan
jalur Native. Bila **hanya** array stok mentah mencapai50001, sumber server juga
membawa ringkasan SQL stok lengkap dengan waktu/query sama. read_points tetap
mencatat native_capture_status=INCOMPLETE dan menandai jalur khusus, tanpa
mengubah status Native atau mengisi array stok kosong. Seluruh guard Native
lain dipertahankan: jumlah produk/unik root, identitas komersial sekarang dan
saat jual, empat cap koleksi lain50.000, serta tepat satu jurnal asli untuk
setiap penjualan final. Badan history_source_within sekarang ikut pin DB.

Hari tersedia tetap aturan Native penuh; event/jurnal, stok fisik vs reservasi,
pengurangan draft sekali, history_rows dan baseline_rows memakai kernel asli.
Mismatch reservasi, batas grid/target, snapshot/query dan jumlah baris yang
berkurang tetap ditolak. Hash sumber jalur ringkas diberi identitas terpisah;
ini bukan hash operasional analisis besar atau izin memakai WIP lama.

Seluruh202.000 pergerakan/2.000 produk kini melewati jalur lengkap menjadi
60.000 hari riwayat,2.000 target dan2.000 titik; bukan hanya stock_summary.
Semua stok bebas450, pilihan profil nol tetap0, tanpa penjualan/jurnal fiktif.
Perubahan satu pergerakan **di luar**50001 baris mentah mengubah key lewat hash
ringkasan lengkap meskipun JSON array mentah sama. Snapshot beda waktu ditolak.
PGlite lokal membutuhkan sekitar10detik untuk kompilasi penuh; ini **bukan
Native/Auth/SLA3detik**. Cache hit belum diuji karena caller/cache belum dibuat.

Harnes sumber kini memuat badan history_source_within dan baseline.source_within
aktual atas tabel ERP fixture; adapter profil/identitas tetap terkontrol.
Sebelas penolakan guard disuntikkan lewat adapter sumber sementara, kemudian
badan Native dipulihkan dan hash diperiksa tepat; ini bukan kualifikasi Native.
Installer/admission/inverse/reapply22 serta guard dependensi caller tetap lulus.
