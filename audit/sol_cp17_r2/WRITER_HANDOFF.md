# Handoff Sol — audit r2 CP1–7

**Kandidat `2e9d6a468c110684c278d585418eb404250d1150`, tree `5e50d224f8e74fa3bca83b599fb606739435b598`. Vonis: HOLD.**

Audit putaran ini selesai; tidak ada job uji yang masih berjalan. Semua perubahan auditor berada di cabang
`audit/sol-cp1-7-r2-2e9d6a46-20261016`. Auditor tidak memperbaiki kode produk, menyentuh cabang writer/main,
memasang aplikasi, atau mengakses database hosted. Penerimaan CP6 lama tetap mengikuti kontrak dan keputusan owner;
penilaian ini berlaku untuk kandidat integrasi r2 dan gerbang penutup CP1–7.

## Pekerjaan perbaikan

| Urut | Item | Keadaan | Langkah writer |
|---|---|---|---|
| 1 | **SOL-R2-001, S2: nomor PO ke-1.000 macet** | Baru, terverifikasi Native | Ubah pengisi nol menjadi lebar minimum; jaga kunci per tanggal, keunikan, UUID dan atomicity. |
| 2 | **KNOWN-R2-POOL-UI, S1: siklus pool HPP absensi belum punya layar** | Sudah diungkap writer, dikonfirmasi dari sumber; bukan temuan baru Sol | Lengkapi preview/buat/aktifkan/batalkan dengan writer Native, riwayat, review/version, izin dan penghalang periode. D15-2 tidak menghapus kebutuhan ini. |
| 3 | **KNOWN-RECEIPT-FIRST100, S3** | Sudah diungkap writer; skrip kandidat masih hanya halaman pertama | Paginasi daftar run, job dan anotasi; tambah uji lebih dari 100 baris. Receipt r2 yang dipaginasi terpisah tetap bisa dibaca. |

### 1. Nomor PO ke-1.000

- Lokasi: `scripts/cp7-src/cutting-correction/auto-po.sql`, baris 212–217.
- `lpad(v_n::text,3,'0')` memotong `1000` menjadi `100`. Dengan nomor harian `001` sampai `999` sudah ada,
  perulangan kembali memeriksa nomor yang sudah terpakai dan tidak menghasilkan nomor berikutnya.
- **Kontrol:** 998 header PO sintetis tanpa stok/jurnal → PO `PO-261014-999` berhasil, **0,040 detik**.
- **Kasus gagal:** 999 header PO → seharusnya `PO-261014-1000`; command dihentikan batas uji **3,003 detik**,
  SQLSTATE `57014`. Konteks PostgreSQL menunjuk tepat ke `WHILE ... lpad(...)`.
- **Dampak yang terbukti:** pembuatan potongan/PO baru tidak selesai pada batas tersebut. **Seluruh batas data tetap utuh**;
  stok roll tetap 10, tidak ada PO atau jurnal setengah jadi. Kunci penomoran per tanggal tertahan selama command
  berlangsung; dampak ke permintaan lain pada tanggal sama ditelusuri dari sumber, belum diuji dengan dua sesi di batas 1.000.
- Bukti: run **38934111700**, job **117085146759**, artifact **12059209949**, `SOL_R2_NEW_RESULT.json`.
  Kasus `SOL_R2_AUTO_PO_NUMBER_999_CONTROL` PASS dan `SOL_R2_AUTO_PO_NUMBER_1000_BOUNDED` COUNTEREXAMPLE
  (**FAIL** dalam kosakata audit).
- Usulan: tiga digit menjadi **lebar minimum**, misalnya panjang yang dipakai `lpad` minimal panjang angka itu sendiri.
  Menaikkan timeout tidak menyelesaikan penyebabnya. Jika memang dibatasi kapasitas, batas harus menolak cepat dengan
  pesan jelas dan memerlukan keputusan bisnis; auditor menyarankan penomoran bisa melewati 999.

Uji penerimaan yang perlu ditambahkan:

1. 998 → 999 → 1000 → 1001, dan 9999 → 10000: nomor benar, unik, tidak terpotong.
2. Dua sesi di batas 999/1000 serta replay UUID sama: satu efek per permintaan sah, tanpa nomor/PO/stok ganda.
3. Kegagalan sesudah header PO dibuat: header, stock movement, jurnal dan riwayat semuanya batal.
4. Draf tetap tidak membuat PO; tanggal potong WIB tetap menentukan nomor dan kunci harian.

Probe auditor sudah tersedia di `new_cases.py`; pertahankan angka, contoh gagal, dan kontrolnya saat writer memperbaiki.

### 2. Pool HPP absensi

`src` dan `scripts/cp7-src` belum mempunyai pemanggil Native create/activate/cancel pool. Layar dan pesan pengaman
meminta pool aktif dibatalkan dahulu sebelum sumber tertentu bisa diperbaiki. Alur pembatalan itu belum bisa
diselesaikan pengguna dari aplikasi. CP17 HPP01 membuktikan **cancel → ubah kebijakan → pool pengganti** di SQL,
bukan ketersediaan langkah itu di layar.

Writer sudah mengungkap batas ini di `CROSS_AUDIT.md` r2. Owner D15-2 menyetujui penyembunyian layar yang belum
terhubung di UAT; keputusan tersebut tidak menerima penghilangan siklus pool. Jangan menutup item ini hanya karena
menu absensi tersembunyi. Uji satu perjalanan layar sampai pembatalan, koreksi sumber dan pool pengganti, termasuk
periode tertutup, perubahan izin, UUID ulang dan dua tab.

## Uji ulang Sol yang sudah selesai

| Item lama | Putusan dalam cakupan uji |
|---|---|
| SOL-R1-001, koreksi pemasukan terpakai | **Tutup.** Literal Native 7/7 dan real Auth HTTP 4/4 PASS. Pemasukan 30,01, dipakai 20, dibetulkan 25,01 → saldo 5,01; catatan saja → 10,01. Saldo akhir negatif tetap ditolak. |
| SOL-R1-002, jalur PO harian | **Tutup untuk jalur biasa.** PO otomatis dan potongan atomik terbukti di Native/race/HTTP/browser, termasuk build UAT lewat transport disposable. Batas nomor baru dicatat terpisah di SOL-R2-001. |
| SOL-R1-003, berhenti sebelum U | **Tutup.** Helper kandidat dijalankan tanpa monkeypatch Sol; stop-before-U diterima, owner 10/10 dan pemasangan 58/58 berkas lulus. |
| SOL-R1-004, QC melebar | **Tutup.** Dokumen demo 390 px pada viewport 390 px, sebelumnya 669 px. |
| SOL-R1-005, HPP melebar | **Tutup.** Dokumen demo 390 px pada viewport 390 px, sebelumnya 627 px. |
| KNOWN-UI-MODE | **Tutup sesuai D15-2.** 17 menu UAT tersembunyi, dashboard tanpa saldo contoh; enam layar contoh disposable berlabel. |
| KNOWN-DAILY-MASTER | **Tutup dalam cakupan enam layar dan tarif.** Native, dua tab, HTTP dan browser; tambahan customer lifecycle pada build UAT sesungguhnya. |
| KNOWN-BF-WAVE | **Tutup dalam cakupan yang diuji.** Jahit per SKU, tarif snapshot, pembatalan satu SKU, dan sisa ukuran terbukti. Contoh tambahan Sol: ukuran 5/2/9, akhir 16 pcs dan WIP bersih 356. |

## Hasil lain yang penting

- F03: **447 eksekusi kasus + 3 smoke**, semuanya PASS; ini gabungan Native/race/HTTP/browser, bukan 447 Native saja.
- Regresi layar BD/BE/BF/readiness pada stack CP7 terakhir: **31/31 PASS**.
- CP17: **145/145 PASS** (80 Native, 18 race, 14 real Auth HTTP, 33 browser).
- F04 model/consumer: **57/57 PASS**, termasuk POST potong dengan PO lama, pemulihan balasan hilang dan pencabutan izin.
- Tiga kasus build **UAT_AUTH_SIMULATION** dengan Auth dan Native disposable: **3/3 PASS**. Semua permintaan ke
  alamat hosted dialihkan ke disposable sebelum dikirim; hasil ini tidak membuktikan pemasangan hosted.
- Inventaris 48 menu × 3 mode × desktop/HP: **288 pengamatan PASS** dengan Auth tiruan dan business reads 403.
  Ini bukti rute, label, lebar dan tampilan penolakan; bukan 288 transaksi Native berhasil.
- Unit/DOM **1.794/1.794 PASS**, gerbang sumber/keamanan PASS; CodeQL JavaScript/TypeScript dan Actions masing-masing
  selesai dengan **0 findings**.

## Yang tetap membatasi penutupan

Status **HOLD** tidak berarti semua bagian rusak. Bug nomor PO terbukti rusak; pool HPP belum mempunyai fungsi layar;
sedangkan batas lain merupakan bukti penerimaan yang belum lengkap. `OPEN_BOUNDARIES.json`, matriks 82 invarian dan
20 sambungan memisahkan ketiganya. Antara lain: data cutover nyata/shadow, original CP2 functional restore, preflight
hosted terbaru, perangkat fisik/iPad, semua kontrol negatif detektor dan cek integritas sebelum/sesudah setiap skenario.
Penundaan CP7C serta EXECUTE 82 writer mengikuti keputusan owner yang sudah ada, tidak ditanyakan ulang.

Semua 10 run/21 job auditor sudah terminal. Dua run merah tetap tersimpan: satu menemukan SOL-R2-001, satu berisi
kesalahan alat observasi dan checkout auditor. Koreksi alat dikualifikasi di run terpisah tanpa mengubah produk atau
oracle; hasil gagal pertama tidak dihapus. Dua INCOMPLETE tambahan pada baseline CP6 sebelum CP7 terpasang adalah
diagnosis yang sengaja disimpan, dengan nol kredit kelulusan produk.

Sesudah writer memperbaiki item terbuka, bekukan kandidat baru dan serahkan diff serta bukti gagal-sebelum/lulus-sesudah
kepada auditor. Tidak ada perintah deploy atau pembukaan produksi dari handoff ini.

Rincian: `RETEST_SOL_2e9d6a46.md`, `FINDINGS.json`, `RETEST_DISPOSITIONS.json`, `IMPACT_MATRIX.json`,
`CASE_LEDGER.json`, `RUN_REGISTER.json` dan penunjuk arsip bukti.
