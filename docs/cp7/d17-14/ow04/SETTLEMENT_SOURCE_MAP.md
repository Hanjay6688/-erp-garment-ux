# OW-04 — retur lunas: kontrak, jalur sumber, dan rencana pembuktian

**INTERNAL_WRITER_SOURCE_REVIEW**, pin produk878e0a9c (identik dengan2ad).
Tiga pemeriksa uang/dependensi/UI dan satu pemeriksa fixture memakai pin dan
kontrak yang sama; penilaian awal dicatat sebelum bertukar bantahan. Tidak
ada edit produk dari pembantu atau runtime Native OW-04 baru. Penyelesaian
kredit/refund **belum diimplementasikan**. Perbaikan waktu fisik yang terpisah
ada di PHYSICAL_TIME.md; itu tidak menutup OW-04.

## Yang sudah diperintahkan owner

D17-14 memerintahkan retur lunas menjadi uang kembali atau kredit pelanggan,
riwayat tetap, dengan langkah pembalikan yang jelas. Tidak perlu meminta
izin fitur ini lagi atau menetapkan satu pilihan global: pengguna memilih
per retur. Jangan mengarang kedaluwarsa, akun default atau batch migrasi.

## Hitungan yang harus dipakai bersama

Untuk invoice aktif, buat satu pembaca settlement privat/STABLE:

- P = seluruh pembayaran Native POSTED, termasuk pembayaran yang didanai
  uang muka. Jangan menyebut seluruh P sebagai uang tunai baru.
- U = penerapan kredit Native aktif ke invoice itu yang belum termasuk P.
- I = jumlah **penerbitan awal kredit yang masih aktif** dari retur invoice
  itu; bukan sisa kredit setelah dipakai/direfund.
- E = P + U − I; piutang = `sale_net_total − E`.
- Untuk retur R: kredit baru K = `max(R − piutang_sebelum_retur, 0)`.
  Prasyarat piutang_sebelum≥0, E≥0 dan E≤net_sebelum harus diperiksa; jangan
  mengubah korupsi lama menjadi kredit baru yang melebihi R.

**Batas penting rumus ini:** P/U/I di atas adalah keadaan terkini, bukan
otomatis angka per tanggal. Jangan menerbitkan seluruh K di tanggal retur
apabila sebagian funding baru ada sesudahnya. Counter tanggal yang nyata
di sumber, termasuk tanggal buku setelah periode dibuka ulang, dicatat di
`TEMPORAL_COUNTER_20261020.md`; rancangan satu tanggal untuk seluruh K
ditolak sebelum implementasi. Belum ada runtime settlement dari rumus ini.

Retur tetap Dr pendapatan/Cr piutang R dan mempertahankan gerakan stok/HPP
Native. Penerbitan kredit menambah Dr piutang/Cr kewajiban kredit K dalam
transaksi yang sama. Refund menambah Dr kewajiban kredit/Cr kas K. Refund
menghabiskan kredit; tidak mengurangi I atau E untuk kedua kalinya.

| Kasus, bruto1000 | Retur total | P | U | I aktif | E | Piutang | Sisa kredit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lunas, kredit disimpan | 200 | 1000 | 0 | 200 | 800 | 0 | 200 |
| Lunas, refund200 | 200 | 1000 | 0 | 200 | 800 | 0 | 0 |
| Dibayar900, retur200 | 200 | 900 | 0 | 100 | 800 | 0 | 100 |
| Belum dibayar | 200 | 0 | 0 | 0 | 0 | 800 | 0 |
| Dibayar900, lalu retur200 dan100 | 300 | 900 | 0 | 200 | 700 | 0 | 200 |
| Dibayar900 dan memakai kredit100 | 200 | 900 | 100 | 200 | 800 | 0 | 200 |
| Koreksi retur200→100 sebelum kredit dipakai | 100 | 1000 | 0 | 100 | 900 | 0 | 100 |

Ini expected independen dari sumber, **bukan hasil runtime baru**.

## Daftar perubahan Native yang harus lengkap

Tidak ada satu helper lama yang mencakup semuanya. `erp.sale_net_total(uuid)`
tetap berarti bruto dikurangi retur; jangan menambah kredit ke nilai penjualan.
Pembaca/stok/jurnal pembayaran asli tetap menyajikan nominal asli.

| Sumber/fungsi | Titik yang harus ditinjau/diganti tepat |
|---|---|
| `20ah_cp6_return_allocation_eligibility.sql`, `erp.post_sales_return(uuid)` | Guard raw-paid310–321 dan status429–431. Masukkan settlement terikat sumber sebelum keputusan akhir; bukan menghapus overpayment guard. |
| `20ap_cp6_connected_import_materials.sql`, `erp.post_sales_payment(uuid)` | Kunci sebelum payment-row4983–4994; kapasitas5024–5031; status5066–5070. |
| File20ap, `erp.reverse_sales_payment(uuid,text)` | Kunci5186–5194, dependency dan status5227–5236. |
| `20ac_cp6_temporal_surface_closure.sql`, `erp.reverse_sales_return(uuid,text)` | Dependency7482–7491; status7554–7559. |
| File20ac, `erp.reverse_sale(uuid,text)` | Guard dependency7376–7381, termasuk incoming credit. |
| `erp.reverse_journal(uuid,text)` | Sumber kredit/apply/refund dilindungi seperti POCKET_HPP_PERIOD; generic undo tidak boleh meninggalkan fakta uang aktif. |
| File20ap, `erp.initial_prepayment_targets_v1(uuid)` | CUSTOMER1078–1094 memakai net−E. Signature tepat satu UUID. |
| `erp.v_customer_receivables` | CTE pembayaran di bootstrap gzip27819–27857; pertahankan shape, owner/ACL, security_invoker. paid_amount menjadi E; credit_amount lama tetap max(E−net,0), bukan saldo kewajiban kredit. |
| `erp.run_v253_financial_integrity_checks()` | SALES_PAYMENT_OVERPAY membandingkan pembayaran dengan bruto−retur. Kredit sah tidak boleh menjadi false positive. |
| `erp._v268_financial_report_checks_pre_scope()` | Definisi penuh mutakhir `20260911092622_…20m…sql`:168–219; CTE AR201–215. Tetap sertakan saldo awal dan signed balance. |
| `erp.run_v268_financial_report_checks()` | Definisi BE `20260926050000_…20be…sql`:2676–2720, status dan piutang per pelanggan. Wrapper tidak mengecualikan pemeriksaan AR global lama. |
| `sales/read.sql`, `cp7_sales.header(erp.sales_headers,boolean)` | Raw-paid33–52; financial preview dan open balance memakai pembaca yang sama. |
| `sales/customer-history.sql`, `cp7_customer_history.invoices(uuid)` | Hitungan terpisah40–54 harus sama. Payment-event asli tetap nominal asli; tambah event kredit dengan lineage. |

20ah/20ap/20ac/20be di atas berada di `supabase/release/cp6-t3/`.
Baseline lengkap bisa dibaca dari
`supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`, lalu
komposisikan migrasi/delta sesudahnya. Jangan mengubah berkas release CP6
yang sudah diterima. Pembaca reminder piutang sudah memakai P11header;
laporan keuangan memakai jurnal. `run_v263d_case_claim_read_integrity_checks`
memakai view piutang: makna kolom lamanya harus tetap cocok.

## Kredit, akun dan hubungan yang tidak boleh diputus

- Buat fakta Native baru yang immutable: penerbitan dari retur, penerapan ke
  invoice pelanggan yang sama, refund kas, dan pembalikan tertaut. Jangan
  memakai `bb_customer_credits_v1` dengan batch/retur migrasi buatan.
- Kontrak akun yang ada `bb_check_credit_account_v1`: akun aktif/postable
  LIABILITY/CREDIT, bukan kas/mapping/prepayment dan bukan saldo jurnal tak
  terjelaskan. Pilih dan snapshot akun nyata per penerbitan. Pemeriksa lama
  hanya mengenali sumber BB; perlu mengenali lineage Native yang direkonsiliasi,
  supaya penerbitan kedua tidak ditolak atau akun asing dibolehkan.
- Sisa kredit diperiksa per kredit dan menurut tanggal ekonomi **dan** buku.
  Tidak boleh dipakai/refund lebih dari kapasitas atau sebelum tersedia.
- Urutan undo mengikuti dependency: penggunaan kredit/refund → penerbitan
  dan retur bersama → pembayaran/funding asal → penjualan. Barang retur yang
  sudah dipakai tetap mempunyai penghalang fisiknya sendiri.
- Incoming credit yang mendanai retur-kredit lain harus ikut terlindungi.
  Ubah review token invoice/return/chain dan tampilkan nomor serta tautan
  dokumen penghalang kedua sisi. Riwayat REVERSED bukan pemakai aktif.

`sales/chain-reversal.sql`:156–173 kini pembayaran→retur→sale; perlu diubah.
`sales/correction.sql`:278–325 kini replay retur **sebelum** pembayaran.
Menghitung ulang kredit pada langkah itu akan menghasilkan nol, kemudian
pembayaran1000 melebihi net800. Susun ulang komposisi atau carry funding
yang benar-benar terikat sumber; jangan memakai bypass. Payment correction
dan return correction juga harus menyelesaikan dependency kredit dahulu.

## Kunci, tanggal, akses dan pemulihan

Pertahankan envelope/request → FG_HPP_SALES_V2620C → pembayaran → retur →
header/items/alokasi, koleksi dikunci berurutan. Kredit lintas invoice harus
mengunci sumber dan tujuan. Native post/reverse payment sekarang belum
mengambil FG; menambahnya harus **sebelum** payment-row agar urutan sama.
Refund ikut CP7_CASH dan dated-guards ekonomi/buku, periode serta pemeriksaan
akhir compound correction. Izin/token diperiksa lagi sesudah menunggu.

Context privat bukan otorisasi umum: ikat PID, tx, actor, UUID, action,
retur/invoice sumber, invoice tujuan, jumlah, tanggal, akun dan payload.
Jumlah berasal dari hitungan server; kehadiran context/GUC tidak boleh
menghapus guard. Refund butuh otorisasi kas penulisnya, bukan hanya AR view.
Native dipanggil langsung tanpa pilihan settlement tetap gagal-tertutup.

Tambahkan bundle dengan capture/expected_definitions/extension/verify/restore
tepat. Dua pembuat private inverse (`sales/correction.sql`:145–179 dan
`sales/return-correction.sql`:192–221) berjalan sebelum delta akhir tertentu:
pasang delta sebelum derivasi atau komposisikan salinan dan verifier secara
eksplisit. `cp7_report_accounts_bundle.py` sudah mengubah kedua V268 reader;
komposisikan transformasinya, jangan longgarkan hash/daftar perubahan.
View-restore mengikuti `cp7_rework_eligibility_bundle.py`:34–60.
Rollback instalasi ditolak setelah **pernah** dipakai, termasuk seluruh
event sudah dibalik; saldo aktif nol bukan izin menghapus riwayat.

## UI dan kontrak expected

`ConnectedSalesPage`→`SalesReturnPanel`→erp_cp7_save_sale_v1 sudah memakai
envelope SALES. Tambahkan pilihan per-retur eksplisit, rincian pengurangan
piutang/kredit/refund, akun kewajiban sah dan rekening/waktu refund bila perlu.
Amount final dihitung server. Panel kredit perlu saldo+event, pakai sebagian
ke invoice pelanggan yang sama, refund sebagian dan undo tertaut.
Refetch invoice sumber/tujuan dan kredit sebelum membuka penulis kembali.
Jangan menjadikan import-only `APPLY_OPENING_AR` sebagai jalur invoice Native.

**Bantahan yang diselesaikan:** ada usulan memensiunkan seluruh
P11_RETURN_PAID_REFUSAL. Sumber payload tidak mengandung pilihan settlement;
penolakan untuk paid80/return20 tanpa pilihan tetap benar dan harus atomik.
Pertahankan kontrol negatif itu. Tambahkan positif **CREDIT/REFUND eksplisit**;
jangan mengubah expected agar payload tanpa pilihan diam-diam memilih mode.
Kedua pemeriksa membaca ulang sumber dan mengoreksi implikasi awalnya.

## Fixture dan bukti yang harus dibuat

Fixture kecil: `payments.fixture(cur,today,qty=5,price='200',discount='0',stock=10)`,
gudang tujuan melalui `returns.location`, bayar1000/900/0, pilih alokasi asal
1PCS, nilai retur200. HPP sumber FOUND_AT_OPNAME10/PCS; expected FG+10,
COGS−10, asal5PCS, tujuan1PCS. Ini bukan bukti produksi.

Fixture produksi E01 terpisah: 60PCS dari tiga lot10/20/30, HPP15; jual40×25,
bayar1000, retur8 senilai200. Expected FG28/nilai420, COGS480, pendapatan800,
laba kotor320, AR0; kredit200 atau kas turun200. E01 lama AR175 dipertahankan.
Snapshot pembayaran harus mencakup status, waktu/nomor, posting fact, jurnal
asli+baris dan reversal facts; seluruhnya tetap pada penerbitan kredit/refund.

Setelah API explicit dipilih, deklarasikan kasus baru sebelum menjalankan:
paid/partial/unpaid; berulang; apply+refund sebagian; pelanggan salah; kapasitas;
koreksi retur/pembayaran/nota; source-used; UUID/reply-loss/revoked replay;
race dua pengguna kredit dan kas; izin dicabut setelah blocking terlihat;
fault pada jurnal refund terakhir dengan nol residu; tanggal ekonomi/buku
berbeda dan periode tertutup; detector sehat serta kontrol0→+1→0.
Browser desktop/HP harus membayar **sebelum** retur dan menyelesaikan
apply/refund/undo. Browser lama yang retur dahulu lalu bayar tidak cukup.

Belum ada runtime positif settlement, bukti kecepatan atau status selesai
OW-04 dari dokumen ini. Tidak ada keputusan owner baru yang dibuat.
