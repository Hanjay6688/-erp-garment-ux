# Takeover writer ERP oleh Claude — 22 Oktober2026 WIB

Instruksi owner terbaru (persis): "selesain sampe checkpoint berikutnya, siapin handoff takeover by claude ya, kinerja lu ampas, selalu stuck setelah kerja 20an menit, gpt emang gak di desain buat coding panjang ya?"

Owner meminta pergantian writer sesudah checkpoint ini. Jangan menambah writer/agent lain atau mengerjakan cabang lain; sesudah Claude mulai, sesi ini tidak menulis kode bersamaan.

## Kotak untuk disalin ke Claude

```text
Claude, takeover sebagai writer ERP Hansen. Baca docs/cp7/handoff/HANDOFF_CLAUDE_20261022.md dari cabang astra/d17-14-integrasi, AGENTS.md, CLAUDE.md, keputusan owner dan daftar OPEN_WORK yang ditautkan di sana. Baca juga ERP_WRITER_CONTEXT_20261021.txt dari paket privat yang saya lampirkan: itu menyimpan seluruh konteks/personal, keputusan, slogan, aturan dan riwayat takeover; bagian paling atas yang terbaru mengalahkan status lama di bawahnya.
Saat mulai, pastikan commit/tree dan isi pekerjaanmu cocok dengan checkpoint di handoff. Gunakan cabang astra/d17-14-integrasi yang sama, satu writer, tanpa menulis ke main, kandidat auditor55c885d1, Enteng, hosted, produksi atau WA nyata.
Status selesai5/16; OW05 selesai dalam cakupan owner dan bukti terikat di completion.json. OW06 baru checkpoint mesin pembayaran, belum selesai seluruh fitur. Teruskan sisa OW06 sesuai daftar tepat di handoff, lalu OW07/08 dan sisa OPEN_WORK. Jangan mengulang investigasi/hijau yang tidak perlu, mengarang keputusan owner atau melonggarkan pemeriksaan. Simpan kegagalan pertama.
Kabar maksimal dua kalimat bahasa sehari-hari; checkpoint bukan alasan berhenti selama scope masih dapat dikerjakan. Kalau layanan/sesi terputus, tulis keadaan nyata dan langkah lanjut, jangan mengaku chat masih bekerja di latar belakang.
```

## Keadaan yang diwariskan

- Repo `Hanjay6688/-erp-garment-ux`, hanya `astra/d17-14-integrasi`. Empat belas cabang lama dan lima commit yang sempat belum tergabung sudah direkonsiliasi; jangan dibuka ulang atau dihapus.
- **5/16 selesai:** OW01 pengingat WA ke provider palsu99; OW02 proses server32; OW03 kelipatan produksi154; OW04 retur tujuh syarat; OW05 koreksi mandor. Daftar satu baris per butir: `docs/cp7/d17-14/SELESAI_UNTUK_DIUJI.md`.
- Kandidat auditor55c885d1 tetap beku. Ini pekerjaan writer di cabang terpisah; kualifikasi writer bukan audit independen atau izin produksi. Audit tetap Fable/Sol sesuai arahan terdahulu.
- CP7C formal belum dimulai. Jangan menjanjikan besok/lusa tanpa bukti kesiapan. Urutan CP7→CP7.5 cleanup/rebaseline/restore→CP7C stress/automation/backup/install→CP8 audit/cutover/owner GO; tidak ada CP9.
- Log besar baru disimpan privat, repo hanya kuitansi ringkas dan potongan kegagalan pertama. Bukti lama56MB belum dihapus atau ditulis ulang. Jangan memasukkan data produksi atau tangkapan layar ke arsip.

## Aturan dan konteks owner

Baca `docs/cp7/OWNER_DECISIONS_20261008.md`, `docs/ERP_BEST_PRACTICES.md`, `docs/erp-reliability-invariants.md`, `docs/AUDIT_PANDUAN_PRO_MAX.md`, dan handoff lama `ARAHAN_ASTRA_20261022.md`. Seluruh konteks lama dipertahankan dalam berkas privat, tidak disalin ke repo publik.

- "VENI. VIDI. VICI. ERP. — I CONQUERED ERP."
- "Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja."
- Owner Hansen Hanjaya, panggil Bos, Indonesia/WIB. Owner bukan programmer; status singkat dan konkret, bukan istilah teknis yang panjang. Ia sudah terlalu sering harus mengetik lanjut dan mengalami streaming interrupted. Jangan mengarang penyebab putusnya sesi.
- Keuangan/stok/HPP/laporan harus atomik dan membaca fakta yang sama; posted immutable, koreksi melalui inverse/successor; uang sen tepat, PCS bulat, UNKNOWN bukan0/GRATIS.
- UUID yang sama mengulang hasil yang sama, UUID sama berisi lain ditolak; jawaban hilang berarti belum pasti sampai UUID yang sama diperiksa. Hak harus diperiksa sesudah menunggu dan saat replay.
- Waktu fisik/ekonomi/buku/pencatatan/pengetahuan dibedakan; semua jam bisnis WIB. Tidak mengarang batas koreksi tiga bulan atau membuka periode tertutup otomatis.
- Target pabrik sekitar1.200SKU×3≈3.600 barang, biaya tambahanRp0. Kebijakan OLD/NEW tarif D16-2/3/4 sudah disepakati; jangan ditanyakan ulang.
- WA seluruh pengingat sudah diputuskan dan diuji ke server palsu. CallMeBot untuk pemasangan CP7C sudah dipilih; jangan minta ulang pilihan atau mengirim WA nyata. Delapan konfigurasi owner diisi di aplikasi, bukan dianggap secret/tugas chat.
- Nilai yang belum diputuskan tetap terbuka: batas wajar/minimum riwayat hasil potong, service level target produksi bila berbeda dari rumus FG95%, syarat model perkiraan lebih baik bila benar-benar dibutuhkan. Cek register sebelum bertanya. BOM aksesori warna/ukuran A/B dan waktu laporan sudah ditanyakan sebelumnya.

## OW05 selesai: bukti yang harus dipertahankan

Satu catatan `docs/cp7/d17-14/ow05/completion.json`; rincian/original SHA pada kuitansi di folder yang sama. Produk uang terakhir e3a37d7308468d2c9983519ff55230aab9ffb2e5; Native28@56830738. UI terakhir5e4b4c1c.

| Bukti | Versi | Run/job | Hasil |
|---|---|---|---|
| Native28 |56830738640a356ceab9bc1a958881b28990bbf4 |39786776421/119851971167 |28PASS; termasuk14 alur OW05,3 HPP/seluruh PO/per SKU,11 oracle tarif lama |
| Auth4 |347a1baf56f07b110e44c003cce837794f89fee7 |39792851198/119872918589 |4PASS; dua pengguna, izin dicabut ketika menunggu, penulis jahit bersamaan dan NOWAIT |
| Layar terbaru |5e4b4c1c89a5b899d331a1c916d4c310c5ab5a6a |39797404450/119888156171 |2PASS; nyata1440/390px, waktu jahit WIB asli, upah lama0/baru24/WIP24 |
| Laundry/FG |5e4b4c1c89a5b899d331a1c916d4c310c5ab5a6a |39797404458/119888156506 |2PASS; public inverse laundry/QC/reopen→jahit→mandor→repost60, sejarah tetap |
| P21 lengkap |9dde276fdbf354368593607e52d7405775c4bf6f |39789070200/119859922468 |13 langkahPASS;10 lama tetap+3 mandor; dump/pulih, baris/urutan/22 katalog, replay dan generasi berikutnya |

Jangan menjumlahkan ulang uji yang sama sebagai kemajuan baru. Seluruh bukti memulihkan CP6/advisor dan nol sisa sesi. Fixture master/NativeSQL disebut apa adanya, bukan klaim pembuatan semuanya melalui layar.

Koreksi penting: **public** buka-ulang PO punya pengunci FG_USED. Balik pemakaian FG aktif dahulu, baru buka PO selesai, QC, laundry, jahit, lalu ganti mandor dan catat ulang pada jam/jumlah fisik asli. Fungsi raw Native yang lebih tua tidak membuktikan aturan jalur aplikasi sekarang. Fungsi inverse privat memang tidak boleh dieksekusi pengguna; jangan memberinya grant untuk membuat uji lulus.

Kegagalan awal Native28, browser, Auth dan laundry/FG tetap tersimpan dan tidak diubah menjadi PASS. Pernah ada kesalahan alat menuntut string16.00 alih-alih Decimal16.00; perbaikannya tidak mengubah nominal/toleransi. Pernah ada salah fixture payroll/attendance dan salah expected penolakan pertama; hasil pertama dipertahankan.

## Checkpoint OW06 yang diserahkan

Status/run/hash akhir ditulis di `docs/cp7/d17-14/ow06/CHECKPOINT.json` setelah uji selesai. **OW06_complete=false; hitungan tetap5/16.** Baca README folder itu untuk cakupan yang dibatasi.

Produk terpisah di `scripts/cp7_supplier_transfer/`; workflow `.github/workflows/cp7-ow06-native.yml`. Pemasang bawaan dan UI belum diubah, sehingga kode ini belum aktif pada aplikasi yang diwariskan. Tidak ada pemasangan hosted.

Desain: parent transfer+alokasi privat; Native supplier_payments tetap satu per penerimaan; kapabilitas backend/transaksi/aktor/request hanya mendelegasikan jurnal anak kepada satu jurnal aggregate Native. Pembatalan/koreksi wajib parent, bukan anak. Tidak menggunakan rekening perantara, jurnal kas per anak, offset tersembunyi atau FIFO. Penulis Native tetap memeriksa kapasitas utang, kredit bertanggal, rekening, tanggal dan status.

Sembilan fungsi lama diturunkan secara ketat di `native_delta.py`: post/reverse supplier payment, reverse_journal, payment_detail, reverse_payment_locked, supplier correction.apply, Native financial detector, receipt-correction blockers, transaction-source resolver. Metadata/ACL fungsi lama tetap; helper privat hanya diberi EXECUTE sempit ke pemilik pembaca lama, bukan pengguna. Komposisi membandingkan seluruh22 kelompok, tidak memproyeksikan definisi lama ke pemeriksa baru; tidak menambah trigger ERP.

Uji finite10: enam kontrol grup baru + empat oracle pembayaran tunggal lama yang berkas/expected-nya tidak diubah. Asli hasil CI dan kegagalan awal harus dipertahankan. Native runner membatalkan tiap kasus: pemeriksa deferred milik transfer dipaksa IMMEDIATE untuk membuktikan batas COMMIT, kemudian dikembalikan DEFERRED; ini belum bukti restore database yang sudah dipakai.

### Langkah Claude sesudah mengambil alih

1. Baca CHECKPOINT dan hasil per kasus, verifikasi commit/tree. Ulang hanya bila ada perubahan atau risiko yang belum dibuktikan; jangan menghabiskan waktu mengulang suite OW05 hijau tanpa perubahan yang menyentuhnya.
2. Telusur sembilan delta serta semua pembaca/pemanggil sampai GL, AP, reminder dan laporan; tambah kontrol lintas supplier, izin sesudah menunggu, dua transaksi, UUID sama/berbeda, tagihan/invoice bersama, kredit bertanggal dan tanggal buku tertutup. Nilai uang expected tetap; penolakan harus nol efek.
3. Buat kontrak klien tertutup dan layar pada Pembelian & Penerimaan. Pemilih penerimaan harus menyimpan alokasi lintas halaman; jumlah sen tepat sama dengan total; tanggal bayar dikonfirmasi pengguna. `payment_detail` kini menambah field `transfer` hanya untuk anak grup: parser lama menolak field baru, jadi perbarui secara eksplisit dan uji. Tampilkan nominal alokasi dan total transfer dengan jelas, buka parent, sembunyikan aksi pembatalan/edit anak. GL drill parent harus membuka seluruh alokasi melalui anak yang ditautkan server.
4. Gunakan useProductionMutation dan pemulihan hasil belum pasti. Domain baru/aksi baru harus didaftarkan dengan benar bila dipakai; invalidate semua fakta saat401/403/sumber berubah, current-ticket untuk jawaban terlambat. Jangan membuka tombol writer hanya karena sudah ada kode SQL.
5. Uji Auth/PostgREST nyata, persaingan nyata (observed lock wait, hak dicabut sesudah menunggu), browser desktop/390px, pencatatan→pembatalan→empat koreksi. Uji viewport dengan scrollWidth<=innerWidth, bukan overflow hidden.
6. Tambahkan owner pemasangan/used-state restore untuk OW06: semua baris, urutan,22 katalog, tamper refusal, replay sesudah pulih, inverse/successor berikutnya; integrasikan default P21 hanya sesudah jalur ini terbukti. Sumber badan yang diuji harus sama dengan badan paket yang dipasang. Jangan mengganti pemeriksa lama dengan yang tidak mengenal sumber baru.
7. Baru tutup OW06 jika seluruh syarat owner dan alur aplikasi terbukti; tulis satu baris SELESAI_UNTUK_DIUJI dan6/16. Lanjut OW07/08, bukan CP7C.

## Sisa pekerjaan setelah OW06

Daftar authoritative `docs/cp7/OPEN_WORK_D17_14_20261020.md`:

- OW07: tutup buku tertahan saat pool kantong/absen belum dibagi; sisa WIP PO selesai ditutup saat pool absen terlambat aktif.
- OW08: laporan sesudah kredit pelanggan masih BLOCKED (tiga detektor legacy menunjukkan2/3/1); kasbon bisa dibuka dari GL; piutang laundry/cuci gagal tanpa tarif/QC lainnya. Jangan menulis seolah laporan kredit sudah beres.
- OW09: urut/saring delapan layar atas seluruh hasil sebelum pagination, jumlah dan halaman konsisten.
- OW10–14: target cadangan dengan demand/leadtime tanpa hitung ganda; model lebih baik benar-benar dipakai dan fallback/produk serupa; skala3.600 barang dengan keuangan/HPP/pembanding; analisis pertama otomatis, yield>200grup, saran potong di form; ROP manual Enteng dibaca/migrasi saat pemasangan dan rumus kain di Ringkasan Gudang.
- OW16: status hasil potong otomatis sesudah selesai; total PCS dibanding sejarah seluruh pabrik per jenis bahan+pola+rentang ukuran, bukan akun; tanpa WA/pengingat/tombol manual. Lebar rentang/minimum riwayat tidak dikarang.
- OW15 terakhir: satu paket auditor jelas, daftar tertutup/terbuka;21 gagal CP6 dan4 gagal layar tetap gagal dengan baseline, pemetaan pengganti layar yang dipensiunkan. "Tidak ada kegagalan baru" bukan "kebutuhan selesai".

## Menjalankan dan memeriksa

Sebelum SQL Native: admission membutuhkan asli Native32 dan Native28 yang hash/bytes-nya dipin. Workflow mengambilnya dan menguji sumber sebelum menyentuh database. Contoh lokal source-only (tanpa DB):

```bash
ERP_REPO="$PWD" OW04_NATIVE32_ORIGINAL_REPORT=/abs/accepted-native32-original.json OW05_NATIVE28_ORIGINAL_REPORT=/abs/ow05-native28-56830738-pass.json PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python -c 'from cp7_supplier_transfer import native_probe as p; p.admitted()'
```

Bukti asli yang dibutuhkan disertakan di paket privat atau di arsip Library yang dicatat konteks. Jangan bergantung hanya pada artifact GitHub30 hari. Definisi fungsi installed terkini ada dalam ZIP P21 `PAYMENT_USED_RESTORE_MANIFEST.json`→`catalog.functions[signature][0]`; `CLONE_install.source-erp.sql` lebih tua, bukan dasar guard aplikasi terkini.

Status job GitHub kadang tersimpan lama sebagai queued meski run selesai dan artifact tersedia. Cocokkan metadata run, artifact dan hasil per kasus sebelum menyimpulkan macet; jangan rerun kandidat hijau hanya karena daftar job lama.

Git push CLI di sesi ini tidak punya auth; publisher GitHub API memverifikasi blob/tree dan mengubah ref dengan expected parent/forcefalse, kemudian fetch dan soft-reset hanya jika tree sama. Kalau Claude punya git push biasa, pakai alur biasa ke cabang yang sama. Jangan membuat cabang-cabang baru. Hindari `git add -A`; ada satu clone-temp tak terkait yang sengaja tidak diikutkan.

## Paket privat lengkap

`ERP_WRITER_CONTEXT_20261021.txt` memuat seluruh28 dokumen konteks awal,7 aliran takeover dan versi checkpoint berurutan, termasuk konteks personal/owner. Jangan mengunggahnya ke repo publik. Ringkasan handoff ini menuntun urutan baca; ia tidak menggantikan berkas konteks lengkap.

Setelah Claude mengakui takeover, hanya Claude yang menulis. Owner cukup memberikan paket dan kotak instruksi di atas; tidak perlu mengulang keputusan yang sudah tersimpan.
