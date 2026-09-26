# CP6: tabel 13 kebijakan (D11) dan dua opsi klaim laundry lama (GBD-03)

Disusun writer (Claude) atas arahan owner D11 (26 Sep 2026) dan handoff auditor R12-B. Nilai semua kebijakan tetap `PENDING_POLICY_VALUE` sampai owner memilih di aplikasi (Gudang · Aksesori → Kebijakan & area; Laundry → Harga & tagihan → Kebijakan owner). Kolom "Rekomendasi" adalah saran writer, bukan nilai yang dipasang. Writer tidak mengisi angka: nominal dan akun dipilih owner sendiri.

## 1. Tabel operasional 13 kebijakan

| Kode | Nama | Kegunaan | Pilihan yang diterima server | Rekomendasi writer + alasan | Transaksi yang tertahan selama kosong |
|---|---|---|---|---|---|
| ACC-DEC01 | Dua timeline nyata | Menyatakan bahwa tanggal fisik dan tanggal catat aksesori disimpan terpisah | `BOTH_REAL_TIMELINES` saja | Tetapkan. Hanya ada satu pilihan, dan sistem memang sudah bekerja begitu | Tidak ada; pengaturan ini tidak menahan transaksi |
| ACC-DEC03 | Nilai pemulihan barang bekas | Akun tujuan dan batas harga satuan saat barang titipan/bekas dinilai masuk stok | Akun kredit: akun pendapatan atau beban yang aktif dan dapat diposting. Batas: `MOVING_AVERAGE` atau `NONE` | Batas `MOVING_AVERAGE`, supaya nilai pemulihan tidak melebihi harga rata-rata dan nilai stok tidak membengkak. Akun kredit dipilih owner (mis. pendapatan lain-lain) | Menilai titipan/bekas yang masih pending (`VALUE_CUSTODY`) ditolak `BC_POLICY_PENDING` |
| ACC-DEC04 | Akun biaya servis pelanggan dan perbaikan FG sendiri | Akun beban untuk aksesori yang dipakai servis pelanggan atau perbaikan barang jadi sendiri | Minimal satu akun beban aktif: servis pelanggan dan/atau perbaikan FG sendiri | Isi keduanya dengan akun beban yang berbeda, agar laporan memisahkan biaya servis dan biaya perbaikan | Pemakaian aksesori bertujuan servis pelanggan atau perbaikan FG sendiri ditolak; pemakaian pabrik tetap jalan |
| ACC-DEC05 | Kredit retur nota mandor | Cara aksesori yang dikembalikan mandor mengurangi nota | Mode: `CREDIT_UNPAID_ONLY`, `CREDIT_THEN_CARRY`, atau `CREDIT_THEN_REFUND`. Kondisi yang dikreditkan: `USABLE` dan/atau `DAMAGED` | `CREDIT_UNPAID_ONLY` dengan kondisi `USABLE` saja. Kredit hanya mengurangi sisa nota yang belum dibayar, dan barang rusak tidak dikreditkan. Paling konservatif sampai ada kesepakatan tertulis dengan mandor | Kredit retur nota (`CREDIT_NOTE_RETURN`) ditolak |
| ACC-DEC06 | Pembulatan rupiah nota mandor | Pembulatan total nota ke rupiah terdekat beserta akun selisihnya | Mode `NOTE_NEAREST_RUPIAH`; akun untung (pendapatan/beban) dan akun rugi (beban) | Tetapkan dengan akun selisih pembulatan tersendiri, agar selisih kecil tidak tercampur ke akun lain | Baris pembulatan nota tidak dapat diposting |
| ACC-DEC07 | Ambang persetujuan owner dan pengguna per zona | Nominal biaya aksesori (pemakaian internal, pemusnahan, selisih hitung) yang perlu persetujuan owner/admin, serta siapa boleh mencatat per zona | Nominal (teks angka); daftar pengguna per zona opsional | Nominal ditentukan owner dari kebiasaannya sendiri; writer tidak mengusulkan angka. Daftar pengguna zona diisi bila area pemeriksaan/rusak dijaga orang tertentu | Tidak tertahan, tetapi setiap biaya bernilai perlu owner/admin (bukan hanya yang di atas ambang) |
| ERP-DEC02 | Kategori gratis Special | Kategori aksesori yang boleh diberikan gratis di nota (baris FREE) | Daftar kategori aksesori aktif (boleh kosong) | Isi hanya kategori yang memang biasa diberikan gratis ke mandor; daftar ditentukan owner | Baris gratis ditolak, begitu juga harga manual 0 (`BC_FREE_REQUIRES_POLICY`) |
| LAU-DEC01 | Satuan tarif tambahan laundry | Mengizinkan tarif borongan per batch dan/atau minimum charge (tarif per PCS selalu berlaku) | `BATCH` dan/atau `MINIMUM` | Aktifkan hanya yang benar-benar dipakai vendor sekarang, supaya tarif lain tidak bisa dipasang tanpa dasar | Tarif borongan per batch dan minimum charge tidak dapat disimpan atau dipakai; per PCS tetap jalan |
| LAU-DEC02 | Kategori yang boleh ditagih vendor laundry | Dasar qty invoice vendor laundry | `GOOD`, `BS`, dan/atau `FAILED_ATTEMPT` | `GOOD` dan `BS` (vendor tetap mengerjakan potongan yang jadi BS). Tambahkan `FAILED_ATTEMPT` hanya bila perjanjian vendor memang menagih cuci gagal | Semua draf dan posting invoice vendor laundry ditolak (butuh LAU-DEC02 dan LAU-DEC06) |
| LAU-DEC03 | Diskon, komponen ekstra, pembulatan, pajak invoice laundry | Aturan baris invoice di luar harga master | Diskon: `ALLOWED`/`REFUSED`; ekstra: `ALLOWED`/`REFUSED`; pembulatan: `LAST_LINE`/`REFUSED`; akun pajak (aset) opsional | Diskon `ALLOWED`, ekstra `REFUSED` (komponen tambahan lewat harga master), pembulatan `LAST_LINE`. Akun pajak hanya bila perusahaan memang mengkreditkan pajak masukan | Invoice berdiskon/pajak/pembulatan dan komponen ekstra di luar paket ditolak |
| LAU-DEC04 | Jual barang yang harga laundry-nya belum diketahui | Boleh tidaknya barang jadi dijual sebelum harga laundry-nya pasti | `REFUSE` atau `ALLOW_PENDING` | `REFUSE`, supaya HPP pasti sebelum penjualan. Akibatnya: harga laundry harus diisi dulu sebelum barang dijual | Selama kosong berlaku sama dengan `REFUSE`: penjualan barang itu ditolak (`BD_SALE_LAUNDRY_PRICE_UNKNOWN`) |
| LAU-DEC05 | Tarif khusus model/ukuran/warna | Tarif vendor yang berbeda per model, ukuran, atau warna | Scope: `MODEL`, `MODEL_SIZE`, `MODEL_SIZE_COLOR`; fallback `BASE_RATE` atau `REFUSE` | Aktifkan hanya scope yang dipakai vendor. Fallback `REFUSE`, supaya ukuran tanpa tarif khusus tidak diam-diam memakai tarif dasar | Tarif khusus tidak dapat disimpan; kiriman tetap memakai tarif proses dasar |
| LAU-DEC06 | Perlakuan selisih invoice laundry | Ke mana selisih invoice terhadap estimasi dibukukan, dan boleh tidaknya koreksi sesudah dibayar | Mode: `PRODUCT_COST` atau `VARIANCE_ACCOUNT` (dengan akun beban); sesudah bayar: `REFUSE` atau `CORRECTION_DOCUMENT` | `PRODUCT_COST`, supaya HPP memuat biaya laundry sebenarnya; pembagiannya mengikuti D10 (per potong dalam sumber tagihan yang sama). Sesudah bayar: `REFUSE` (pembayaran dibalik dulu) | Semua invoice vendor laundry ditolak (bersama LAU-DEC02) |

Konfigurasi uji: setiap run CI menetapkan nilai kebijakan hanya di dalam fixture (savepoint atau salinan disposable) sesuai kasusnya, dan kasus mencatat nilai serta versinya. Nilai ini tidak menjadi rekomendasi dan tidak dipasang di data mana pun di luar run.

## 2. GBD-03: dua opsi representasi klaim laundry lama (ALL-W05)

Contoh dari oracle auditor GBD-03: sebelum cutover vendor memegang 10 PCS; 2 sudah kembali, 1 hilang (MISSING) belum diselesaikan, 7 masih diproses normal; utang ke vendor 30,00; kemudian vendor memberi kredit klaim 5,00. `c` adalah nilai per PCS di saldo awal WIP (ditentukan data cutover, bukan angka writer).

**Opsi 1: potongan yang diklaim tetap di WIP sebagai tahanan (perilaku kode sekarang).**
- Saat cutover: WIP laundry 8 PCS senilai 8c, dengan 1 PCS ditahan klaim. Sisa WIP yang bisa diselesaikan 7.
- Kembalinya 7 PCS menyelesaikan WIP normal sekali. Klaim yang pulih (`RECOVER_CLAIM`) mengembalikan potongannya ke sisa WIP.
- Klaim diselesaikan (`RESOLVE_CLAIM`, SETTLED): kredit 5,00 dicatat sekali, AP_VENDOR debit / OTHER_EXPENSE kredit, dibatasi utang vendor. Utang tersisa 25,00.
- Nilai c potongan yang hilang tetap di WIP sampai PO selesai, lalu dibebankan lewat penutupan residu PO, seperti potongan hilang biasa.
- Kelebihan: tidak ada akun baru; potongan tetap terlacak per PO. Kekurangan: kerugian baru terlihat saat PO selesai.

**Opsi 2: potongan hilang keluar dari WIP ke piutang klaim laundry saat cutover.**
- Saat cutover: WIP laundry 7 PCS senilai 7c, ditambah piutang klaim laundry c untuk 1 PCS.
- Klaim pulih: c kembali dari piutang klaim ke WIP, dan potongannya diproses normal.
- Klaim diselesaikan dengan kredit 5,00: AP_VENDOR debit 5,00, piutang klaim kredit 5,00. Selisih c − 5,00 langsung dibebankan ke akun kerugian klaim. Bila klaim dihapus tanpa kredit, seluruh c dibebankan.
- Kelebihan: nilai klaim terlihat sebagai aset terpisah dan kerugian diakui saat klaim selesai. Kekurangan: butuh akun piutang klaim dan akun kerugian klaim (pilihan owner), dan kode perlu diubah.

Sampai owner memilih, ALL-W05 tidak diklaim ACCEPT penuh; yang dibuktikan hanya invariant strukturalnya (tabel kasus BD §GBD).

## 3. Keputusan owner GBD-03 (26 Sep 2026, chat)

Kata owner: "opsi satu tapi bisa pindah akun gak? misal mengurangi hutang di bulan X, karena kan biasa claim belakangan??"

Dicatat: **opsi 1**. Jawaban writer atas pertanyaannya, dari kode yang berlaku (`scripts/cp6_bd_objects_import.sql`, aksi `RESOLVE_CLAIM`):
- **Bisa, utang berkurang di bulan klaim diselesaikan.** Penyelesaian klaim membawa tanggalnya sendiri (tidak boleh sebelum saldo awal, sebelum tanggal klaim, atau di masa depan). Jurnal kompensasi (AP_VENDOR debit, OTHER_EXPENSE kredit) diposting pada tanggal itu. Jadi klaim yang disepakati vendor di bulan X mengurangi utang vendor di bulan X, bukan di bulan cutover. Tanggalnya harus masih di periode yang belum ditutup.
- Selama klaim belum selesai, tidak ada jurnal. Potongan tetap tertahan di WIP, dan potongan yang kembali dicatat `RECOVER_CLAIM`.
- Kompensasi dibatasi utang ke vendor itu pada saat dicatat. Bila utangnya sudah lunas, kompensasi ditolak (`BD_W05_COMPENSATION_EXCEEDS_PAYABLE`); penagihan tunai ke vendor belum punya alur.
- **Akun lawan kompensasi sekarang tetap OTHER_EXPENSE** (aturan klaim laundry baseline). Bila owner ingin akun lain (misalnya pendapatan klaim), itu perubahan kecil tetapi mengubah aturan baseline, jadi perlu disebut akunnya dan diputuskan tertulis.
