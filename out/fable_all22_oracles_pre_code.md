# Oracle pre-code — 22 state ALL saldo awal (6 keluarga)

Ditulis dari teks kontrak SEBELUM kode penulis dibaca. Sumber: M = `ERP_V3_2_Master_Pulih_20260923.md`
(baris dikutip persis); P = `ERP_V3_2_Perubahan_Pulih_20260923.md` (duplikat isi M pada titik yang dicek, tidak
dikutip ulang kecuali beda); Addendum D01–D05 = `ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` (disahkan tertulis
"sah bos" 25 Sep 2026); §29.6 = rute impor yang ADA menurut `cp6-au-r1-handoff.md` (hanya lokasi rute, bukan
otoritas nilai); GPT = `gpt_all_round8_binding.md` (hipotesis sejawat, bukan otoritas). Cutover = tanggal E.
Aturan umum yang berlaku pada SELURUH 22 state, tidak diulang tiap baris kecuali relevan:

- **Scope ALL disahkan** (M:1024, tidak boleh ditanyakan ulang): master, stok/nilai awal, kas/piutang/utang/uang
  muka, dokumen operasional terbuka.
- **Tidak menggandakan stok/uang** dan **tidak mengarang histori** (M:1025/M:3818, M:369, M:930–938).
- **Draft editable, finalize memakai isi terakhir di bawah lock** (M:1025, M:3818 "Prepare tetap DRAFT dan
  editable... validasi/prepare terbaru menentukan yang diposting").
- **Total kontrol tidak diposting**, hanya rekonsiliasi rincian vs total (M:44–45, M:934, M:629).
- **Exactness**: seluruh qty/nilai diproses exact, tidak dikonversi ke JS Number (M:365, dikuatkan M:3816–3826
  "Atomic... Idempotent dan fail-closed... Satu ledger stok resmi... Identitas exact").
- **D02** (M:629–648 + addendum bagian 4): operasi yang MENURUNKAN sisa uang muka/kasbon hanya boleh memakai
  kapasitas pada tanggal operasi itu; kode penolakan `BA_ADVANCE_DATED_CAPACITY`.
- Rute §29.6 hanya menunjukkan JALUR ADA, bukan nilai yang benar — nilai tetap berasal dari kontrak (M), tidak dari
  keberadaan rute.

---

## Keluarga P — Pembelian/GRNI

### P01 — Diterima belum ditagih, sebagian terpakai
**Kontrak.** M:829 (Template-18 `UNINVOICED_RECEIPT`: "menghubungkan identitas supplier/penerimaan/baris/tanggal
asal ke `opening_source_key`... mewakili kewajiban yang masih belum ditagih, bukan penerimaan fisik kedua"); M:363
(`OPENING_COST_ORIGIN`: "jumlah penerimaan = sisa bahan awal + seluruh jumlah asal biaya terpakai"); M:831 ("jurnal
kewajiban awal mendebit OPENING_EQUITY dan mengkredit GRNI_MATERIAL pada cutover. Tidak ada jurnal
MATERIAL_PURCHASE, reclass AP sementara, invoice historis atau pembayaran historis sintetis"); M:383–388 (skenario
utama, angka fixture di bawah); M:845 (header opening tidak bisa jadi REVERSED lewat reversal pembelian biasa).
**Fixture (dari kontrak, skenario utama).** Penerimaan 12 unit bahan @10 sebelum E, belum ditagih. Sisa fisik
gudang 4 unit (=40); 8 unit sudah terpakai sebelum E → origin WIP 8 pcs (=40), BS 2 pcs (=20), FG 4 pcs (=20).
GRNI_MATERIAL awal = 120 (estimated).
**Setelah impor.** Bahan 40; WIP 60 (40+20 BS-related tercermin di WIP baris kontrol terpisah — lihat W02/W03);
FG 20; GRNI 120 kredit, OPENING_EQUITY 120 debit; HPP status **ESTIMATED** (M:396 "HPP tetap ESTIMATED selama
sumber penerimaan terkait belum seluruhnya dicocokkan dengan nota"). Tidak ada movement MATERIAL_PURCHASE historis.
**Setelah lanjutan (invoice pemasok).** Invoice memakai harga aktual 12/unit atas 12 unit: bahan 48, WIP 36, FG 48,
biaya lainnya 12 (M:389, baris "Setelah harga nota menjadi 12"). Recost menembus WIP/FG/COGS via movement OPENING
tertaut; GRNI_MATERIAL turun ke 0; AP naik 144; HPP menjadi kepastian final untuk lot yang tercocokkan.
**Setelah inverse (batal invoice / retur).** Recost balik ke nilai opening 40/60/20 apa adanya; retur supplier
tidak boleh mengambil dari 8 unit yang sudah habis dipakai sebelum E (M:363 "Retur supplier tidak boleh mengambil
kuantitas yang telah habis sebelum cutover").
**Ditolak.** Retur atas qty yang sudah 100% terpakai pra-cutover; pembayaran GRNI sebelum invoice; kedua kali impor
penerimaan yang sama lintas batch (M:845, M:81 "dokumen yang sama lintas batch ditolak"); jalur pembelian biasa
memasukkan nomor penerimaan yang sudah diimpor opening.
**Rute §29.6.** MAPPED — `UNINVOICED_RECEIPT` + stok sisa (`MATERIAL_ROLL`/OBI MATERIAL) + `OPENING_COST_ORIGIN` →
invoice `save_material_supplier_invoice_draft_v2`/`post_material_supplier_invoice_v2` → recost origin → bayar.
**Status.** ORACLE_READY.

### P02 — Hutang supplier sudah diinvoice, sebagian dibayar sebelum cutover
**Kontrak.** M:934 ("Nilai awal 100 dikurangi pembayaran lama 32,75 harus sama dengan amount/saldo 67,25. Nominal
dan pembayaran lama disimpan sebagai fakta asal pada registry privat; opening subledger/jurnal hanya mengakui
67,25. Tidak dibuat invoice penjualan/pembelian atau arus kas historis palsu"); M:936 (lima jenis saldo termasuk
SUPPLIER_PAYABLE; pola pembayaran lanjutan).
**Fixture.** Invoice asli 100,00; dibayar historis 32,75 sebelum E; saldo awal yang dibukukan = 67,25 (fakta asal
100,00/32,75 tersimpan sebagai provenance privat, tidak dijurnal ulang).
**Setelah impor.** OPENING_EQUITY debit 67,25 / SUPPLIER_PAYABLE kredit 67,25. Bank tidak berubah (tetap 100,00 —
pola M:936 "Bank awal 100 tetap 100 saat impor"). Tidak ada dokumen invoice pembelian native yang dibuat.
**Setelah lanjutan (bayar sisa).** Pembayaran 7,25 → sisa payable 60,00; bank turun sesuai kas keluar aktual
(pola M:936 "pembayaran berikut 7,25 memberi sisa 60 dan arus bank yang tepat").
**Setelah inverse.** Reversal pembayaran kembali ke 67,25; bank kembali 100,00 (M:936 "reversal kembali ke 67,25
dan bank100").
**Ditolak.** Membayar ulang bagian 32,75 yang sudah lunas historis (tidak ada dokumen untuk itu — hanya 67,25 yang
bisa disettle); koreksi opening yang menyusutkan saldo di bawah bagian yang sudah dibayar/opening tersisa; nominal
sisa salah/tanggal dokumen melewati E ditolak tanpa perubahan ledger (M:938).
**Rute §29.6.** MAPPED — OBI SUPPLIER_PAYABLE (`settled_before_cutover`) → OSS cabang supplier / APPLY uang muka
supplier. Catatan handoff: "Tidak ada invoice native, jadi tidak ada retur/match ke invoice lama" — retur atas
P02 tidak tersedia sebagai retur pembelian biasa, hanya sebagai koreksi opening tertaut.
**Status.** ORACLE_READY.

### P03 — Penerimaan sebagian sudah ditagih, sebagian belum
**Kontrak.** Gabungan P01+P02: M:829 (UNINVOICED_RECEIPT) + M:934 (SUPPLIER_PAYABLE); fixture bertahap di M:817–820
(checkpoint gelombang penerimaan): "10 unit bahan estimasi 10... Setelah invoice 3×8,25: WIP 82,37; FG 49,43;
COGS 32,95; AP 24,75; GRNI 70. Setelah 7×11,75: WIP 88,50; FG 53,10; COGS 35,40; AP 107; GRNI 0."
**Fixture.** Penerimaan tunggal 10 unit bahan estimasi @10 (GRNI awal 100) sebelum E. 3 unit sudah diinvoice
sebelum E @8,25 (AP 24,75 terbentuk, GRNI turun 30→70 sisi yang tertagih); 7 unit masih belum ditagih (GRNI 70
tetap terbuka).
**Setelah impor.** Dua baris tercatat dari SATU penerimaan fisik: OBI SUPPLIER_PAYABLE untuk bagian tertagih (AP
24,75, sudah final) + UNINVOICED_RECEIPT untuk 7 unit sisa (GRNI 70, ESTIMATED). WIP/FG/COGS opening mengikuti
origin gabungan tanpa duplikasi stok — satu penerimaan fisik, bukan dua.
**Setelah lanjutan.** Invoice susulan atas 7 unit sisa @11,75: GRNI turun ke 0; AP total naik 107; WIP/FG/COGS
recost naik ke 88,50/53,10/35,40 (angka kontrak persis).
**Setelah inverse.** Pembatalan invoice susulan mengembalikan GRNI ke 70 dan WIP/FG/COGS ke nilai sebelum invoice
kedua (82,37/49,43/32,95); pembatalan tidak menyentuh AP 24,75 yang sudah final dari bagian pertama.
**Ditolak.** Menagih ulang 3 unit yang sudah final; membayar GRNI 70 sebagai invoice tanpa invoice sah; mencampur
ringkasan saldo dengan rincian dokumen walau total aritmetika cocok (M:98).
**Rute §29.6.** PARTIAL — dua baris OBI terpisah untuk satu penerimaan. **Celah:** "Satu identitas penerimaan untuk
kedua bagian; qty tertagih tidak tersimpan di penerimaan" — risiko qty 3+7 tidak diverifikasi = 10 fisik pada level
adapter.
**Status.** NEEDS_OWNER_INPUT — nilai yang hilang: kontrak belum menegaskan bagaimana identitas penerimaan tunggal
dipecah menjadi dua rincian opening tanpa risiko qty invoice > qty fisik (persamaan P03 = P01-share + P02-share
harus dijadikan validator eksplisit, belum ada di M).

### P04 — PO pembelian belum diterima / draf pengadaan
**Kontrak.** Tidak ada klausul M eksplisit untuk komitmen pembelian bahan yang belum diterima sama sekali sebagai
item saldo awal — hanya `OPEN_PO` (M:359, target produksi per PO) dan `UNINVOICED_RECEIPT` (mensyaratkan penerimaan
fisik ada). M:930–938 melarang mengarang histori demi adapter kosong.
**Fixture (usulan auditor, konsisten dengan pola kontrak).** PO pembelian bahan 10 unit @10 (nilai komitmen 100),
belum ada penerimaan fisik apa pun pada E.
**Setelah impor.** Tidak boleh ada movement stok, tidak boleh ada GRNI/AP, tidak boleh ada OPENING_EQUITY yang
terbentuk — hanya identitas komitmen (nomor PO, tanggal, target qty/nilai, status DRAFT/OPEN) tersimpan sebagai
referensi, tanpa efek keuangan/stok (selaras M:359 "PO selesai atau dibatalkan tidak menerima saldo produksi yang
belum selesai" — pola yang sama berlaku: PO yang belum ada penerimaan tidak menerima saldo GRNI palsu).
**Setelah lanjutan.** Penerimaan pertama pasca-E memakai jalur pembelian native biasa (bukan opening), qty/nilai
menurut penerimaan aktual — bukan menurut komitmen lama yang mungkin berubah.
**Setelah inverse.** Pembatalan PO tanpa penerimaan tidak menyisakan efek apa pun untuk dibalik.
**Ditolak.** Impor yang membukukan penerimaan/GRNI untuk PO yang belum ada barang fisik masuk (M:831 "Tidak ada
jurnal MATERIAL_PURCHASE... historis sintetis" berlaku analog); menganggap qty PO = qty commitment yang otomatis
menjadi utang.
**Rute §29.6.** NO_ADAPTER — "Impor hanya menulis penerimaan POSTED. Dicari: purchase order, PURCHASE_ORDER,
OPEN_PURCHASE, header DRAFT" — tidak ada.
**Status.** NEEDS_OWNER_INPUT — kontrak tidak menyebut sama sekali template CSV untuk komitmen pembelian bahan
belum diterima; owner perlu memutuskan apakah P04 masuk cakupan ALL (dokumen operasional terbuka, M:1024) atau
sengaja di luar cakupan karena tidak ada efek keuangan/stok untuk dibawa.

---

## Keluarga S — Penjualan

### S01 — Invoice penjualan lama, piutang belum lunas
**Kontrak.** M:934–936 (lima saldo termasuk CUSTOMER_RECEIVABLE, pola dan angka sama seperti P02 tetapi pihak
kredit/pelanggan). M:1024 (dokumen operasional terbuka termasuk piutang).
**Fixture.** Invoice penjualan asli 100,00; diterima historis 30,00 sebelum E; saldo awal piutang = 70,00.
**Setelah impor.** OPENING_EQUITY kredit 70,00 / CUSTOMER_RECEIVABLE debit 70,00. Tidak ada `sales_headers`/invoice
penjualan native yang dibuat (M:934 "Tidak dibuat invoice penjualan/pembelian... historis palsu"). Tidak ada
pengurangan stok kedua — barang sudah keluar historis, opening hanya membawa nilai piutang.
**Setelah lanjutan (tagih 25,00).** Piutang turun ke 45,00; kas masuk 25,00 dicatat pada tanggal penagihan aktual
(bukan E).
**Setelah inverse.** Reversal pembayaran kembali piutang ke 70,00; kas keluar 25,00 dari saldo bank.
**Ditolak.** Menagih di atas piutang tersisa; menagih bagian 30,00 yang sudah lunas historis (tidak ada dokumen);
tanggal pembayaran mendahului E atau mendahului tanggal dokumen invoice asal (D02, `BA_ADVANCE_DATED_CAPACITY`
berlaku analog untuk kapasitas piutang).
**Rute §29.6.** MAPPED — OBI CUSTOMER_RECEIVABLE → OSS cabang AR / APPLY uang muka pelanggan ke OPENING. Catatan:
"Tidak ada `sales_headers`, jadi tidak ada retur/nota kredit ke invoice lama" — retur atas invoice S01 lama tidak
tersedia sebagai retur penjualan biasa.
**Status.** ORACLE_READY.

### S02 — Draf penjualan dengan reservasi resmi terbuka saat cutover
**Kontrak.** M:2354 ("tidak ada mandat membuat modul order, CRM, promosi atau reservation kedua"); M:3821 ("Satu
ledger stok resmi... Pengecualian sales DRAFT mengurangi availability melalui reserve resmi sekali; edit/cancel
merekonsiliasi; POST tidak stock-out kedua. Jangan menghidupkan pengurangan ATP/reserved kedua"); M:3032 (FG
availability dipengaruhi sales DRAFT sekali, WIP hanya proyeksi).
**Fixture (usulan auditor, konsisten pola GPT).** FG fisik 10 pcs pada cutover; 3 pcs sudah direservasi oleh draft
penjualan lama (belum POST) sebelum E.
**Setelah impor.** Stok FG opening 10 pcs dibukukan penuh (fisik). Reservasi 3 pcs pada draft lama TIDAK dapat
dibawa masuk sebagai fakta opening — tidak ada `sales_headers`/`save_sale_draft_v2` untuk diimpor, sehingga
availability resmi tercatat 10/10 tersedia sampai draft itu dibuat ulang secara operasional.
**Setelah lanjutan (draft baru dibuat menagih 3 pcs, lalu POST).** Reserve resmi terjadi SEKALI saat draft baru
disimpan; POST tidak mengurangi stok kedua kali (M:3821).
**Setelah inverse.** Cancel draft baru mengembalikan availability tanpa histori draft lama yang hilang direkonstruksi.
**Ditolak.** Mengarang draft lama sebagai dokumen operasional baru dengan tanggal fisik E palsu; mengurangi ATP dua
kali (reserve opening + reserve draft baru) untuk 3 pcs yang sama.
**Rute §29.6.** NO_ADAPTER — "stok FG bisa diimpor, reservasi tidak". Dicari: `sales_headers`, `save_sale_draft_v2`,
`reserve` — tidak ada jalur opening.
**Status.** NEEDS_OWNER_INPUT — kontrak eksplisit melarang membuat reservation module kedua (M:2354), tapi tidak
menjawab: apakah reservasi lama yang belum POST HILANG dari sistem baru (availability penuh 10/10, mandor/sales
harus reservasi ulang manual) — ini pilihan bisnis, bukan hanya celah teknis. Owner perlu menegaskan salah satu.

### S03 — Retur/kredit/refund penjualan lama masih terbuka
**Kontrak.** M:629 ("pelanggan memakai kewajiban/kredit" pada `OPENING_ADVANCE`); tabel enam siklus M:638–643
(67,25 → pakai 12,75 → refund 10,00 → pakai 44,50 → lunas 10,00 → balik semua); D02 (kapasitas bertanggal).
**Fixture.** Kredit pelanggan lama (dari retur/nota kredit yang belum di-refund) senilai 67,25 sebelum E, dibukukan
sebagai `OPENING_ADVANCE` pihak CUSTOMER (akun kewajiban/kredit).
**Setelah impor.** OPENING_EQUITY debit 67,25 / akun khusus uang muka pelanggan kredit 67,25. TIDAK ada
`sales_returns` fisik yang ditulis — hanya nilai kredit yang dibawa, bukan retur barang historis.
**Setelah lanjutan (pakai ke invoice baru 44,50, lalu refund kas 22,75).** Sisa kredit turun sesuai APPLY/REFUND
tertaut immutable (pola tabel M:638–643); refund tidak boleh melebihi sisa pada tanggal refund (D02).
**Setelah inverse.** Balik seluruh pemakaian/refund mengembalikan kredit ke 67,25 tepat, bank kembali ke posisi
semula (pola M:643 "Balik seluruh pelunasan, pemakaian dan refund").
**Ditolak.** Refund bertanggal sebelum kapasitas tersedia (`BA_ADVANCE_DATED_CAPACITY`); menganggap kredit ini
sebagai retur fisik baru yang menambah FG perusahaan.
**Rute §29.6.** PARTIAL — kredit pelanggan via `OPENING_ADVANCE` CUSTOMER + PREPAYMENT APPLY/REFUND (BA). Celah:
"Retur fisik penjualan lama (`sales_returns` tidak ditulis). Apakah uang muka sah sebagai pengganti nota kredit
adalah pertanyaan kontrak" (kutipan langsung handoff §29.6).
**Status.** NEEDS_OWNER_INPUT — nilai yang hilang: kontrak tidak menegaskan apakah `OPENING_ADVANCE` CUSTOMER cukup
mewakili nota kredit/retur lama, atau apakah dibutuhkan jenis dokumen "retur lama" terpisah yang mengikat ke
barang/SKU/harga asal (bukan hanya nilai kredit generik).

---

## Keluarga Y — Payroll/Reimbursement

### Y01 — Upah/reimburse mandor diakui, belum dibayar
**Kontrak.** M:936 (CONTRACTOR_PAYABLE termasuk lima saldo yang diuji, pola sama seperti P02); M:3824 ("Upah
berbeda dari reimbursement... Approval mengakui kewajiban; pembayaran menyelesaikan, tidak mengakui biaya kedua").
**Fixture.** Upah mandor diakui 80,00 + reimburse aksesori diakui 20,00 (total kewajiban 100,00) sebelum E; dibayar
historis 40,00; sisa opening CONTRACTOR_PAYABLE = 60,00.
**Setelah impor.** OPENING_EQUITY debit 60,00 / CONTRACTOR_PAYABLE kredit 60,00. Tidak ada payroll baru yang
dibuat/di-approve untuk periode lama — kewajiban ini bukan `payroll_work_items`, hanya nilai utang.
**Setelah lanjutan (bayar 60,00).** Payable turun ke 0; kas keluar 60,00 melalui OSS (settlement saldo awal), BUKAN
melalui payroll run baru — payroll hanya menaut `CASH_ADVANCE` (piutang ke mandor), bukan payable ke mandor
(handoff §29.6 Y01: "Tidak bisa dinetting di payroll").
**Setelah inverse.** Reversal kembali ke 60,00; kas kembali.
**Ditolak.** Membayar 60,00 ini lewat potongan payroll baru (jenis netting yang tidak didukung untuk PAYABLE);
membayar ulang 40,00 yang sudah lunas historis; mengakui kewajiban kedua untuk upah/reimburse yang sama saat
payroll periode berjalan berikutnya diproses.
**Rute §29.6.** MAPPED — OBI CONTRACTOR_PAYABLE → OSS, tunai saja.
**Status.** ORACLE_READY.

### Y02 — Hasil jahit/absensi belum disetujui, komponen carry, reimburse belum dialokasi
**Kontrak.** M:369 ("WIP awal membuat saldo tahap produksi pada tanggal cutover, **tanpa mengarang** cutting, hasil
jahit historis, absensi atau upah lama"); M:38 ("Biaya kerja baru tetap dicatat lewat transaksi domain biasa" —
bukan lewat opening); M:3824 (upah≠reimbursement, entitlement lewat GOOD×BOM sah).
**Fixture.** 10 pcs sudah dijahit sebelum E tapi belum diapprove (upah 50,00 belum diakui); 1 periode absensi
terbuka; entitlement reimburse aksesori atas GOOD tersebut belum dialokasikan.
**Setelah impor.** TIDAK ADA kewajiban upah/reimburse yang dibukukan untuk 10 pcs ini sebagai opening — kontrak
melarang mengarang hasil jahit/absensi/upah historis. Yang boleh dibawa hanya fisik: jika 10 pcs itu sudah menjadi
WIP/FG fisik pada E, itu masuk sebagai OBI WIP/FG biasa (jalur W02/normal), TANPA nilai upah yang belum diapprove
menyertainya sebagai liability.
**Setelah lanjutan.** Approval upah/reimburse untuk pekerjaan pra-cutover harus terjadi melalui transaksi domain
biasa pasca-E (payroll run baru), dengan bukti fisik (attendance cell, sewing event) yang memang ada — bukan lewat
opening. Bila bukti fisik itu sendiri tidak direkonstruksi (larangan mengarang), maka pekerjaan itu efektif TIDAK
bisa diakui sebagai kewajiban baru tanpa data attendance/sewing asli.
**Setelah inverse.** Tidak relevan — tidak ada opening item untuk dibalik.
**Ditolak.** Import yang membukukan upah/reimburse "diestimasi" untuk pekerjaan lama yang belum disetujui; membuat
`payroll_work_items`/`sewing_terminal_events`/absensi retroaktif sintetis untuk menutup kekurangan data.
**Rute §29.6.** NO_ADAPTER — "Impor tidak menulis `payroll_work_items`, absensi, `sewing_terminal_events`,
entitlement reimburse; dok impor melarang mengarang histori" (kutip `docs/cp6-initial-import-progress.md:166`,
dikutip handoff).
**Status.** NEEDS_OWNER_INPUT — bukan celah adapter biasa: kontrak (M:369) secara eksplisit menutup jalur ini demi
integritas data. Nilai yang hilang bukan angka, melainkan KEPUTUSAN: apakah pekerjaan pra-cutover yang belum
disetujui itu HANGUS (tidak pernah bisa diakui) atau owner menyediakan sumber bukti fisik terpisah (mis. kertas
absensi lama) untuk direkonstruksi secara terkendali (controlled adjustment), bukan lewat opening generik.

---

## Keluarga A — Uang muka/kasbon

### A01 — Uang muka supplier/pelanggan/vendor-laundry belum terpakai
**Kontrak.** M:629 (Template-19 `OPENING_ADVANCE`, seluruh isi field); tabel enam siklus M:634–643; D02 (kapasitas
bertanggal, `BA_ADVANCE_DATED_CAPACITY`); M:179 ("Koreksi opening 67,25→80,25 mempertahankan dokumen asli 100,00
dan bagian historis 32,75. Setelah 75,00 dipakai, koreksi/reversal yang membuat kapasitas kurang ditolak").
**Fixture (tabel kontrak persis).** Dokumen asli 100,00 − pembayaran/pemakaian lama 32,75 = saldo awal 67,25.
**Setelah impor.** OPENING_EQUITY debit 67,25 (supplier/vendor, akun aset) atau kredit 67,25 (pelanggan, akun
kewajiban) / akun khusus uang muka 67,25. Bank awal 100,00 tidak berubah saat impor.
**Setelah lanjutan (siklus penuh dari tabel M:634–643).** Pakai 12,75 → sisa 54,50. Refund 10,00 → sisa 44,50,
tagihan tetap 54,50, bank supplier/vendor 110,00, bank pelanggan 90,00. Pakai 44,50 sisa → uang muka 0,00, tagihan
10,00. Lunas kas 10,00 → tagihan 0,00, bank kembali 100,00/100,00.
**Setelah inverse.** Balik seluruh pelunasan+pemakaian+refund → uang muka 67,25, tagihan 67,25, bank 100,00/100,00
tepat (M:643).
**Ditolak.** Refund bertanggal sebelum kapasitas tersedia (contoh addendum D02: saldo 67,25, koreksi naik ke 100
efektif 22 Sep, refund 100 bertanggal 21 Sep DITOLAK — `BA_ADVANCE_DATED_CAPACITY`); pihak beda dari dokumen asal;
nominal melebihi uang muka/tagihan; tanggal mendahului E/tagihan atau di masa depan; GRNI belum ditagih dibayar
sebagai invoice; generic journal reversal atas sumber uang muka.
**Rute §29.6.** MAPPED — `OPENING_ADVANCE` (SUPPLIER/CUSTOMER/VENDOR) → PREPAYMENT `manage_initial_prepayment_v1`
(APPLY/REVERSE_PAYMENT/REFUND/CORRECT/REVERSE_EVENT).
**Status.** ORACLE_READY.

### A02 — Kasbon tunai mandor lama, dipotong payroll masa depan
**Kontrak.** M:749–757 (kontrak proposal kasbon lengkap: `source_kind=CONTRACTOR_CASH_ADVANCE`, `ALLOCATE_CASH_ADVANCE`,
jurnal `Dr CONTRACTOR_PAYABLE / Cr CONTRACTOR_RECEIVABLE` via `PAYROLL_CASH_ADVANCE_DEDUCTION`); M:700–704
(checkpoint numerik: "Nilai dokumen 100 dikurangi pembayaran lama 32,75 menghasilkan kasbon tersisa 67,25"); D02.
**Fixture.** Kasbon asli 100,00 (mandor X), pembayaran lama 32,75 → sisa opening CONTRACTOR_RECEIVABLE 67,25.
Alokasi draft payroll baru: reservasi 30,00 dari sisa 67,25 (bebas 37,25).
**Setelah impor.** OPENING_EQUITY debit 67,25 / CONTRACTOR_RECEIVABLE kredit 67,25 (aset — piutang ke mandor).
Draft allocation 30,00 menyisihkan kapasitas TANPA jurnal (M:753 "Draft allocation menyisihkan kapasitas tanpa
jurnal").
**Setelah lanjutan (payroll approve+pay).** Payment membukukan `Dr CONTRACTOR_PAYABLE / Cr CONTRACTOR_RECEIVABLE`
30,00 (memisahkan kasbon dari penalti); kas keluar hanya sebesar net payroll (gross dikurangi 30,00 kasbon dan
potongan lain); kasbon dikeluarkan dari kategori OTHER_INCOME. Sisa kasbon setelah alokasi = 37,25.
**Setelah inverse.** Reversal payroll membalik jurnal `PAYROLL_CASH_ADVANCE_DEDUCTION` dan memulihkan kasbon ke
67,25; pembatalan payroll UNPAID atau pelepasan draft alokasi membebaskan cadangan 30,00.
**Ditolak.** Alokasi kedua yang bersama-sama melebihi sisa 67,25 (cadangan gabungan dua payroll tidak boleh
melebihi saldo — kontrak checkpoint 716); pembayaran cash langsung yang memakai bagian yang sedang direservasi ke
payroll lain; DML langsung untuk cash advance; approved/paid payroll dilepas lewat editor import.
**Rute §29.6.** MAPPED — OBI CONTRACTOR_RECEIVABLE + `source_kind=CONTRACTOR_CASH_ADVANCE` → `ALLOCATE_CASH_ADVANCE`
→ `set_opening_cash_advance_payroll_v1` → potongan payroll; tunai lewat OSS.
**Status.** ORACLE_READY.

### A03 — Settlement historis dan dokumen yang sudah habis terpakai
**Kontrak.** M:934/M:629 (`settled_before_cutover`/bagian historis disimpan sebagai fakta provenance, TIDAK
dijurnal); handoff §29.6 A03 ("Dokumen yang sudah lunas penuh ditolak — sisa harus >0; pembayaran historis per
transaksi tidak disimpan").
**Fixture.** Invoice supplier lama 100,00, dibayar penuh 100,00 sebelum E (sisa 0). Uang muka lama 50,00, terpakai
penuh 50,00 sebelum E (sisa 0).
**Setelah impor.** TIDAK ADA baris opening yang dibuat untuk dua dokumen ini — hanya dokumen dengan sisa > 0 yang
diterima (M:938 "nominal sisa salah... ditolak"); kalau operator memaksa impor sisa 0, sistem harus MENOLAK, bukan
membukukan baris kosong/nol diam-diam (M:3823 "Unknown bukan nol... final bukan sekadar ada angka").
**Setelah lanjutan.** Tidak ada — tidak ada saldo untuk disettle lagi. Permintaan "bayar ulang" 100,00 atau
"pakai lagi" 50,00 harus ditolak karena tidak ada subledger opening yang mewakilinya.
**Setelah inverse.** N/A — tidak ada opening item.
**Ditolak.** Membayar dokumen yang sisanya 0 sebagai "pembayaran baru" (double payment); membuat kas keluar/masuk
historis sintetis untuk merepresentasikan 100,00/50,00 yang sudah lunas; menggunakan koreksi opening untuk
"menghidupkan kembali" dokumen yang sudah habis tanpa sumber eksplisit baru (identified explicit source, sesuai
GPT hypothesis yang selaras kontrak M:3817 "Dokumen posted immutable").
**Rute §29.6.** PARTIAL — direpresentasikan sebagai agregat `settled_before_cutover` pada OBI keuangan dan
`OPENING_ADVANCE`, bukan sebagai baris transaksi historis individual.
**Status.** ORACLE_READY (untuk arah refusal); NEEDS_OWNER_INPUT untuk satu titik: kontrak tidak menegaskan apakah
UI/registry wajib tetap MENAMPILKAN dokumen yang sisanya 0 sebagai riwayat baca-saja, atau boleh sama sekali tidak
disimpan (M:936 hanya menyebut lima saldo yang diuji, tidak menyebut dokumen nol secara eksplisit).

---

## Keluarga W — WIP/produksi

### W01 — Header PO produksi terbuka
**Kontrak.** M:359 ("target PO harus menampung total WIP/BS. PO selesai atau dibatalkan tidak menerima saldo
produksi yang belum selesai"); M:371 ("PO harus tetap terbuka; finish/cancel ditolak selama WIP/BS awal masih
tersisa"); D03 (produk pada WIP mengikat bila diisi).
**Fixture.** PO produksi target 10 pcs dibuka sebelum E, belum ada WIP/BS fisik yang diimpor untuk PO ini.
**Setelah impor.** Hanya header/target/status yang dibukukan lewat `OPEN_PO` — **TIDAK ADA klaim WIP fisik**
(handoff: "WIP fisik tidak diklaim"). Tidak ada movement stok, tidak ada kerja/upah.
**Setelah lanjutan (WIP 7 + BS 3 ditambahkan terpisah, lalu diselesaikan).** PO tidak boleh di-finish/cancel selama
WIP 7 atau BS 3 tersebut masih ada saldo tersisa; penutupan PO menunggu disposisi keduanya tuntas (M:371).
**Setelah inverse.** Pembatalan PO yang masih punya WIP/BS terbuka DITOLAK (bukan dibatalkan paksa).
**Ditolak.** Finish/cancel PO ini sementara WIP/BS opening masih tersisa; mengisi WIP/BS opening pada PO yang
sudah berstatus selesai/dibatalkan (M:359).
**Rute §29.6.** MAPPED — `OPEN_PO` → `apply_migration_open_pos`; guard selesai/batal ada. Catatan UNSURE handoff:
"Prasyarat pola/BOM/potong tidak diimpor" — belum ditelusuri penuh apakah cutting group/pola perlu ada dulu.
**Status.** ORACLE_READY untuk header/guard; NEEDS_OWNER_INPUT untuk satu titik teknis (bukan nilai bisnis):
apakah PO opening butuh pola/BOM master sudah ada dulu sebelum WIP dapat ditautkan — writer belum menelusuri, jadi
oracle tidak bisa memastikan prasyarat ini tanpa konfirmasi tambahan.

### W02 — WIP fisik SEWING/LAUNDRY diketahui saat cutover
**Kontrak.** M:359 ("SEWING wajib mandor dan LAUNDRY wajib vendor laundry"); M:369–371 (WIP_OUTPUT/completion,
"Sisa dibaca ulang saat pengesahan; jumlah berlebih, versi sisa usang dan tanggal sebelum cutover/di masa depan
ditolak"); skenario utama M:383–388 (WIP 8 pcs = 40, hasil baik 4 pcs memindahkan 20 ke FG); D03 (identitas produk
mengikat, `BA_WIP_OUTPUT_PRODUCT_BOUND`, `BA_WIP_OUTPUT_SOURCE_MISMATCH`).
**Fixture.** WIP SEWING 8 pcs bernilai 40 (mandor wajib terisi) pada PO/ukuran tertentu, tahap "saat cutover".
**Setelah impor.** OBI WIP 8 pcs/40 dibukukan sebagai saldo tahap produksi pada tanggal E; halaman status WIP
menampilkan tahap dengan keterangan "saat cutover", bukan tahap operasional terkini (M:377); tidak ada cutting/
upah historis diciptakan.
**Setelah lanjutan (completion 4 pcs baik).** `complete_initial_import_wip_v1` memindahkan 20 (bagian nilai 4 pcs)
dari WIP ke FG lot PRODUCTION dengan movement QC_GOOD; identitas produk hasil harus sama dengan identitas sumber
(D03) — produk/merek/warna beda ditolak `BA_WIP_OUTPUT_PRODUCT_BOUND`. Sisa WIP = 4 pcs/20.
**Setelah inverse.** Pembatalan completion membuat event dan mutasi kebalikan tertaut: FG −4 pcs/−20, WIP kembali
8 pcs/40; sumber opening asal tidak berubah (immutable).
**Ditolak.** Completion melebihi sisa WIP; UUID sama menggandakan hasil; tanggal completion sebelum E/di masa
depan; versi sisa usang (stale) saat pengesahan; memindahkan WIP SEWING opening langsung ke tahap LAUNDRY tanpa
transaksi domain biasa (celah handoff: "Memindah WIP SEWING pembuka ke laundry... belum ada").
**Rute §29.6.** PARTIAL — OBI WIP ada; WIP_OUTPUT (COMPLETE/REVERSE) ada. Celah: transfer SEWING→LAUNDRY dan upah
sesudah cutover atas WIP opening tidak dipetakan penuh.
**Status.** ORACLE_READY untuk import+completion+inverse; NEEDS_OWNER_INPUT untuk transfer tahap SEWING→LAUNDRY
pada WIP opening (nilai yang hilang: kontrak tidak menjelaskan mekanisme transfer tahap untuk saldo WIP awal,
hanya completion langsung ke FG).

### W03 — BS bernilai teridentifikasi saat cutover
**Kontrak.** M:359 ("BS bernilai membutuhkan identitas produk, ukuran, PO dan pemegang/lokasi yang dikenal");
M:373 ("BS awal terhubung ke kasus BS native. Scrap/writeoff memindahkan bagian nilai BS dari WIP ke biaya lainnya.
Rework yang menghasilkan barang baik membawa bagian nilai BS ke HPP barang jadi; sisa BS tetap mempunyai nilai...
Biaya BS yang dibuang dikecualikan dari biaya PO yang dapat terserap ke barang jadi, sehingga tidak masuk HPP dua
kali"); skenario utama M:383–388 (BS 2 pcs = 20, scrap 1 pcs memindahkan 10 ke biaya lainnya).
**Fixture.** BS 2 pcs bernilai 20 pada PO/SKU/ukuran/tahap (termasuk QC) dan pemegang dikenal, sebelum E.
**Setelah impor.** OBI BS 2 pcs/20 dibukukan sebagai `bs_cases` LEGACY, terhubung ke mesin BS resolution native.
Tidak ada asumsi nilai — jika BS tanpa PO, nilai 0 wajib eksplisit (handoff: "BS tanpa PO bernilai 0").
**Setelah lanjutan — scrap 1 pcs.** 10 (setengah nilai BS) berpindah dari BS ke biaya lainnya (other cost); biaya
BS yang dibuang ini DIKECUALIKAN dari biaya PO yang bisa terserap ke FG (tidak masuk HPP dua kali). Sisa BS = 1
pcs/10.
**Setelah lanjutan alternatif — rework jadi barang baik.** Bagian nilai BS ikut pindah ke HPP FG hasil rework
(bukan ke biaya lainnya); `SAVE_REWORK` sendiri tidak membuat FG/payable — completion hanya pada boundary sah,
GOOD+BS = qty dikirim (M:3823).
**Setelah inverse.** Pembatalan canonical membalik nilai lewat event tertaut: biaya lainnya −10, BS +1 pcs/+10.
**Ditolak.** Membuang BS opening lalu MENYERAP biayanya ke HPP FG lain (double count); duplikasi sumber BS yang
sama dalam batch yang sama; klasifikasi tanpa mengubah histori BS asal.
**Rute §29.6.** MAPPED — OBI BS → `erp_save_bs_resolution_action_v1` (CLASSIFY/REWORK/DISPOSE/HOLD/CLAIM).
**Status.** ORACLE_READY.

### W04 — Potongan menunggu pickup / kelompok cutting belum selesai
**Kontrak.** M:359 menyebut tahap WIP umum (SEWING/LAUNDRY eksplisit disyaratkan mandor/vendor) tapi tidak
menyebut CUTTING sebagai tahap opening yang diterima secara eksplisit dengan aturan sendiri; M:3082 (lineage
native mensyaratkan "cutting group, roll/material asli, pola/revisi... sisa unik" — ini kontrak untuk OPERASIONAL
berjalan, bukan untuk opening).
**Fixture (usulan auditor).** 50 pcs sudah dipotong dari roll sebelum E, belum diambil/dipickup mandor; sisa roll
residual 3 unit yang masih terkait grup cutting yang sama.
**Setelah impor (kondisi seharusnya, belum ada rute).** Idealnya: 50 pcs tercatat sebagai WIP tahap CUTTING dengan
pemegang "gudang cutting" pada E, TANPA mengonsumsi ulang bahan (bahan sudah terkonsumsi historis ke origin, lihat
OPENING_COST_ORIGIN); sisa roll 3 unit tercatat sebagai stok bahan opening biasa.
**Setelah lanjutan.** Pickup mandor mengambil dari 50 pcs opening ini via jalur pickup native, mengurangi saldo
WIP CUTTING opening sekali.
**Setelah inverse.** Pembatalan pickup mengembalikan ke WIP CUTTING opening.
**Ditolak.** Memotong ulang bahan yang sudah dianggap habis via origin (double consumption); mengklaim 50 pcs ini
via header `OPEN_PO` tahap CUTTING saja (header tidak membawa fisik — lihat celah di bawah).
**Rute §29.6.** NO_ADAPTER — "(OPEN_PO tahap CUTTING hanya header). Dicari: cutting_groups, cutting_pickups,
CUTTING" — tidak ada.
**Status.** NEEDS_OWNER_INPUT — kontrak (M:359) tidak menyebut CUTTING sebagai tahap WIP opening yang sah secara
eksplisit (hanya SEWING/LAUNDRY disebut dengan syarat wajibnya); owner perlu menegaskan apakah CUTTING termasuk
"tahap" yang dimaksud M:359 dan apa syarat wajibnya (analog mandor untuk SEWING).

### W05 — Pengiriman laundry di luar, gagal, klaim, atau nota lama
**Kontrak.** M:4210 ("Claim STUCK/MISSING/DAMAGE dan pemulihan barang tetap mengikuti pool/lineage existing.
Invoice/credit/claim settlement tidak boleh membuat barang pulih sementara vendor tetap ditagih penuh tanpa
koreksi yang sah. Refund atau credit vendor tidak menghapus physical receipt yang benar"); M:4207 ("failed-wash
attempt dengan custody RETRY_AT_VENDOR atau RETURN_UNPROCESSED. Jasa gagal yang benar-benar ditagih boleh mencatat
biaya tanpa GOOD/BS palsu").
**Fixture.** Vendor laundry memegang 10 pcs sebelum E; 2 pcs sudah kembali (di luar cakupan opening — sudah jadi
FG/WIP normal); 1 pcs diklaim MISSING dengan status belum settle; vendor payable terkait 30,00 belum dibayar.
**Setelah impor.** WIP tahap LAUNDRY opening = 7 pcs (10 − 2 sudah kembali − 1 klaim dipisahkan sebagai catatan
custody terpisah, BUKAN dihitung sebagai WIP normal karena outcome-nya belum pasti) + OBI VENDOR_PAYABLE 30,00 +
`OPENING_ADVANCE` VENDOR bila ada uang muka. Custody `MISSING` 1 pcs harus tercatat statusnya, bukan diam-diam
masuk hitungan 7 pcs yang "sedang dikerjakan normal".
**Setelah lanjutan (klaim disettle, credit 5,00).** Credit vendor 5,00 tidak menghapus fakta bahwa fisik pernah
diterima vendor; vendor tetap ditagih penuh untuk sisa yang bukan bagian klaim (M:4210). Kembalinya 7 pcs
menyelesaikan WIP LAUNDRY opening via WIP_OUTPUT.
**Setelah inverse.** Pembatalan credit klaim mengembalikan payable ke nilai sebelum credit; status custody kembali
ke sebelum settlement.
**Ditolak.** Menganggap 1 pcs MISSING sebagai "sudah pulih" tanpa koreksi klaim sah; mengirim ulang 1 pcs yang
sama sebagai service source baru tanpa attempt baru yang nyata (retry HTTP UUID sama bukan attempt baru); QC
kedua atas susulan.
**Rute §29.6.** PARTIAL — WIP tahap LAUNDRY + vendor; OBI VENDOR_PAYABLE; `OPENING_ADVANCE` VENDOR ada. Celah:
"Attempt gagal, klaim pending, penerimaan belum tertagih tidak ditulis." `SAVE_CLAIM` pada BS pembuka: UNSURE.
**Status.** NEEDS_OWNER_INPUT — nilai yang hilang: kontrak tidak punya template opening eksplisit untuk status
custody `STUCK/MISSING/DAMAGE` pada barang yang dikirim SEBELUM cutover (hanya operasional berjalan); apakah
klaim lama masuk sebagai WIP LAUNDRY biasa dengan flag tambahan, atau butuh entitas terpisah, belum dijawab M.

### W06 — Rework terkirim/sebagian selesai/komponen belum dibayar
**Kontrak.** M:3823 ("Partial/rework tidak menghasilkan output palsu: SAVE_REWORK tidak membuat FG/payable;
completion hanya pada boundary sah dan total GOOD+BS=yang dikirim. Susulan tidak menjalani QC kedua; qty sumber
tidak dihitung dua kali"); M:373 (rework barang baik membawa nilai BS ke HPP FG).
**Fixture.** Rework dikirim 5 pcs sebelum E (dari BS asal); 2 pcs sudah kembali (GOOD) sebelum E; 3 pcs masih di
rework saat E; komponen rework (aksesori/jasa tambahan) sebagian dibayar 15,00 dari total 25,00.
**Setelah impor (proksi, belum ada rute langsung).** Hanya 3 pcs SISA yang boleh masuk sebagai BS/WIP opening
tertaut rework terbuka; 2 pcs yang sudah GOOD sebelum E TIDAK diimpor ulang sebagai output rework baru (itu sudah
final historis, masuk FG opening biasa bila memang jadi stok). Komponen belum dibayar 10,00 (25,00−15,00) masuk
sebagai CONTRACTOR_PAYABLE opening gabungan.
**Setelah lanjutan.** Completion 3 pcs sisa: GOOD+BS = 3 (boundary sah, M:3823); tidak QC kedua untuk susulan;
bagian nilai BS yang jadi GOOD masuk HPP FG (pola M:373); bayar sisa 10,00 komponen via OSS.
**Setelah inverse.** Pembatalan completion 3 pcs kembali ke BS terbuka; pembatalan pembayaran 10,00 kembali ke
payable.
**Ditolak.** Mencatat ulang 2 pcs GOOD lama sebagai output rework baru (double FG); membayar ulang 15,00 yang
sudah lunas historis; completion 3 pcs dengan GOOD+BS ≠ 3.
**Rute §29.6.** NO_ADAPTER — "(proksi: impor BS lalu rework baru; komponen sebagai CONTRACTOR_PAYABLE gabungan)."
Dicari: `rework_orders`, `rework_component_lines` — tidak ada identitas rework lama sendiri.
**Status.** NEEDS_OWNER_INPUT — nilai yang hilang: tidak ada cara membedakan "3 pcs sisa rework lama" dari "BS
baru" pada level identitas dokumen begitu diimpor lewat proksi BS — owner perlu menegaskan apakah proksi ini cukup
atau dibutuhkan flag/`source_kind` REWORK_CARRY eksplisit seperti pola `CONTRACTOR_CASH_ADVANCE` pada A02.

---

## Keluarga C — Aksesori/kain kantong

### C01 — Aksesori/kain kantong milik perusahaan yang tersedia fisik
**Kontrak.** M:44–45 ("7 PCS adalah aksesori. Impor harus membukukan isi draft terakhir... Kain kantong universal
memakai stok gudang/roll tanpa memaksa saldo per mandor; pengeluaran dasar menjadi biaya periode tanpa HPP
produk"); M:3902 ("Membuat master tidak menambah stok. Nota DRAFT biasa tidak mengurangi stok. Pengambilan mandor
yang posted mengurangi barang detail sekali").
**Fixture.** Aksesori kancing 100 unit @2,00 (stok=200) + roll kain kantong 50 unit di gudang, milik perusahaan,
sebelum E.
**Setelah impor.** OBI MATERIAL (aksesori) 100 unit/200 dan `MATERIAL_ROLL` (kain kantong) 50 unit dibukukan
sebagai stok gudang biasa; tidak ada saldo per mandor yang dipaksa untuk kain kantong (M:47 "tanpa memaksa saldo
per mandor").
**Setelah lanjutan (issue 7 pcs aksesori sebagai nota mandor manual).** 7 buah mengurangi stok tepat 7; tagihan =
7 × harga eceran manual yang diketik (bukan pecahan lusin) — M:1023 ("Tujuh buah mengurangi stok tepat tujuh;
tagihan = 7 × harga manual"). Untuk kain kantong: pengeluaran menjadi biaya periode (lihat C04) tanpa HPP produk
langsung, dengan opsi alokasi ke hasil jahit sah.
**Setelah inverse.** Retur/pembatalan issue mengembalikan stok dan membalik tagihan tertaut.
**Ditolak.** Mengubah 7 pcs jadi pecahan lusin; mengurangi stok kain kantong dua kali (issue + alokasi periode);
membuat entitlement reimburse baru dari sekadar stok tersedia perusahaan.
**Rute §29.6.** MAPPED — OBI MATERIAL/`MATERIAL_ROLL` → `erp_save_accessory_issue_action_v1`;
`erp_save_pocket_fabric_action_v1` REGISTER/POST.
**Status.** ORACLE_READY.

### C02 — Nota aksesori mandor sebelum cutover sudah dibayar sebagian + retur belum terpakai
**Kontrak.** M:4762/M:3912 ("Retur Nota Mandor berbayar: Mandor→receipt tertaut nota. Credit hanya hak yang
terbukti; settlement diperiksa. Batas qty/nominal source, bukan harga master baru"); M:4458 (ACC-DEC05, **belum
diputus**: "Retur nota mandor setelah lunas/parsial: credit, carry atau refund? Pertahankan settlement asli; batasi
hak berdasarkan source; blok finalisasi finansial yang belum didukung").
**Fixture.** Nota mandor lama 10 unit @5,00 (tagihan 50,00), sudah dibayar 20,00 sebelum E (sisa CONTRACTOR_RECEIVABLE
opening 30,00 dengan `source_kind` BALANCE atau CASH_ADVANCE bila dipotong payroll); 3 unit dari nota ini
dikembalikan mandor SETELAH E, belum terpakai.
**Setelah impor.** OBI CONTRACTOR_RECEIVABLE 30,00 (fakta asal 50,00/20,00 sebagai provenance, tidak dijurnal
ulang) — identik pola A02/P02.
**Setelah lanjutan (retur 3 unit pasca-E).** Credit HANYA sebesar hak yang terbukti dari harga/qty nota ASAL
(bukan harga master terbaru); batas qty/nominal mengikuti source nota lama. **Nilai pasti credit/refund/carry
belum ditentukan kontrak** — ACC-DEC05 eksplisit terbuka.
**Setelah inverse.** Pembatalan credit retur kembali ke saldo 30,00 sebelum retur; histori payroll yang sudah
dipakai untuk melunasi 20,00 TIDAK di-reverse otomatis oleh retur ini (M:5238 "Reverse payroll lama otomatis, bayar
dua kali, atau hapus outstanding" — eksplisit DILARANG).
**Ditolak.** Retur ini menghapus outstanding 30,00 tanpa transaksi credit yang tertaut; retur dihargai memakai
harga master terbaru; reverse payroll lama demi mengakomodasi retur; membayar dua kali.
**Rute §29.6.** PARTIAL — hutang sebagai OBI CONTRACTOR_RECEIVABLE (BALANCE) atau CASH_ADVANCE. Celah: "Identitas
nota aksesori; retur aksesori tak terpakai ke nota lama" tidak tertaut.
**Status.** NEEDS_OWNER_INPUT — nilai yang hilang secara eksplisit dari kontrak sendiri (ACC-DEC05, M:4458): owner
belum memilih credit vs carry vs refund untuk retur atas nota yang sudah lunas/parsial. Ini bukan celah audit,
melainkan keputusan bisnis yang secara tertulis "belum diputus" di kontrak.

### C03 — Titipan servis perusahaan/karantina/rusak/pemulihan aksesori
**Kontrak.** M:3933 ("Untuk sisa perusahaan yang sudah bernilai di ledger, perpindahan ke karantina mempertahankan
nilai asal. Untuk bongkaran yang belum memiliki nilai pemulihan sah, boleh ada penerimaan fisik/custody dengan
**nilai pending**, bukan stock-in Rp0 lalu laporan dianggap selesai"); M:4882 ("Satu jumlah barang tidak boleh
sekaligus berada di pos, gudang dan karantina. `Di gudang` dan `Siap dipakai` bukan dua saldo yang ditambahkan").
**Fixture.** 5 unit aksesori company-owned dititip di pos servis (usable); 2 unit dikarantina (kondisi
dipertanyakan, nilai asal tetap dipertahankan bila sudah pernah bernilai di ledger); 1 unit belum kembali dari
servis pelanggan (bukan milik perusahaan — lihat larangan M:3919/M:4785); nilai pemulihan bongkaran "tidak
diketahui" sebelum E.
**Setelah impor.** 5 unit pos + 2 unit karantina dibukukan sebagai OBI MATERIAL DI LOKASI MASING-MASING dengan
kondisi eksplisit — TIDAK dijumlahkan sebagai satu saldo "siap pakai" tunggal (M:4882). Barang pelanggan (1 unit)
TIDAK masuk stok perusahaan sama sekali (M:3919 "servis tidak otomatis menjadi sales return, penambahan FG
perusahaan"). Nilai bongkaran yang belum diketahui = **pending**, bukan Rp0 otomatis (M:3933).
**Setelah lanjutan (pemulihan karantina jadi usable, nilai bongkaran ditentukan 8,00).** Perpindahan lokasi
mempertahankan nilai asal (2 unit karantina tetap nilai lama saat jadi usable); nilai pending 8,00 baru
direkonsiliasi eksplisit ke ledger resmi, bukan menambah stok kedua.
**Setelah inverse.** Pembatalan penentuan nilai bongkaran mengembalikan status "pending"; pembatalan pemulihan
karantina mengembalikan lokasi/kondisi semula.
**Ditolak.** Menjumlahkan pos+gudang+karantina sebagai satu qty "tersedia"; stock-in Rp0 untuk bongkaran lalu
laporan HPP dianggap selesai; membuat entitlement reimburse otomatis dari inspeksi/penerimaan custody.
**Rute §29.6.** NO_ADAPTER — proksi "OBI MATERIAL di lokasi mana pun, tercatat stok perusahaan". Dicari: `custody`,
`quarantine`, `karantina`, `titipan`, `recovered` — tidak ada entitas dedicated.
**Status.** NEEDS_OWNER_INPUT — nilai yang hilang: kontrak (M:3933) mensyaratkan "nilai pending" sebagai status
eksplisit yang harus BISA direpresentasikan, tapi §29.6 tidak menemukan kolom/status pending pada adapter proksi
MATERIAL biasa — perlu owner menegaskan apakah MATERIAL opening bisa membawa flag nilai-pending atau butuh entitas
baru.

### C04 — Kain kantong sudah ditarik / periode alokasi terbuka
**Kontrak.** M:466–479 (kebijakan penuh + fixture numerik empat lifecycle, sudah disahkan owner "ya gas lah
tanggung ye"); M:363 (`OPENING_COST_ORIGIN` — kuantitas satuan bahan, bukan pcs; berlaku juga untuk kain kantong
yang sudah ditarik sebelum E sebagai origin terpakai).
**Fixture (kontrak persis).** Stok kain kantong 20 unit di gudang sebelum periode; 5 unit sudah dikeluarkan
(ditarik) sebelum penutupan periode/cutover; sisa 15 unit. 10 pcs SELESAI_DIJAHIT sah pada periode (termasuk
Afui): 5 pcs masih WIP, 3 pcs FG tersedia, 2 pcs terjual. Biaya kain keluar 11,25 dibagi: WIP +5,62, FG tersedia
+3,38, COGS +2,25.
**Setelah impor.** Sisa fisik 15 unit dibukukan sebagai stok gudang biasa (bukan aksesori per-mandor). 5 unit yang
sudah ditarik SEBELUM E dan sudah dialokasikan (periode ditutup pra-cutover) — nilainya SUDAH final sebagai biaya
periode historis (11,25 sebagai pola), TIDAK diimpor ulang sebagai stok atau biaya baru (larangan biaya ganda,
M:471 "Tidak ada pengurangan stok kedua atau biaya ganda").
**Setelah lanjutan (periode baru pasca-E dengan koreksi nota jadi 15,00).** Denominator = seluruh pcs
SELESAI_DIJAHIT sah periode ITU (bukan periode lama); pengesahan memindahkan 15,00: WIP +7,50, FG +4,50, COGS
+3,00 (angka kontrak persis, pola proporsi 5:3:2 tetap).
**Setelah inverse.** Cancel alokasi memulihkan HPP; setelah nota dibalik, semua akun kembali persis ke baseline
(M:481); header/snapshot sumber tidak ditulis ulang.
**Ditolak.** Pengeluaran baru dalam periode yang masih aktif (harus tunggu periode ditutup/dibatalkan); periode
tumpang tindih; koreksi denominator hasil jahit langsung tanpa membatalkan alokasi lama dulu; perubahan langsung
histori immutable; guard inverse sumber yang sedang dialokasikan.
**Rute §29.6.** NO_ADAPTER untuk opening — celah spesifik: fakta "5 unit sudah ditarik & dialokasikan SEBELUM
cutover" tidak punya template opening (`pocket_fabric_usage` dan periode tidak ditulis impor). Mekanisme
periode/alokasi PASCA-cutover sendiri sudah punya rute penuh dan diuji (136/136 PASS menurut M:453), jadi
kontinuasi (poin 4–6) ORACLE_READY begitu sisa 15 unit berhasil diimpor sebagai stok biasa.
**Status.** ORACLE_READY untuk mekanisme periode/alokasi lanjutan (angka kontrak eksplisit tersedia);
NEEDS_OWNER_INPUT hanya untuk satu titik: bagaimana 5 unit yang SUDAH ditarik+dialokasikan sebelum E dicatat
sebagai fakta opening (biaya periode historis) tanpa menciptakan biaya kedua saat periode baru dimulai — kontrak
belum punya template CSV untuk "alokasi kain kantong historis yang sudah final".

---

## Ringkasan

| ID | Rute §29.6 | Status oracle | Nilai/keputusan yang hilang (bila NEEDS_OWNER_INPUT) |
|---|---|---|---|
| P01 | MAPPED | ORACLE_READY | — |
| P02 | MAPPED | ORACLE_READY | — |
| P03 | PARTIAL | NEEDS_OWNER_INPUT | Validator identitas penerimaan tunggal utk qty tertagih+belum tertagih |
| P04 | NO_ADAPTER | NEEDS_OWNER_INPUT | Apakah komitmen pembelian bahan belum diterima masuk cakupan ALL |
| S01 | MAPPED | ORACLE_READY | — |
| S02 | NO_ADAPTER | NEEDS_OWNER_INPUT | Nasib reservasi draft lama: hangus atau direservasi ulang manual |
| S03 | PARTIAL | NEEDS_OWNER_INPUT | Apakah OPENING_ADVANCE CUSTOMER sah menggantikan nota kredit lama |
| Y01 | MAPPED | ORACLE_READY | — |
| Y02 | NO_ADAPTER | NEEDS_OWNER_INPUT | Nasib pekerjaan lama belum disetujui: hangus atau sumber bukti terpisah |
| A01 | MAPPED | ORACLE_READY | — |
| A02 | MAPPED | ORACLE_READY | — |
| A03 | PARTIAL | ORACLE_READY* | *hanya 1 titik: kewajiban tampil read-only utk dokumen nol |
| W01 | MAPPED | ORACLE_READY* | *prasyarat pola/BOM sebelum WIP ditaut, UNSURE teknis |
| W02 | PARTIAL | ORACLE_READY* | *transfer tahap SEWING→LAUNDRY pada WIP opening |
| W03 | MAPPED | ORACLE_READY | — |
| W04 | NO_ADAPTER | NEEDS_OWNER_INPUT | Apakah CUTTING sah sbg tahap WIP opening + syarat wajibnya |
| W05 | PARTIAL | NEEDS_OWNER_INPUT | Representasi custody STUCK/MISSING/DAMAGE pra-cutover |
| W06 | NO_ADAPTER | NEEDS_OWNER_INPUT | Identitas rework-carry terpisah dari BS biasa (source_kind?) |
| C01 | MAPPED | ORACLE_READY | — |
| C02 | PARTIAL | NEEDS_OWNER_INPUT | ACC-DEC05: credit vs carry vs refund utk retur nota lunas/parsial |
| C03 | NO_ADAPTER | NEEDS_OWNER_INPUT | Status nilai-pending eksplisit pada MATERIAL opening |
| C04 | NO_ADAPTER | NEEDS_OWNER_INPUT | Template opening utk alokasi kain kantong historis yang sudah final |

Hitung: ORACLE_READY penuh 10 (P01,P02,S01,Y01,A01,A02,W03,C01 + A03,W01,W02 dgn syarat kecil) — murni tanpa syarat:
8. NEEDS_OWNER_INPUT 11 (P03,P04,S02,S03,Y02,W04,W05,W06,C02,C03,C04). Bersyarat-kecil 3 (A03,W01,W02).

## Celah kontrak (kutipan)

1. **P03/identitas ganda** — tidak ada kutipan M yang menjelaskan validator "qty tertagih + qty belum tertagih =
   qty fisik satu penerimaan"; hanya diturunkan dari kombinasi M:829 + M:934.
2. **P04** — tidak ada satu pun kutipan M yang menyebut template opening untuk komitmen pembelian bahan belum
   diterima; M:359 hanya menyebut "target PO" untuk PO **produksi**, bukan PO pembelian bahan ke supplier.
3. **S02** — M:2354: "tidak ada mandat membuat modul order, CRM, promosi atau reservation kedua" — melarang solusi
   teknis paling jelas (reservation module baru) tanpa memberi alternatif untuk saldo awal reservasi lama.
4. **S03** — handoff §29.6 sendiri menulis: "Apakah uang muka sah sebagai pengganti nota kredit adalah pertanyaan
   kontrak" — diakui terbuka oleh penulis inventaris rute, bukan hanya oleh auditor.
5. **Y02** — M:369: "tanpa mengarang cutting, hasil jahit historis, absensi atau upah lama" — larangan eksplisit
   tanpa jalur alternatif yang disebut untuk pekerjaan yang benar-benar terjadi tapi belum disetujui.
6. **W04** — M:359 menyebut kewajiban SEWING/LAUNDRY punya syarat wajib (mandor/vendor) tapi tidak menyebut
   CUTTING sama sekali dalam daftar tahap WIP opening yang diakui.
7. **C02/ACC-DEC05** — M:4458, kutipan kolom "Keputusan owner masih dibutuhkan": "Retur nota mandor setelah
   lunas/parsial: credit, carry atau refund?" — status **belum diputus** tertulis eksplisit di kontrak sendiri.
8. **C03** — M:3933 mensyaratkan status "nilai pending" tapi tidak ada satu pun template CSV (dari 19 jenis yang
   disebut M:359–650) yang membawa field status nilai-pending untuk aksesori bongkaran/karantina.
9. **C04** — M:466–511 sepenuhnya menjelaskan mekanisme periode SETELAH cutover, tapi tidak satu kalimat pun
   menjelaskan bagaimana penarikan/alokasi kain kantong yang SUDAH final SEBELUM cutover masuk sebagai fakta
   opening — gap murni antara "kebijakan operasional lengkap" dan "template migrasi historis".
10. **W06** — tidak ada satu pun kemunculan `rework_orders`/`rework_component_lines`/`REWORK_CARRY` di seluruh M;
    kontrak hanya mengatur rework SEBAGAI transaksi operasional (M:3823), tidak sebagai fakta saldo awal.
