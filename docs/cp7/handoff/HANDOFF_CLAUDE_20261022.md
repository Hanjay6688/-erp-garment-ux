# Takeover writer ERP oleh Claude — 22 Oktober2026 WIB

> **Pembaruan 22 Okt 2026 (D17-17):** pembagian yang berlaku adalah `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md` versi 2. Claude bekerja di `claude/d17-14-uang` (OW-06, OW-07, OW-08, OW-09, OW-12a, OW-15, penggabung); Astra di `astra/d17-14-produksi`. Bagian yang menyebut Codex OW07 dan `claude/ow06-supplier-transfer` di bawah sudah digantikan.

Instruksi awal: "selesain sampe checkpoint berikutnya, siapin handoff takeover by claude ya". Checkpoint itu sudah diserahkan. **Terbaru: D17-16 dan pembagian Claude versi2**, semua fitur tetap lingkup. Baca [PEMBAGIAN_DUA_PENULIS_20261022.md](../PEMBAGIAN_DUA_PENULIS_20261022.md) dan [KOORDINASI.md](../d17-14/KOORDINASI.md). Pembagian OW06-Claude/OW07-Codex dan aturan satu writer sebelumnya sudah digantikan. Pesan lama dan konteks personal tetap disimpan dalam paket privat.

Claude/A menangani uang, stok, HPP, laporan, OW06/07/08/09, modul angka analisis OW12a dan paket auditor sekaligus integrator tunggal. Codex/Astra/B menangani produksi/perencanaan OW16, OW10/11, OW12b, OW13/14 pada cabang produksi. Jangan mengerjakan scope penulis lain. Penugasan ini tidak berarti Claude sudah mulai bekerja atau memberikan production_go.

## Kotak untuk disalin ke Claude

```text
Claude, takeover sebagai writer ERP Hansen. Baca docs/cp7/handoff/HANDOFF_CLAUDE_20261022.md dari cabang astra/d17-14-integrasi, AGENTS.md, CLAUDE.md, keputusan owner dan daftar OPEN_WORK yang ditautkan di sana. Baca juga ERP_WRITER_CONTEXT_20261021.txt dari paket privat yang saya lampirkan: itu menyimpan seluruh konteks/personal, keputusan, slogan, aturan dan riwayat takeover; bagian paling atas yang terbaru mengalahkan status lama di bawahnya.
Saat mulai, baca PEMBAGIAN_DUA_PENULIS_20261022.md versi2 dan d17-14/KOORDINASI.md, pastikan commit/tree cocok. Cabang A claude/d17-14-uang, cabang B astra/d17-14-produksi; hanya Claude sebagai integrator yang memajukan astra/d17-14-integrasi. OW07 sekarang milik Claude, bukan Codex. Dasar produk01c5f856, kepala integrasi a255e48 menambahkan dokumen saja. Gunakan checkout terpisah; jangan menulis ke main, kandidat auditor55c885d1, Enteng, hosted, produksi atau WA nyata.
Status selesai5/16; OW05 selesai dalam cakupan owner dan bukti terikat di completion.json. OW06 baru checkpoint mesin pembayaran, belum selesai seluruh fitur. Tuntaskan scope A sesuai pembagian versi2; semua fitur D17-16 tetap lingkup. Jangan mengambil scope B. Jangan mengulang investigasi/hijau yang tidak perlu, mengarang keputusan owner atau melonggarkan pemeriksaan. Simpan kegagalan pertama.
Kabar maksimal dua kalimat bahasa sehari-hari; checkpoint bukan alasan berhenti selama scope masih dapat dikerjakan. Kalau layanan/sesi terputus, tulis keadaan nyata dan langkah lanjut, jangan mengaku chat masih bekerja di latar belakang.
```

## Keadaan yang diwariskan

- Repo `Hanjay6688/-erp-garment-ux`; titik integrasi tetap `astra/d17-14-integrasi`. Cabang A/B dibatasi pembagian Claude versi2. Dua cabang persiapan OW06/OW07 sebelumnya tidak diteruskan. Empat belas cabang lama dan lima commit yang sempat belum tergabung sudah direkonsiliasi; jangan dibuka ulang atau dihapus.
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

Dasar bisnis tetap D17-14 butir5 pada register keputusan owner: satu transfer ke beberapa penerimaan/tagihan, jumlah alokasi sama dengan pembayaran, kas keluar sekali, pembatalan/koreksi konsisten.

**Checkpoint lulus10/10** pada f764c5080991690bac443ecfe0f9171c77a0307e, tree34c35fe3cce0b02e31abba94bd6a303f7ac76e7a, run39808778963/job119929044980. Status per kasus, hash asli dan batas ada di `docs/cp7/d17-14/ow06/CHECKPOINT.json`. **OW06_complete=false; hitungan tetap5/16.** Baca README folder itu untuk cakupan yang dibatasi.

Produk terpisah di `scripts/cp7_supplier_transfer/`; workflow `.github/workflows/cp7-ow06-native.yml`. Pemasang bawaan dan UI belum diubah, sehingga kode ini belum aktif pada aplikasi yang diwariskan. Tidak ada pemasangan hosted.

Desain: parent transfer+alokasi privat; Native supplier_payments tetap satu per penerimaan; kapabilitas backend/transaksi/aktor/request hanya mendelegasikan jurnal anak kepada satu jurnal aggregate Native. Pembatalan/koreksi wajib parent, bukan anak. Tidak menggunakan rekening perantara, jurnal kas per anak, offset tersembunyi atau FIFO. Penulis Native tetap memeriksa kapasitas utang, kredit bertanggal, rekening, tanggal dan status.

Sembilan fungsi lama diturunkan secara ketat di `native_delta.py`: post/reverse supplier payment, reverse_journal, payment_detail, reverse_payment_locked, supplier correction.apply, Native financial detector, receipt-correction blockers, transaction-source resolver. Metadata/ACL fungsi lama tetap; helper privat hanya diberi EXECUTE sempit ke pemilik pembaca lama, bukan pengguna. Komposisi membandingkan seluruh22 kelompok, tidak memproyeksikan definisi lama ke pemeriksa baru; tidak menambah trigger ERP.

Uji finite10 seluruhnya PASS: enam kontrol grup baru + empat oracle pembayaran tunggal lama yang berkas/expected-nya tidak diubah. Pembayaran400+600 tepat satu kas1000, pembalikan kas net0, empat koreksi dengan nominal akhir900, bank kosong menolak tanpa sisa; detektor korupsi satu sen0→1→0 dan penolakan pencopotan sesudah dipakai lulus. Seluruh22 katalog/pencopotan/CP6/advisor kembali tepat. Asli hasil CI dan kegagalan awal harus dipertahankan. Native runner membatalkan tiap kasus: pemeriksa deferred milik transfer dipaksa IMMEDIATE untuk membuktikan batas COMMIT, kemudian dikembalikan DEFERRED; ini belum bukti restore database yang sudah dipakai.

### Langkah Claude sesudah mengambil alih

1. Baca CHECKPOINT dan hasil per kasus, verifikasi commit/tree. Ulang hanya bila ada perubahan atau risiko yang belum dibuktikan; jangan menghabiskan waktu mengulang suite OW05 hijau tanpa perubahan yang menyentuhnya.
2. Telusur sembilan delta serta semua pembaca/pemanggil sampai GL, AP, reminder dan laporan; tambah kontrol lintas supplier, izin sesudah menunggu, dua transaksi, UUID sama/berbeda, tagihan/invoice bersama, kredit bertanggal dan tanggal buku tertutup. Nilai uang expected tetap; penolakan harus nol efek.
3. Buat kontrak klien tertutup dan layar pada Pembelian & Penerimaan. Pemilih penerimaan harus menyimpan alokasi lintas halaman; jumlah sen tepat sama dengan total; tanggal bayar dikonfirmasi pengguna. `payment_detail` kini menambah field `transfer` hanya untuk anak grup: parser lama menolak field baru, jadi perbarui secara eksplisit dan uji. Tampilkan nominal alokasi dan total transfer dengan jelas, buka parent, sembunyikan aksi pembatalan/edit anak. GL drill parent harus membuka seluruh alokasi melalui anak yang ditautkan server.
4. Gunakan useProductionMutation dan pemulihan hasil belum pasti. Domain baru/aksi baru harus didaftarkan dengan benar bila dipakai; invalidate semua fakta saat401/403/sumber berubah, current-ticket untuk jawaban terlambat. Jangan membuka tombol writer hanya karena sudah ada kode SQL.
5. Uji Auth/PostgREST nyata, persaingan nyata (observed lock wait, hak dicabut sesudah menunggu), browser desktop/390px, pencatatan→pembatalan→empat koreksi. Uji viewport dengan scrollWidth<=innerWidth, bukan overflow hidden.
6. Tambahkan owner pemasangan/used-state restore untuk OW06: semua baris, urutan,22 katalog, tamper refusal, replay sesudah pulih, inverse/successor berikutnya; integrasikan default P21 hanya sesudah jalur ini terbukti. Sumber badan yang diuji harus sama dengan badan paket yang dipasang. Jangan mengganti pemeriksa lama dengan yang tidak mengenal sumber baru.
7. Baru tutup OW06 jika seluruh syarat owner dan alur aplikasi terbukti; tulis satu baris SELESAI_UNTUK_DIUJI dan hitungan berdasarkan daftar aktual. OW07/OW08/seterusnya dibagi menurut pembagian Claude versi2; OW07 tetap di jalur A bersama uang/HPP. Ini belum CP7C.

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

Git push CLI di sesi ini tidak punya auth; publisher GitHub API memverifikasi blob/tree dan mengubah ref dengan expected parent/forcefalse, kemudian fetch dan soft-reset hanya jika tree sama. Kalau Claude punya git push biasa, pakai alur biasa ke cabang A claude/d17-14-uang. Hanya integrator memajukan cabang integrasi; jangan force-push atau membuat cabang di luar pembagian versi2. Hindari `git add -A`; ada satu clone-temp tak terkait yang sengaja tidak diikutkan.

## Paket privat lengkap

`ERP_WRITER_CONTEXT_20261021.txt` memuat seluruh28 dokumen konteks awal,7 aliran takeover dan versi checkpoint berurutan, termasuk konteks personal/owner. Jangan mengunggahnya ke repo publik. Ringkasan handoff ini menuntun urutan baca; ia tidak menggantikan berkas konteks lengkap.

Setelah Claude mulai, Claude hanya menulis scope A dan integrasi; Codex/Astra hanya scope B produksi/perencanaan. Baca pembagian Claude versi2 dan KOORDINASI dari GitHub, termasuk jika ZIP privat masih berisi handoff awal yang memakai satu writer atau pembagian OW07-Codex. Owner tidak perlu menyalin ulang keputusan yang sudah tersimpan.

## Catatan run lama dan kegagalan pemasangan

Dua hasil asli0 kasus dipertahankan: 39803289633 (postgres tidak punya CREATE pada schema pemilik pembaca) dan39807454686 (helper role OW04 sengaja hanya mengizinkan role milik OW04). Perbaikan final memakai helper OW06 sendiri dengan daftar fungsi/pemilik schema lama yang tepat, SET LOCAL ROLE terbatas dan ACL asli kembali persis di transaksi yang sama; helper OW04 tidak dilonggarkan. Tidak ada perubahan nominal/expected untuk membuat lulus.

Run39804712826/job119914712281 pada versi lama bef6b782 masih dilaporkan IN_PROGRESS pada pemasangan alat sebelum kasus saat penyerahan; log belum tersedia. Versi itu belum punya helper owner final dan tidak dipakai menutup checkpoint. Ini job server yang sudah dikirim, bukan chat yang terus bekerja. Claude cukup mencatat hasil akhirnya ketika tersedia; jangan mererun. Workflow terkini sudah membatasi pemasangan dependensi8menit dan hanya menerima psql/pg_dump/pg_restore versi17 yang diperiksa; kunci tanda tangan lama tetap persis.

Batas lama yang jangan disembunyikan: kasus CURRENT_ACCESS yang dipertahankan mencatat SQL langsung authenticated bisa membuat DRAFT dan memanggil penulis supplier Native tanpa finance.ap.pay; seluruh observasi dibatalkan. Ini belum dibetulkan oleh OW06. Aplikasi/PostgREST hanya mengekspos public, bukan schema erp; jangan menyamakan batas jalur aplikasi itu dengan bukti bahwa seluruh akses SQL langsung sudah tertutup. Detail asli tetap di CHECKPOINT dan audit keterpaparan masih terbuka.
