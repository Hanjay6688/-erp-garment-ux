# OW-04 — bantahan tanggal pada rancangan kredit retur lunas

**INTERNAL_WRITER_SOURCE_REVIEW, bukan runtime atau audit independen.**
Pin sumber produk `4e3c98b3ce04427c65c7bc7c1b21ec3bdacfea71`.
Belum ada implementasi kredit/refund; produk sekarang masih menolak retur
yang membuat pembayaran melebihi nilai penjualan bersih. Karena itu contoh
di bawah membantah rancangan baru, bukan melaporkan kredit rusak yang sudah
terjadi di produk. P/U/I tetap hitungan keadaan terkini yang berguna.

## Sumber tanggal yang benar-benar ada

- `scripts/cp7-src/sales/commands.sql`, cabang RETURN, meneruskan
  `physical_at` dari operator; waktu baru tidak boleh berasal dari jam buka
  halaman (`erp-reliability-invariants.md`, Physical time).
- Native `post_sales_return` di
  `supabase/release/cp6-t3/20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.sql:414–417`
  memanggil `post_journal` dengan tanggal ekonomi WIB `h.physical_at`.
- Native `post_sales_payment` di `20260922135615_…20ap…sql:5038–5042`
  memakai tanggal pembayaran WIB, kecuali jalur pengganti realokasi yang
  memang mempertahankan tanggal sumber. Pembayaran asli tidak ditulis ulang.
- Native `post_journal` di `20260915031500_…20ac…sql:4056–4078`
  menyimpan ekonomi=input, buku=`resolve_accounting_transaction_date(input)`;
  saldo harian memakai tanggal buku itu. Resolver tidak menerima tanggal
  buku terpisah. Delta calendar20t:338–340 dan business_clock20ab:260
  mengikat hari kini ke `statement_timestamp()` dalam WIB.
- Laporan owner20ac:2737–2744 membaca AR dari `account_daily_balances`,
  menurut tanggal buku. Mengabaikan tanggal buku bukan pilihan yang aman.
- `sales/return-correction.sql:158–185` dan `sales/correction.sql:109–136`
  memakai jurnal neutral/effective tertaut, melalui `post_journal` yang sama;
  tidak memberi wewenang tanggal buku arbitrer.
- `ERP_BEST_PRACTICES.md` A2/A4: semua dasar tanggal yang dilihat owner
  diperiksa; tanggal asli tetap, pengakuan terlambat memakai buku sah.
  D15-1 secara eksplisit mengatur kas pada dua dasar tanggal, koreksi dan
  larangan membuka periode otomatis. Ini bukan kutipan kebijakan baru
  pengakuan kredit pelanggan dari owner.

## Expected dicatat sebelum ada uji fitur

Nominal berikut dalam rupiah; penjualan1000 tanggal18; nilai retur200
tanggal19; pencatatan perintah pada20. Untuk A/B seluruh hari masih terbuka,
sehingga tanggal ekonomi dan buku sama. Tidak ada refund/pemakaian kredit.

| Kasus | Sumber pembayaran | Expected akhir19 | Expected akhir20 |
|---|---|---|---|
| A | 1000 pada20 | AR800, kredit0 | AR0, kredit200 |
| B | 900 pada18,100 pada20 | AR0, kredit100 | AR0, kredit200 |

Expected ini **inferensi konservasi dari jurnal sumber dan cakupan tanggal**,
bukan hasil runtime atau keputusan owner baru. Pada A, jurnal retur19
mengurangi AR dari1000 menjadi800; belum ada dana19. Pada20 pembayaran1000
membuat kelebihan200 yang perlu dipisah menjadi kewajiban kredit.
Pada B, pembayaran900 sudah ada18: retur19 menghasilkan kelebihan100,
dan pembayaran100 berikutnya menambah kelebihan100 pada20.

Rancangan awal menghitung K dari pembayaran terkini lalu meletakkan seluruh
K pada tanggal retur. K200 pada19 menghasilkan A: AR1000/kredit200 pada19,
dan B: AR100/kredit200 pada19. Keduanya salah untuk cakupan itu walaupun
saldo terkini20 cocok. Satu tanggal pilihan operator tidak mewakili kedua
bagian B. Pembagian turunan yang perlu dibuktikan: A200 bertanggal20;
B100 bertanggal19 dan100 bertanggal20, dengan lineage pendanaan nyata.

### Periode yang kemudian dibuka kembali

Counter lanjutan: pembayaran900 ekonomi18/buku20 (dicatat ketika buku
ditutup sampai19); kemudian owner secara sah membuka hingga17; retur200
ekonomi19/buku19 dimasukkan. Tambahkan pembayaran100 ekonomi20/buku20.
Profil ekonomi memerlukan kredit100 pada19 dan200 pada20; profil buku
memerlukan kredit0 pada19 dan200 pada20. Bagian pertama dapat memerlukan
pasangan ekonomi19/buku20. Resolver sekarang akan memberi19/19 bila hanya
diberi19 sesudah pembukaan, jadi memecah berdasarkan ekonomi saja belum
menyelesaikan masalah.

Tidak ditemukan hook posting pasangan ekonomi/buku terpisah yang sudah
terikat sumber. Ini batas rekayasa yang perlu diimplementasikan atau
ditolak secara jelas pada alur yang belum didukung; bukan alasan mengubah
tanggal sumber, memalsukan status tutup buku, menambah flag sesi umum,
atau meminta owner mengulangi izin fitur retur lunas.

## Keputusan rancangan dan bukti yang masih diperlukan

1. **Tolak rancangan satu K/satu tanggal sebelum implementasi.** Nilai
   terkini P+U−I bukan pembaca historis. Simpan penerbitan/pembalikan dan
   lineage sumber immutable; jangan hitung I dari sisa yang belum dipakai.
2. Rencanakan bagian kredit dari jurnal pendanaan dan retur yang sebenarnya,
   termasuk incoming credit, serta tanggal ekonomi **dan** buku yang
   tersimpan. Nominal kedua profil harus berkonsiliasi dengan GL, AR dan
   kewajiban kredit. Algoritme final belum dibuktikan di sini.
3. Bila diperlukan penulis pasangan tanggal baru, ikat sempit ke PID/tx,
   actor/request, sumber retur dan pendanaan, nominal, pasangan tanggal,
   account serta payload. Pertahankan period lock, keseimbangan jurnal,
   account_daily_balances, detector, audit, dan izin sesudah menunggu.
   Tidak ada otorisasi pasangan tanggal bebas.
   Usulan komposisi: private copy Native `post_journal` dengan hash sumber
   dan verifier tepat, mengikuti pola private inverse yang sudah ada;
   ubah hanya penentuan buku menjadi maksimum resolver sah dan lantai
   sumber yang diverifikasi. Pertahankan identitas unik setiap bagian,
   pembulatan sen, audit pergeseran serta capture/restore yang lengkap.
   Ini masih usulan; jangan memasang helper tanpa semua pemakainya.
4. Ketersediaan per kredit pada setiap dasar tanggal harus cukup sebelum
   refund/apply. Refund tanggal19 pada A harus menolak; pada B hanya100
   tersedia19 pada contoh buku terbuka. Pemeriksaan ini tidak mengganti
   penjaga saldo kas D15-1 atau periode.
5. Tambahkan Native oracle A/B/periode dibuka kembali, dua basis tanggal,
   pembayaran yang datang kemudian, koreksi funding/retur/nota, replay,
   race, detector0→+1→0 dan rollback jurnal terakhir. Bandingkan jurnal
   asli/status/posting facts sebelum/sesudah; tidak boleh berubah.

Dua pemeriksa Sol Max menilai counter secara independen sebelum bertukar
temuan. Writer membaca ulang anchor jurnal/tanggal dan laporan; penyelesaian
berasal dari sumber itu, bukan voting. Tidak ada runtime baru untuk counter,
tidak ada fitur kredit selesai, dan tidak ada penerimaan produksi.
