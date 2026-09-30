# Analyzer hasil potong — usulan producer dan cangkang F05

Instruksi owner 30 September 2026: keluarga bahan menjadi basis; kombinasi ukuran harus dibedakan; **lebar opsional, kosong tetap boleh dianalisis dan tidak menjadi syarat menyimpan potongan**. Hasil rendah menjadi tanda cek lapangan dengan reasoning. Tidak menyimpulkan kehilangan, kecurangan atau BS sebagai penyebab tanpa bukti.

Implementasi saat ini adalah kartu consumer pada pratinjau P14, kontrak privat dan fixture. Model pembelajar dari transaksi belum dibangun/terhubung. Kontrak shared dan writer F03/F04 tidak diubah. Angka fixture bukan range pabrik dan tidak diambil dari benchmark pakar.

## Bahasa bayi

Mesin bertanya: **“Bahan ini, pola ini, meter segini, dengan campuran ini biasanya jadi berapa?”**

1. Kelompokkan bahan menurut identitas yang benar: merek/pabrik/varian dan revisi spesifikasi. Riwayat perilaku/susut bahan menjadi basis awal, bukan asumsi bahwa semua batch selamanya identik.
2. Ingat campuran, bukan cuma ukuran terkecil–terbesar. `28×2 + 29×2 + 30×2`, `28×1 + 29×3 + 30×2` dan `30×6` berbeda. Campuran yang berubah bisa mengubah susunan marker dan pemakaian bahan.
3. Cari kejadian sebanding atau model campuran yang telah lolos pengujian. Jumlah PCS dan meter per ukuran bukan rata-rata seragam. Model bisa belajar pengaruh porsi ukuran dan interaksi campuran/lebar, bila riwayat memiliki variasi yang cukup.
4. Beri **rentang hasil kejadian baru**, lalu bandingkan dengan hasil potong yang sudah lengkap. Sebelum hasil lengkap, hanya perkiraan yang boleh tampil; isian kosong bukan nol.
5. Kalau campuran baru belum didukung data/model, bilang “belum dapat dinilai”. Satu tahun kalender tidak otomatis berarti cukup kejadian sebanding.

Jika semua histori selalu 2:2:2, pengaruh ukuran 28/29/30 secara terpisah belum dapat dipastikan. Mesin tidak boleh pura-pura tahu konsumsi 30 semua hanya dari rata-rata campuran tersebut. Diperlukan histori campuran yang bervariasi atau informasi geometri pola/marker yang sah. Susunan slot yang bertukar urutan tidak otomatis menjadi campuran baru; marker/layout yang berbeda tetap dapat mempengaruhi yield.

## Lebar opsional

| Kondisi | Perilaku yang ditetapkan |
| --- | --- |
| Lebar kosong | Basis `WITHOUT_WIDTH`: keluarga bahan + pola + meter terpakai + campuran, dengan variasi batch yang belum dipisahkan. Tidak mengisi lebar nominal diam-diam atau memakai nol cm. |
| Lebar diisi | Basis `WITH_RECORDED_WIDTH`: tambahkan lebar sebagai pembeda. Hasil lama tidak dipakai ulang. Lebar tercatat tetap dibedakan dari ukuran fisik yang dibuktikan. |
| Lebar keliru format | Minta koreksi atau kosongkan untuk analyzer. Tidak menambah syarat transaksi cutting. |
| Riwayat/validasi tidak cukup | Tahan rentang. Ini terpisah dari lebar kosong. |
| Campuran/varian/kondisi di luar dukungan | Tahan atau tampilkan estimasi eksploratif terpisah jika kelak diizinkan policy; tidak memberi label normal/abnormal pasti. |

Tanpa lebar, range empiris mengandung variasi lebar yang tidak diobservasi serta variasi proses lainnya. Model width-aware tidak dijamin selalu lebih sempit atau lebih akurat; ia harus mengalahkan baseline pada data baru sebelum dipromosikan. Jangan menganggap range historis sebagai batas desain ideal: pencatatan bias atau masalah yang sudah lama berulang dapat ikut membentuk kebiasaan.

## “Kenapa sedikit?” dibedakan dari “ada selisih”

| Bukti | Yang bisa dinyatakan |
| --- | --- |
| Panjang tersedia tercatat berbeda dari pengukuran fisik pada slice roll yang sama | Ada selisih panjang yang perlu rekonsiliasi; penyebabnya belum diketahui. Bedakan pemakaian terdahulu, retur/sisa sah dan roll yang memang kurang. |
| Lebar diisi berbeda dari pembanding | Lebar adalah pembeda input; belum membuktikan bahwa lebar adalah penyebab tunggal. |
| Panjang/lebar tercatat sama tetapi hasil rendah | Ada selisih hasil terhadap kebiasaan. Catatan dimensi yang sama tidak membuktikan dimensi fisik sama. |
| Lebar tidak diisi | Hasil dapat dibandingkan, tetapi tidak bisa memisahkan penyebab lebar, panjang sebenarnya, susunan marker, cacat, salah input atau kehilangan. |
| Ada cacat/scrap/recut yang tertaut | Tampilkan bukti tahap yang benar dan jumlahnya. BS laundry kemudian tidak menjadi bukti cacat saat cutting. |
| Hasil terlalu tinggi | Periksa kelengkapan komponen, mutu, ukuran dan pencatatan meter. Tidak otomatis dianggap lebih efisien. |

Contoh panjang 100 M di catatan versus 80 M diukur serta contoh range 80–120 PCS pada kartu adalah **kasus tampilan sintetis**, bukan kesimpulan usaha. Meter terpakai lebih rendah saja tidak membuktikan roll pendek; bisa ada sisa. `qty_reported_remaining` yang dihitung dari keluar − terpakai juga bukan bukti sisa fisik yang diukur independen. Input yang sengaja dipalsukan tidak dapat dibuktikan palsu hanya dari input yang sama; perlu pemeriksaan fisik/referensi independen saat ada tanda selisih.

## Producer yang dibutuhkan setelah data tersedia

- Satu observasi per slice roll/kejadian cutting yang selesai, dengan hasil per ukuran dan revision lineage. Draft, replay, pembagian pickup, completion berikutnya, serta koreksi/reversal tidak menjadi observasi ganda. Simpan waktu fisik, waktu diketahui, source/hash/model/policy/access versions.
- Gunakan komposisi marker/rencana yang diketahui sebelum hasil, bila tersedia. Hasil per ukuran sesudah potong tidak otomatis membuktikan rasio gambar yang direncanakan. Jangan memakai label “normal” atau hasil batch saat ini sebagai training input untuk meramal dirinya sendiri.
- Baseline pertama: pembanding keluarga bahan/pola/komposisi/panjang, dengan kuantil atau metode lain yang memenuhi dukungan data. Lebar/marker/aturan arah/susut aktual adalah fitur tambahan ketika tersedia; missingness tetap eksplisit. Konversi unit ke M harus punya sumber, tidak diasumsikan untuk YARD/KG/ROLL.
- Model campuran kandidat: regresi konsumsi/yield yang memperhitungkan porsi ukuran, panjang, pola/varian dan interaksi susunan. Uji kemampuan generalisasi ke rasio baru; interpolasi bukan jaminan. Jangan sekadar mengalikan “semua ukuran makan meter sama”.
- Pisahkan training, kalibrasi interval dan evaluasi pada blok waktu/batch yang baru. Jangan memecah ukuran dari roll yang sama ke train/test. Catat support, interval coverage, lebar interval, bias dan false-alert menurut bahan/pola/campuran. Pilih policy toleransi alert secara eksplisit; tidak menetapkan n minimum/akurasi/ambang ±10% tanpa bukti.
- Model yang lebih rumit harus mengalahkan baseline pada data baru. Jika model/data drift atau kontrak belum lengkap, kembalikan status unavailable dengan alasan. Hasil/normal-range lama tetap auditable dan tidak ditulis ulang; histori yang bermasalah tidak boleh dihapus supaya skor bagus.
- Hasil consumer mengikat input lengkap, actor scope, epoch, run dan model/policy. Perubahan bahan, pola, rasio, meter, lebar atau revisi sumber membatalkan penilaian lama. Produksi/save tidak menunggu analyzer. Tombol/trigger final pada form asli merupakan integrasi P04/P14, bukan perubahan cangkang ini.

## Data yang sudah terlihat pada pembaca cutting

`src/cuttingPersistence.ts` membawa roll/material/unit/supplier, pattern/revision, qty issued/consumed/reported remaining, size slots/drawing number dan yields per slot. `ConnectedCuttingPage.tsx` menyimpan sisa sebagai issued − consumed dan payload drawing_no saat ini 1. Reader ini belum membawa lebar efektif per roll/batch, pengukuran sisa independen, keluarga merek/pabrik/susut terverifikasi, marker geometris, atau bukti cacat cutting yang diperlukan untuk atribusi sebab. Ini batas DTO yang dibaca, bukan klaim semua field tersebut tidak ada di database.

Lebar tetap pengayaan opsional. Mapping keluarga bahan dan komposisi/slot historis harus dibuktikan integrator; tidak menyimpulkan rasio marker hanya dari label range ukuran atau drawing_no. Cangkang tidak menambah kolom/mutasi SQL ataupun memasang producer F04 secara diam-diam.

## Riset dasar dan pilihan desain

- [Lectra — roadmap cutting-room waste](https://www.lectra.com/en/library/your-7-steps-roadmap-to-reduce-material-waste-in-your-fashion-cutting-room): vendor membahas spesifikasi kain/pola, lebar, susut, arah/motif, mixed-size marker dan pemantauan yield. Ini mendukung pemilihan fitur, bukan angka yield pabrik Hansen. Tidak mengadopsi persentase waste umum vendor sebagai ambang alert.
- [NIST — prediction interval untuk satu hasil baru](https://www.itl.nist.gov/div898/handbook/pmd/section5/pmd512.htm): ketidakpastian hasil individual mencakup variasi kejadian baru, bukan hanya ketidakpastian rata-rata. Pilihan desain: range untuk kejadian cutting baru, bukan CI mean yang sempit.
- [Romano, Patterson, Candès — Conformalized Quantile Regression, 2019](https://arxiv.org/abs/1905.03222): kandidat interval adaptif berbasis model kuantil. Tidak mengklaim jaminan coverage langsung berlaku pada data pabrik berurutan atau yang berubah; ketergantungan batch/drift harus diuji. Tidak ada model CQR terpasang dalam patch F05.

Kesimpulan implementasi dari sumber tersebut adalah pilihan desain kami, bukan rekomendasi personal dari penulis paper. Metode pakar mengatur cara belajar/menguji; nilai normal tetap berasal dari data usaha yang valid.
