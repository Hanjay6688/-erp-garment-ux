# Pemeriksaan lanjutan range SKU — 28 September 2026

Status: **CP6 HOLD; production_go=false; audit_complete=false; CP7 belum boleh mulai.**

Ini pemeriksaan writer atas source efektif dan kasus tambahan, bukan audit independen seluruh ERP. Tidak ada akses/tulisan data production, UAT, atau legacy. Dokumen ini menambah temuan yang belum tercakup pada handoff BF sebelumnya; tidak membuka ulang bug BD/BE yang sudah dinyatakan sembuh oleh auditor tanpa bukti baru.

## Dasar dan batas penutupan

Owner menegaskan empat hal masih terbuka: **alur setelah konfigurasi gratis, seluruh variasi rework/range, paket rilis terbaru, last check CP6.** Hasil writer berikut tidak boleh otomatis menutup empat hal tersebut.

Audit independen pada `6739a2f` menemukan SKU-01 aktif: master SKU menolak FREE/WAIVED Rp0 dengan alasan sah. Skenario range 31–33 menjadi31–34, harga/resep bersama, biaya per ukuran, jual–retur, impor exact-size, desktop/HP emulasi dinyatakan lulus pada cakupan yang diuji. BD140/140 dan BE135 lulus; observasi antrean lock tidak membuktikan data rusak. Rujukan: `SKU_RANGE_INDEPENDENT_AUDIT_20260928.md`, `SKU_RANGE_WRITER_HANDOFF_20260928.md`, audit commit `17e229108ec712ae479f76418615b504c446d67b`.

Satu SKU mengatur harga jual, resep, dan tarif pekerjaan jahit bersama; ukuran menentukan barang fisik dan penerima biaya. **Laundry memakai tarif vendor menurut proses/paket/komponen yang dipilih, bukan harga wajib dari SKU.** Contoh: SKU31–33, stok31=5,32=8,33=3. Tarif jahit127,19 berlaku bagi setiap PCS; finishing hanya3PCS ukuran32 tidak menjadi biaya jasa untuk16PCS. Rata-rata HPP SKU tidak mengubah FIFO/lot penjualan atau ukuran retur. SKU27 yang khusus adalah master terpisah.

## Koreksi dasar laundry — penegasan owner 28 September 2026, 14:59 WIB

Owner mengingatkan bahwa tarif vendor mengikuti jenis cucian yang dicentang. SKU hasil biasanya baru muncul saat finishing; biaya yang kemudian dikenal untuk SKU tersebut berasal dari proses yang benar-benar dijalani. Ini **penegasan aturan lama**, bukan permintaan aturan baru: `cp6-d11-kebijakan-dan-gbd03.md` §4, LAU-DEC05, sudah mencatat keputusan tidak mengaktifkan tarif khusus; Lampiran C6 §3.1 mencatat master per vendor, paket/komponen, dan SKU opsional.

Penegasan lanjutan15:05WIB: daftar jenis cucian dapat panjang; operator memilih checkbox dan harga komponen/proses yang dipilih dikombinasikan. Jika SKU hasil sudah diketahui saat kirim, SKU boleh membantu menarik riwayat kombinasi cucian yang biasa dan referensi biayanya. Ini kebutuhan bantuan pemilihan/riwayat, **bukan master tarif laundry kedua yang menimpa tarif vendor**. SKU tidak dilarang diketahui lebih awal dan juga tidak diwajibkan sebelum laundry. Paket/komponen tetap menjaga penerima jasa aktual, sumber versi harga dan biaya kiriman; rata-rata historis bukan bukti tarif vendor pada tanggal kirim.

Konsekuensi terhadap laporan writer:

- Alasan lama R04/R05 bahwa laundry/celup ulang wajib mengambil tarif master SKU **ditarik dan ditutup sebagai salah klasifikasi**, bukan bug yang harus diperbaiki dengan menambahkan override SKU.
- Referensi SKU boleh diperlukan untuk konteks pekerjaan jahit tanpa memaksa identitas FG final sebelum klasifikasi. Ketiadaan SKU saat laundry bukan kesalahan operator.
- Nilai HPP/biaya historis rata-rata SKU tidak boleh otomatis menjadi tarif vendor untuk kiriman berikutnya.
- Prioritas resolver BF yang sudah dibuat justru perlu dikoreksi/dibuktikan terhadap aturan vendor; lihat R16. Jangan memperluas prioritas yang salah itu ke celup ulang.
- Angka125PASS tetap merupakan hasil eksekusi kasus pada kandidat yang disebut. Sebagian oracle laundry sengaja memakai tarif dari master SKU; hasil itu **tidak membuktikan kesesuaian sumber tarif dengan aturan owner**. Bukti asli tidak dihapus atau diubah menjadi hasil retest baru.

### Apa yang dimaksud belum cukup bukti

| Batas | Bukti yang sudah ada | Yang belum dibuktikan / alasan tetap terbuka |
|---|---|---|
| Alur gratis setelah konfigurasi | Writer telah menguji simpan status, kirim, terima, QC/HPP, replay, HTTP dan browser pada kandidat tercantum | Audit lama berhenti pada master; belum ada retest independen patch ini. Selain itu skenario baru harus memakai harga gratis vendor/komponen yang sah, bukan mengandalkan harga SKU sebagai sumber laundry |
| Kombinasi rework/range | Perubahan31–33→31–34, harga/resep bersama, exact-size, jual/retur dan impor dasar sudah diuji pada cakupannya | Belum rangkaian penuh penambahan anggota pada PO yang sudah mengunci resep, perpindahan saat WIP/BS lalu rework, retur sesudah pindah range dan invoice susulan, maupun semua kombinasi rewash/paket/extra. Ini kekurangan eksekusi kasus spesifik, bukan semua rework dianggap gagal |
| Paket kandidat gabungan | Development BF dan paket BE terdahulu mempunyai bukti masing-masing | Belum satu paket terbaru berisi revisi yang sama, manifest exact, install/upgrade/recovery dan runtime yang diuji sebagai satu kesatuan |
| Last check CP6 | Banyak skenario BD/BE/BF sudah lulus pada versi dan batasnya | Belum pemeriksaan akhir kandidat gabungan beserta sambungan lintasCP dan seluruh temuan yang masih berlaku. Writer tidak menerbitkan izin CP7 sendiri |

Tidak ada empat baris ini yang menunggu owner mengulang aturan tarif laundry. Penutupan harus berdasarkan bukti atau penetapan bahwa temuan tidak berlaku, bukan sekadar mengganti label menjadi PASS.

### PR #30 — diterima dan dibaca, belum retest native

[Draft PR #30](https://github.com/Hanjay6688/-erp-garment-ux/pull/30), head`e9bba9907089546bcf439dd5ace9d86d87c1b592`, menambah satu dokumen audit delta. Tiga pemeriksaan source auditor mendukung prediksi; bukan tiga transaksi PostgreSQL yang telah terbukti. Tidak ada merge produk atau penutupan independen dari pembacaan ini.

- **D-01:** bindingBF tanpa override melewati resolver tarif khusus/fallbackREFUSE. Fixture auditor mengaktifkan MODEL_SIZE; itu konfigurasi bersyarat yang owner saat ini memutuskan tidak diaktifkan. Tetap berguna sebagai pemeriksaan bahwa referensi pekerjaan tidak membypass kebijakan tarif, tetapi jangan mengaktifkan tarif ukuran atau mempertahankan overrideSKU yang salah demi membuat oracle lama lulus. Hubungkan dengan koreksi sumber vendor R16.
- **D-02:** binding wave dibuat sebelum ukuran pindah kelompok, kemudian jasa pertama memakai kelompok lama. Dampak tarif laundry dariSKU harus dieliminasi menurut aturan di atas. Pemeriksaan referensi pekerjaan jahit sebelum pin tetap relevan; pekerjaan yang sudah sah terpin harus mempertahankan snapshot historis. Belum ada hasil native kasus gabungan ini.
- **D-03:** workspace menggunakan tanggal historis untuk produk tetapi revisi terbaru untuk grup/anggota. Ini masalah konsistensi pratinjau bertanggal yang tetap relevan, terpisah dari sumber tarif laundry. Perlu native/API/browser sesuai fixture auditor; belum dinyatakan selesai.

## Temuan yang dikerjakan

### SKU-01 — Rp0 sah tertolak sebelum status harga diperiksa

`scripts/cp6_bf_objects_rates.sql`, `bf_validate_rates_v1`, selalu memanggil parser nominal dengan syarat positif. Akibatnya FREE/WAIVED tidak pernah mencapai pemeriksaan nol dan alasan.

Perbaikan: KNOWN tetap wajib positif; FREE/WAIVED boleh tepat0, tetap wajib alasan; UNKNOWN tetap harusnull. Format nominal tepat dua desimal, negatif, rate nonzero yang diberi status gratis, dan aturan hanya COMPONENT tidak dilonggarkan. UI sudah mengirim `0.00` melalui normalisasi yang tepat.

Sambungan yang diuji: master → binding wave → work snapshot → kirim berharga → cakupan ukuran → receipt → QC → lot/HPP → ringkasan SKU; replay, hak akses saat ini, dua editor, simpan/muat ulang desktop dan HP emulasi. Perubahan tarif berikutnya menjadi berbayar tidak boleh mengganti biaya kiriman gratis yang sudah disimpan.

Oracle writer:16PCS(5/8/3), jahit127,19 =2035,04; laundry0. Fixture writer membeli dan menghabiskan kain100 melalui posting normal. Maka total HPP2135,04, per ukuran667,20/1067,52/400,32, rata-rata133,44. Ini berbeda secara eksplisit dari fixture auditor yang menggunakan prasyarat kain0 dan total2035,04; angka kain tidak disembunyikan agar kedua oracle terlihat sama.

### RANGE-02 — satu ukuran dalam dua slot gambar muncul dua kali pada referensi SKU

Temuan source baru: `get_sku_workspace_v1` membentuk `wave.sizes` dari setiap `cutting_group_size_slots`. Satu ukuran memang boleh mempunyai beberapa drawing; ini terlihat pada kontrak input potong dan contoh slot31-1/31-2. `SkuWaveReferences.save()` lalu memetakan setiap baris itu menjadi referensi SKU. `bf_bind_wave_v1` menolak size_id ganda. Jadi slot gambar disalahartikan sebagai daftar ukuran unik.

Contoh bisnis: ukuran31 gambarA menghasilkan2PCS dan gambarB3PCS;32=8PCS;33=3PCS. Wave mempunyai **4 slot, 3 ukuran, 16PCS**. Daftar referensi tarif harus berisi31,32,33 sekali masing-masing. Semua slot hasil potong tetap ada;31 tetap5PCS.

Perbaikan `scripts/cp6_bf_objects_router.sql`: deduplikasi size_id pada daftar pilihan referensi, sebelum join nama/binding. Tidak menduplikasi atau menghapus hasil potong, tidak mengubah aturan binding satu SKU per ukuran. Uji `scripts/cp6_bf_range_followup.py` memakai SAVE_DRAFT/POST potong normal, membaca public workspace, mengirim payload persis pola UI tanpa deduplikasi di test, memeriksa empat slot/5–8–3/tiga binding/replay/tidak ada FG fiktif.

Hasil kandidat produk `fb8fb11`: RANGE-02 PASS pada native DB (empat slot/5–8–3/tiga binding/replay/tanpa FG fiktif). SKU-01 PASS pada master, invalid matrix, downstream hingga HPP, race, HTTP dan browser; retest desktop/HP `9e04af4` menggunakan produk identik. Bukti gabungan125kasus beserta kegagalan pengujian sebelumnya ada pada [handoff SKU-01/RANGE-02](cp6-bf-free-range-handoff-20260928.md). Ini writerPASS dalam cakupan terdaftar, bukan penutupan independen atau seluruh matriks R03–R15.

## Risiko lain yang ditemukan dari sambungan source

**Tabel ini bukan daftar bug keuangan yang sudah terbukti.** “Batas terkonfirmasi” berarti bentuk data/jalur tersebut memang ada pada source efektif. Dampak transaksi yang masih perlu dieksekusi ditandai secara eksplisit.

| ID / prioritas | Kasus bisnis yang bisa mengenai owner | Bukti source efektif dan implikasi | Oracle/tindakan berikutnya |
|---|---|---|---|
| R03 / tinggi — batas terkonfirmasi | Dua SKU berbeda sama-sama memakai ukuran32 dalam satu wave, misalnya dua merek/warna dengan tarif berbeda | `bf_wave_skus_v1` primary key `(cutting_group_id,size_id)` dan `BF_DUPLICATE_SIZE` hanya bisa menunjuk satu SKU untuk32. Mixed-wave yang sudah PASS memakai ukuran yang tidak bertabrakan, bukan kasus ini | Jangan mengklaim kasus ini didukung. Uji wave nyata owner. Sampai referensi mempunyai pemisah sumber/batch yang memadai, dua referensi tarif untuk32 harus memakai wave terpisah; bukan membagi biaya dengan menebak |
| R04 / alasan lama DITUTUP — sesuai aturan laundry | Laundry berjalan sebelum identitas SKU final diketahui | SKU opsional dan sumber tarif vendor/proses/paket/komponen adalah aturan sah. Tidak memilih referensi SKU tidak otomatis berarti tarif laundry terlewati | Jangan mewajibkan binding SKU untuk laundry. Pisahkan pemeriksaan kelengkapan snapshot jahit dari sumber tarif vendor. Risiko prioritas override BF yang terlanjur dibuat dicatat R16 |
| R05 / alasan lama DITUTUP — sumber vendor bukan bug | Celup ulang barang32 ke warna/target SKU baru | `be_save_redye_v1` membaca `laundry_vendor_rate_versions`; ketiadaan resolver SKU tidak melanggar aturan sumber tarif owner | Jangan menambahkan override SKU hanya agar menyamai BF. Uji biaya tiap attempt, status harga, sumber barang, dan identitas hasil pada rangkaian rework/redye yang relevan; hasil laundry biasa tidak menggantikan bukti rangkaian ini |
| R06 / tinggi — perlu eksekusi | Tambah34 ke31–33 ketika PO sedang berjalan; resep baru berbeda dari resep yang sudah disepakati PO | `bf_bom_for_lot_v1` mengunci resep perPO+SKU; anggota baru yang resepnya berbeda ditolak `BF_PO_NEW_MEMBER`. Ini guard riwayat, bukan bukti data rusak | Uji tambahan34 resep identik harus lanjut; resep berbeda harus berhenti atomik tanpa mengubah lot31–33. Lanjutkan sampai QC/HPP, bukan hanya simpan master. Revisi PO yang sah harus jelas; jangan menonaktifkan guard supaya lolos |
| R07 / tinggi — perlu eksekusi | Ukuran34 pindah SKU saat barang masih WIP/BS; rework dilakukan sesudah pindah | Work memilih SKU dari binding wave; fallback rework bisa memilih keanggotaan pada tanggal kirim. BOM lebih dulu mencari komitmen physical product, lalu pinPO+SKU. Titik waktu dan sumbernya berbeda | Uji satu ukuran34 sudah punya komitmen, satu belum; mandor sama/berbeda; master lama/baru berbeda. Tarif/resep sumber yang sah harus dapat ditelusuri dan lot lama tidak dihitung ulang tanpa koreksi |
| R08 / tinggi — perlu eksekusi | BS sebelum FG pada wave multiSKU tetapi produk/ukuran BS belum diketahui | `bf_group_sku_v1(group,null)` hanya menemukan SKU bila wave berisi satu SKU; `bf_snapshot_matches_v1` tidak menebak pada multiSKU. Form BS membolehkan produk belum diidentifikasi | Uji klasifikasi2PCS dari wave duaSKU. Wajib minta sumber yang cukup atau menolak sebelum entitlements/rework; jangan memilih tarif snapshot pertama atau membayar seluruh wave |
| R09 / sedang — jalur lama terkonfirmasi | Kode SKU komersial berbeda dari kode physical product lama, atau anggota dipindahkan ke kode SKU lain | Master/HPP memakai BF, tetapi workspace konversi dan resolver impor mencari `products.sku`; keduanya belum menyelesaikan kode melalui master komersial. Master BF tidak mengganti teksSKU di semua physical product | Uji pencarian/input dengan kode komersial baru +size32. Pastikan operator menemukan produk yang benar. Jangan menyamakan masalah label/resolusi ini dengan mutasi stock ledger; importer tetap harus memilih satu identitas historis tepat |
| R10 / tinggi — cakupan UI belum connected | Penjualan1lusin untuk singleton27, range3/4/5 ukuran atau ukuran sangat laku saja | Helper menerima jumlah anggota aktual:12;4/4/4;3/3/3/3;5 ukuran meminta manual bila tidak habis dibagi. Halaman `SalesPages.tsx` masih simulasi existing, meski engine jual/retur telah diuji native | Connected sale harus membawa qty per ukuran yang direview, expected stock/reservation, harga bersama, request replay. 1lusin bukan perintah memproduksi/mengambil ukuran saudara yang tidak dipilih. Jangan menganggap browser helper sebagai bukti posting penjualan |
| R11 / sedang — perlu eksekusi | Retur ukuran34 dari penjualan sebelum pindah range, setelah master baru dan invoice biaya terlambat | Pengelompokan HPP membaca keanggotaan pada tanggal laporan; retur/cost memakai lot/allocation asal. Bukti jual–retur sebelumnya tidak otomatis mencakup pindah group di tengah rangkaian | Jual4×34, pindahgroup, biaya terlambat+160, retur1×34: hanya lot/ukuran34 asal bertambah; totalFG+COGS konservatif; laporan sebelum/sesudah tidak menghitung satu lot dua kali |
| R12 / sedang — perlu eksekusi | Impor cutover yang memuat versi identitas lama dan baru dengan kode/range sama | Resolver BF mewajibkan satu physical identity dan tidak meratakan aggregate. Resolver historis memakai `effective_from<=cutover`; lebih dari satu kandidat sengaja ditolak sampai disambiguasi | Uji dua versi identitas, size32, merek sama/berbeda; exact product_id harus menjaga sumber historis. Total12 tanpa rincian ukuran tidak boleh otomatis menjadi4/4/4 pada saldo historis |
| R13 / sedang — perlu eksekusi | Sebagian kiriman rangeBS, rewash beberapa kali, paket+extra hanya ukuran32, lalu invoice/koreksi/claim | Laundry menyimpan shares exact-size dan provenanceSKU; jalur rework/redye/claim mempunyai source sendiri. Kombinasi lintasjalur belum semua tercakup | Ikuti penerima jasa setiap attempt; bukan jumlah anggota range. Pastikan gratis tidak menjadi UNKNOWN, paket included tidak ditagih dua kali, pembulatan total tepat dan invoice/reversal tidak menghapus sebab biaya |
| R14 / sedang — perlu eksekusi | HPP range yang stoknya tersebar gudang/grade, ada ukuran nol stok dan biaya belum lengkap | `get_sku_hpp_v1` memakai nilai/qty sisa lot dan filter lokasi/grade yang sama; biaya dihitung menurut versi yang tersedia saat laporan. Ada perbedaan waktu fisik vs waktu kalkulasi | Uji qty5/8/3 pada dua lokasi, stok34nol, satu biaya UNKNOWN dan invoice susulan. Nilai tak tersedia tetap terlihat, bukan HPP0 atau pembagian rata jumlah ukuran. Tentukan tanggal laporan secara eksplisit |
| R15 / gate — belum selesai | Development BF bagus tetapi paket yang dipasang hanya releaseBE lama | BF masih `supabase/dev/cp6_bf_t1_family.sql`; paket BE terdahulu bukan bukti BF terpasang | Kandidat gabungan terbaru perlu paket/manifest exact, clean install, upgrade yang diizinkan, rollback/backup restore, browser dan runtime proof, lalu last check CP6. Jangan memasukkan hashbaru ke laporanlama tanpa menjalankan gate |
| R16 / tinggi — prioritas tarif BF bertentangan dengan dasar laundry; source terkonfirmasi | Wave diberi referensi pekerjaan SKU; vendor punya tarif cucian101,23, tetapi pengaturan SKU lama memuat127,19 atau GRATIS | `bf_laundry_rate_v1` langsung mengembalikan `settings.laundry_rates` ketika binding ditemukan, sebelum membaca tarif vendor, tanpa pemeriksaan LAU-DEC05. `cp6_bf_free_probe.py` malah membuat komponen vendor tanpa versi harganya lalu menggunakan harga SKU. Ini menunjukkan salah dasar oracle/source, bukan bukti kerusakan data live | Perbaiki sumber laundry agar vendor/proses/paket/komponen tetap menentukan tarif tanpa syarat SKU final. Uji binding kosong/terisi, beberapa ukuran, dua calon SKU, tarif vendor berbeda dari metadata SKU, FREE/WAIVED vendor, UNKNOWN, paket/extra dan perubahan master setelah kirim. Snapshot lama tidak boleh ditulis ulang; nilai/reason/versi vendor dan penerima jasa harus terlacak. Belum ada eksekusi oracle baru pada koreksi laporan ini |

## Yang diperiksa dan tidak ditemukan sebagai bug baru dari source ini

- Stok fisik tetap product/size/lot; menggabungkan `identity_root_id` antarukuran justru dilarang. Keanggotaan grup memakai versi dan transfer atomik, bukan parsing string31–33.
- Batas tiga ukuran pada helper penjualan sudah diganti menjadi jumlah anggota aktual. Empat/singleton tidak otomatis terpotong menjadi tiga. Label/contoh demo yang menyebut31/32/33 bukan dengan sendirinya bug backend.
- Laundry tanpa SKU memang sah. Temuan source bahwa BF memilih resolver SKU lebih dulu tidak lagi dianggap bukti perilaku benar; sumber tarifnya harus mengikuti keputusan vendor/proses/paket/komponen (R16).
- Pemeriksaan kelengkapan kerja memakai `wcl.po_component_snapshot_id=s.id`, sehingga posting satu snapshot tidak otomatis menutup snapshot SKU lain hanya karena work_component_id sama.
- Impor sales/custody/pocketCOGS/rework “ambil produk pertama berdasarkan teksSKU” di source BB/BE lama sudah diganti oleh generated BF. Mencari teks `limit 1` pada file historis saja bukan bukti bug kandidat efektif.
- Rework accessory lebih dulu mencari komitmen PO+product/physical root sebelum fallback resep baru. Jangan menyimpulkan semua rework otomatis memakai resep hari ini. Kombinasi yang belum memiliki komitmen itulah yang perlu tes R06/R07.

## Urutan pekerjaan dan bukti penutupan

1. Tuntaskan SKU-01 dan RANGE-02 dengan hasil native/HTTP/browser/race yang benar-benar dibaca per kasus. Angka workflow hijau saja tidak cukup.
2. Koreksi prioritas tarif yang keliru di R16; jangan menghidupkan kembali alasan R04/R05 yang sudah ditarik. Tindaklanjuti resolusi kode komersial R09 tanpa mengubah identitas historis. Kasus overlap R03 hanya relevan bila dua referensi pekerjaan berbeda memang dibutuhkan; ini bukan alasan memaksa SKU final sebelum laundry.
3. Eksekusi matriks PO sedangjalan, perpindahan group, rework/BS, retur lintastanggal, impor historis dan cakupan jasa parsial R06–R14. Gunakan jumlah tidak rata agar bug pembagian rata tidak tersembunyi.
4. Kualifikasi paket kandidat gabungan dan last check CP6. Auditor/owner menutup temuan berdasarkan bukti retest mereka; writer tidak menerbitkan izin CP7 sendiri.

Tidak ada klaim “semua kemungkinan sudah aman”. Hasil yang menenangkan harus berupa invariant stok/nilai/asalbiaya yang terbukti dan batas yang jelas, bukan janji bahwa range hanya masalah string.
