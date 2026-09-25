# Oracle pra-kode — 75 kasus C6 asli (39 ACC + 36 LAU)

**Ditulis SEBELUM kode writer ada.** Sumber: kontrak M (`ERP_V3_2_Master_Pulih_20260923.md`), lampiran C6 rev3
(hanya untuk pemetaan baris/ID — bagian 0 lampiran adalah **usulan scope writer, BELUM disahkan owner**), dan
crosswalk GPT (`gpt_c6_75_case_crosswalk.md`). Tidak ada satu pun baris di bawah diturunkan dari kode kandidat
(`cand/src`, `cand/supabase`) atau catatan writer. Nominal pada LAU-T02–T06 memakai contoh owner M:3731 yang secara
eksplisit **ilustrasi, bukan tarif produksi** (M:4335, M:3739) — dipakai di sini sebagai fixture sintetis berlabel,
bukan seed produksi.

Skema tiap kasus:
- **M**: baris master + kutipan pendek.
- **Fixture**: angka yang bisa dibangun auditor.
- **Hasil per leg**: stok/nilai, jurnal/akun, utang kontraktor/piutang, utang vendor, efek HPP, perilaku UI/izin, atau
  refusal persis sesuai kontrak.
- **Dilarang**: apa yang tidak boleh terjadi (stok/uang ganda, histori karangan, nol diam-diam, dsb).
- **Kebijakan**: nilai owner yang belum ada (tarif, akun, pembulatan) → default aman kontrak (tolak/pending) dan
  tanda `PENDING_POLICY_VALUE` bila relevan.
- **Status**: `ORACLE_READY` atau `NEEDS_OWNER_INPUT`.

Skala rujukan tetap yang dipakai berulang: invariant umum M:3816–3826 (posted immutable, atomic, idempotent
fail-closed, tanggal terpisah, satu ledger stok, identitas exact, no fake output/entitlement, unknown≠nol);
aturan 7 PCS M:44–48, M:1023, M:1066–1071 (ACC-DEC02 **sudah diputus**: eceran diketik manual, fisik tetap exact,
tidak ada pembulatan baru); LAU-R01–R24 M:4021–4044; desain laundry disetujui M:3727–3737; register keputusan
M:4448–4479; batas waktu/CR M:1668, M:1691–1699, M:1753–1757.

---

## A. Aksesori — kelompok A (jumlah dan harga Nota Mandor)

#### ACC-A01 — PCS ganjil, dua cara input
- **M**: 5254 — "1, 5, 7, 11, 12, 13, 29 PCS; input lusin+PCS dan Total PCS"
- **Fixture**: nota ke mandor X, harga eceran manual Rp3.250/pcs (ACC-DEC02), qty {1,5,7,11,12,13,29} pcs; 29 dimasukkan dua cara: Total PCS=29, dan 2 lusin+5 pcs (lusin=12).
- **Hasil per leg**: stok berkurang persis sejumlah tiap angka (7 → tepat 7, M:1023); kedua representasi untuk qty fisik yang sama menghasilkan qty tersimpan dan nominal tagihan mandor yang identik (29×3.250).
- **Dilarang**: pembulatan ke kelipatan lusin (7→0 atau 12); dua representasi menghasilkan qty/nominal berbeda.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A02 — stok pas-pasan
- **M**: 5255 — "Stok tinggal 7; permintaan 7 dan 8"
- **Fixture**: stok=7. Permintaan A=7pcs (percobaan terpisah dari B=8pcs).
- **Hasil per leg**: A sukses, stok→0. B ditolak utuh (insufficient stock), atomik, stok tetap 7 setelah percobaan B.
- **Dilarang**: B silently diubah menjadi 7 dan diposting.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A03 — konversi lusin/gross snapshot
- **M**: 5256 — "Faktor 12, gross 144, pack dengan conversion snapshot"
- **Fixture**: item dipak gross=144 dengan snapshot faktor=12 saat terima. Issue dalam lusin/gross/pcs harus dikonversi memakai snapshot itu, bukan master konversi yang mungkin sudah berubah.
- **Hasil per leg**: 144 unit tetap 144 (tidak 143/145); konversi tak dikenal/mismatch ditolak.
- **Dilarang**: memakai faktor master terkini yang berbeda dari snapshot; unit rusak akibat pembulatan konversi.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A04 — input tidak valid
- **M**: 5257 — "COUNT negatif, nol, kosong, pecahan PCS, NaN/Infinity, overflow, format ambigu"
- **Fixture**: -5, 0, "", 3.5, NaN, Infinity, 1e309, "12.34.56".
- **Hasil per leg**: setiap input ditolak atomik di validator (`accessoryIssue.ts`) dan RPC; tidak ada residu draft/stok/jurnal.
- **Dilarang**: nilai dikoreksi jadi 0 atau angka positif; 0 diterima sebagai no-op post; 3.5 dibulatkan.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A05 — UOM desimal
- **M**: 5258 — "Material meter/kg"
- **Fixture**: bahan 12,75 m dan 3,4 kg dibandingkan dengan aksesori ber-UOM PCS.
- **Hasil per leg**: nilai desimal tetap persis (12,75 tetap 12,75); aturan bulat PCS (M:1023) hanya berlaku untuk UOM PCS.
- **Dilarang**: item meter/kg dipaksa validasi integer.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A06 — preview stale
- **M**: 5259 — "Harga berubah, draft berganti tanggal/mandor, posting setelah preview stale"
- **Fixture**: draft mandor=X tanggal=D1 harga snapshot P1; sebelum POST, master harga→P2 dan/atau draft diedit mandor=Y tanggal=D2.
- **Hasil per leg**: POST merevalidasi harga/versi/mandor/tanggal terkini; bila preview stale, POST ditolak (STALE_VERSION) bukan diposting dengan angka lama.
- **Dilarang**: posting memakai P1 setelah P2 berlaku tanpa revalidasi; mandor Y ditagih hasil hitung untuk mandor X.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A07 — nota legacy lintas upgrade
- **M**: 5260 — "Nota posted legacy, payroll dan reversal lama sebelum/sesudah upgrade"
- **Fixture**: nota posted lama (qty, harga, jurnal, potongan payroll, outstanding) sebelum paket T3/upgrade diterapkan; dibaca lagi sesudahnya.
- **Hasil per leg**: qty, nominal, jurnal, potongan payroll, outstanding, histori identik persis sebelum/sesudah upgrade.
- **Dilarang**: upgrade memicu recompute/mass-reprice nota lama.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-A08 — multi-line, retur berulang, batas sen
- **M**: 5261 — "Multi-line, retur sebagian berulang, reversal penuh, batas sen"
- **Fixture**: nota 3 baris (12pcs@3.250=39.000; 7pcs@1.500=10.500; 29pcs@800=23.200; total=72.700).
- **Hasil per leg (BASELINE)**: sum(line)=dokumen=jurnal=subledger mandor, exact sampai sen; reversal penuh = negatif exact semua baris/jurnal/subledger, net-zero. **(CR-TUNDA)** retur sebagian berulang (3pcs lalu 2pcs lagi dari baris sama): kredit kumulatif tidak boleh melebihi qty/nominal baris asal.
- **Dilarang**: baseline — selisih sen antar leg. CR — kredit kumulatif melebihi qty asal; retur diam-diam diterima tanpa mekanisme credit/carry/refund yang sah.
- **Kebijakan**: ACC-DEC05 (credit/carry/refund) belum diputus → default aman: retur sebagian setelah posting ditolak/pending sampai mekanisme dibangun; reversal penuh tetap baseline.
- **Status**: BASELINE=ORACLE_READY; bagian retur-sebagian=NEEDS_OWNER_INPUT (PENDING_POLICY_VALUE ACC-DEC05)

## B. Aksesori — kelompok B (pos servis dan pemakaian)

#### ACC-B01 — transfer ke "pos"
- **M**: 5267 — "Transfer 120 dari stok 1.000"
- **Fixture**: stok gudang=1.000; transfer 120 unit ke lokasi tujuan (pos servis).
- **Hasil per leg (BASELINE, `post_material_transfer_v2`)**: gudang=880, pos=120, total=1.000; tidak ada kasbon/reimburse/biaya baru dari transfer itu sendiri.
- **Dilarang**: transfer membuat payable/kasbon/pendapatan; total lintas lokasi ≠1.000.
- **Kebijakan**: tipe lokasi "pos servis" khusus + UI-nya adalah ACC-04b (ABSENT, tidak ada facade/UI, hanya transfer generik backend).
- **Status**: hukum konservasi qty/nilai=ORACLE_READY (bisa diuji lewat backend sekarang); UI/tipe-lokasi pos=NEEDS_OWNER_INPUT

#### ACC-B02 — pemakaian lalu kembali
- **M**: 5268 — "Pemakaian 95 lalu kembali 25"
- **Fixture**: stok=1.000; adjustment pemakaian internal 95 (stok→905); lalu 25 dikembalikan (stok→930).
- **Hasil per leg (BASELINE, `post_material_adjustment_v2`)**: pemakaian tercatat persis 95; pengembalian 25 adalah adjustment penambah stok, bukan pembelian (tidak ada AP) dan bukan income (tidak ada jurnal pendapatan).
- **Dilarang**: 25 unit diposting sebagai purchase/other income; pemakaian tercatat selain 95.
- **Kebijakan**: alur "pengembalian" formal dengan UI/facade adalah ACC-04b (ABSENT).
- **Status**: invariant adjustment=ORACLE_READY; UI end-to-end=NEEDS_OWNER_INPUT

#### ACC-B03 — pemakaian langsung tanpa pos
- **M**: 5269 — "Pemakaian langsung 3 tanpa pos"
- **Fixture**: adjustment MAINTENANCE 3 unit langsung dari satu lokasi, tanpa transfer-ke-pos.
- **Hasil per leg**: stok lokasi itu −3 persis; biaya purpose diakui sekali; tidak ada entitlement/kasbon dibuat.
- **Dilarang**: lokasi salah berkurang; biaya diakui dua kali; entitlement tercipta.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-B04 — transfer backdate + invoice susulan
- **M**: 5270 — "Transfer backdate + invoice biaya susulan"
- **Fixture**: transfer dibackdate (tapi sesudah unit tiba di lokasi asal); koreksi biaya/invoice susulan datang kemudian.
- **Hasil per leg**: qty/nilai bersih/average tidak berubah semu akibat backdate saja; backdate yang membuat histori lokasi negatif ditolak (`AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`); koreksi susulan bertanggal max(tanggal ekonomi, tanggal perpindahan) selama periode terbuka (D01).
- **Dilarang**: backdate membuat saldo historis lokasi negatif; average cost berubah tanpa dasar koreksi nyata.
- **Kebijakan**: tidak ada (D01 sudah diputus tertulis).
- **Status**: ORACLE_READY

#### ACC-B05 — lokasi tidak sah
- **M**: 5271 — "Lokasi inactive/tidak berizin/sama atau tipe tidak didukung"
- **Fixture**: transfer ke lokasi inactive; operator tanpa izin lokasi; source=destination; tipe lokasi tak didukung.
- **Hasil per leg**: setiap kasus ditolak jelas dan atomik.
- **Dilarang**: kondisi manapun diperlakukan sebagai grant/bypass diam-diam; source=destination "sukses" sebagai no-op yang tetap mencatat gerakan palsu.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-B06 — rekap dan selisih opname
- **M**: 5272 — "Rekap beberapa hari dan selisih opname"
- **Fixture**: rekap 5 hari pemakaian; opname fisik menunjukkan selisih 5 unit tak terjelaskan (sistem 900, fisik 895).
- **Hasil per leg**: tiap hari mempertahankan tanggal aslinya (tidak dikumpulkan ke tanggal opname); selisih 5 dicatat UNKNOWN/variance, bukan dilabeli penggunaan pasti.
- **Dilarang**: backdate/relabel pemakaian harian ke tanggal rekap; selisih diklasifikasikan sebagai penggunaan tertentu tanpa bukti.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-B07 — rantai integrasi penuh
- **M**: 5273 — "Pembelian/penerimaan sah → transfer/pemakaian/nota → retur/settlement → laporan"
- **Fixture**: beli/terima 1.000 unit @cost C; transfer 120 ke pos; nota ke mandor 95 unit @harga eceran manual; (CR) retur sebagian unit yang sudah dinota.
- **Hasil per leg (BASELINE)**: di setiap tahap qty/nilai reconcile persis (nilai masuk pembelian = nilai keluar transfer/nota, tidak ada nilai tercipta/hilang); jurnal tiap tahap konsisten (AP saat beli, tanpa income/expense palsu saat transfer, potongan payroll saat nota).
- **Dilarang**: tahap manapun menciptakan stok/nilai fantom; rantai berhenti reconcile karena tahap retur belum ada.
- **Kebijakan**: tahap retur/settlement adalah ACC-04b (ABSENT).
- **Status**: rantai BASELINE=ORACLE_READY; end-to-end penuh termasuk retur=NEEDS_OWNER_INPUT

## C. Aksesori — kelompok C (pengembalian dan ganti merek)

#### ACC-C01 — inspeksi penerimaan
- **M**: 5279 — "Terima 100, inspeksi 80 layak + 20 rusak"
- **Fixture**: 100 unit retur fisik dari mandor; inspeksi mengklasifikasi 80 layak, 20 rusak.
- **Hasil per leg**: penerimaan mencatat qty fisik=100 sekali saja (inspeksi bukan event penambah stok kedua); hanya 80 layak yang bisa diissue ulang; 20 rusak dilacak terpisah (scrap/write-off), tidak issuable.
- **Dilarang**: event inspeksi menambah stok tercatat di atas 100; 20 unit rusak tetap issuable.
- **Kebijakan**: workflow inspeksi penerimaan sama sekali ABSENT (A4). Default aman: sebelum klasifikasi tercatat, tidak ada dari 100 unit yang issuable (fail-closed).
- **Status**: NEEDS_OWNER_INPUT (hukum konservasi di atas tetap oracle tetap begitu dibangun)

#### ACC-C02 — inspeksi parsial dua pemeriksa
- **M**: 5280 — "Inspeksi parsial dan dua pemeriksa"
- **Fixture**: 100 diterima; pemeriksa 1 klasifikasi 60 (50 layak+10 rusak); pemeriksa 2 klasifikasi 30 lagi (25 layak+5 rusak); 10 belum diklasifikasi.
- **Hasil per leg**: total klasifikasi ≤100 kapan pun; sisa 10 tetap terlihat; unit yang sudah diklasifikasi satu pemeriksa tidak bisa diklasifikasi ulang pemeriksa lain.
- **Dilarang**: total klasifikasi >100; unit sama diterima dua kali oleh dua pemeriksa.
- **Kebijakan**: ABSENT.
- **Status**: NEEDS_OWNER_INPUT (hukum konservasi tetap fixed)

#### ACC-C03 — source retur dipakai ulang
- **M**: 5281 — "Source return yang sama dipakai lagi lewat request baru"
- **Fixture**: satu source retur (20pcs) sudah full recovered; dicoba lagi dengan request UUID baru (bukan retry).
- **Hasil per leg**: ditolak karena kapasitas recovery source sudah habis (business-level uniqueness), terlepas dari UUID baru — idempotency saja secara eksplisit dinyatakan tidak cukup (M:5281).
- **Dilarang**: diterima hanya karena UUID berbeda dari percobaan pertama.
- **Kebijakan**: objek "source retur" itu sendiri ABSENT.
- **Status**: NEEDS_OWNER_INPUT (prinsip capacity>idempotency tetap ORACLE_READY begitu dibangun)

#### ACC-C04 — tiga sumber berbeda efek finansial
- **M**: 5282 — "Sisa baru vs retur nota berbayar vs bongkaran"
- **Fixture**: (a) sisa baru belum pernah diissue; (b) retur nota mandor yang sudah dibayar (butuh credit/reversal ke nota itu); (c) bongkaran/teardown recovery.
- **Hasil per leg**: masing-masing sumber mempertahankan perlakuan finansial berbeda — sisa baru tidak dibukukan sebagai credit mandor; credit mandor tidak dibukukan sebagai sisa gratis; bongkaran tidak dinilai sama seperti stok baru tanpa keputusan nilai.
- **Dilarang**: tiga sumber tertukar/dicampur dalam satu pembukuan.
- **Kebijakan**: sumber (b) dan (c) sebagian ABSENT/KEBIJAKAN (ACC-DEC03/05).
- **Status**: NEEDS_OWNER_INPUT (prinsip "jangan tertukar" tetap ORACLE_READY)

#### ACC-C05 — nilai bekas belum sah
- **M**: 5283 — "Nilai bekas belum sah"
- **Fixture**: 15 unit hasil salvage/teardown, nilai belum diputus owner.
- **Hasil per leg**: qty dan custody tercatat jelas segera; nilai eksplisit PENDING (bukan 0, bukan harga baru default); 15 unit itu tidak boleh dijual/diissue sebagai stok ready.
- **Dilarang**: nilai default Rp0 atau dibukukan OTHER_INCOME otomatis; unit muncul di stok ready.
- **Kebijakan**: ACC-DEC03 belum diputus → default aman: pending value, blokir jual/issue (M:4456).
- **Status**: PENDING_POLICY_VALUE / NEEDS_OWNER_INPUT (invariant qty/custody/no-fake-zero ORACLE_READY sekarang)

#### ACC-C06 — ganti merek + bongkaran
- **M**: 5284 — "Ganti merek 100, aksesori baru 100, bongkaran 80+20"
- **Fixture**: konversi 100 unit FG dari SKU sumber ke SKU target, konsumsi 100 aksesori baru; bongkaran merek lama: 80 layak + 20 rusak.
- **Hasil per leg**: FG sumber −100 / target +100 (exact swap, tidak ada FG tercipta neto); aksesori baru terkonsumsi persis 100, biaya diakui sekali; 80 aksesori lama layak dicatat (nilai pending ACC-DEC03, tidak issuable/sellable), 20 rusak dicatat terpisah; tidak ada reimbursement BOM kedua ke mandor.
- **Dilarang**: FG dihitung ganda (sumber tidak turun atau target tidak naik); biaya BOM aksesori dua kali; aksesori lama dinilai/dijual tanpa keputusan.
- **Kebijakan**: ACC-DEC03 (nilai bekas) belum diputus; fitur ABSENT.
- **Status**: NEEDS_OWNER_INPUT / PENDING_POLICY_VALUE (hukum konservasi FG −100/+100 dan single-cost tetap ORACLE_READY)

#### ACC-C07 — double charge label
- **M**: 5285 — "Biaya label manual + baris aksesori otomatis yang sama"
- **Fixture**: baris manual "ganti label" + baris otomatis konsumsi BOM label yang sama pada unit sama.
- **Hasil per leg**: sistem mendeteksi/memblokir double charge untuk aksesori+unit fisik yang sama; jasa yang benar-benar berbeda (aksesori lain atau jasa tenaga kerja) tetap bisa tercatat terpisah.
- **Dilarang**: kedua baris (manual + otomatis) dibiayakan untuk penggantian fisik yang sama.
- **Kebijakan**: mekanisme dedup/lineage ABSENT.
- **Status**: NEEDS_OWNER_INPUT (prinsip no-double-charge tetap ORACLE_READY)

#### ACC-C08 — return baru setelah conversion
- **M**: 5286 — "Return baru tiba setelah conversion; ada sale/return/konversi turunan"
- **Fixture**: FG hasil konversi merek sudah terjual; koreksi biaya material aksesori datang setelah event retur baru dicatat.
- **Hasil per leg (BASELINE recost, `refresh_accessory_hpp_after_material_recost`)**: recost mengikuti rantai descendant (konversi→FG→jual), memperbarui HPP/COGS/GL konsisten, atau ditandai PENDING bila rantai tak dapat diselesaikan jujur; total GL = total koreksi sumber.
- **Dilarang**: recost salah sasaran/hilang; laporan mengklaim selesai padahal sebagian rantai belum terselesaikan.
- **Kebijakan**: trigger "return baru" adalah ACC-04b (ABSENT).
- **Status**: linkage recost=ORACLE_READY (bukti AZ T1); skenario trigger retur=NEEDS_OWNER_INPUT

#### ACC-C09 — retur setelah payroll
- **M**: 5287 — "Retur mandor sesudah payroll partial/lunas"
- **Fixture**: nota 100pcs Rp325.000, sudah dipotong payroll sebagian (60.000) atau lunas (325.000); mandor mencoba retur.
- **Hasil per leg (BASELINE)**: reversal penuh nota yang sudah masuk payroll ditolak tegas (existing block, 20ac:6151); histori settlement payroll tidak pernah diubah diam-diam.
- **Dilarang**: reversal nota yang sudah dipayroll diterima; histori payroll ditulis ulang.
- **Kebijakan**: mekanisme credit/carry/refund parsial setelah settlement (ACC-DEC05) belum diputus → default aman: retur fisik boleh dicatat tapi finalisasi finansial ditolak/pending; kredit tidak boleh melebihi qty/nominal sumber.
- **Status**: blok BASELINE=ORACLE_READY; credit/carry/refund=PENDING_POLICY_VALUE / NEEDS_OWNER_INPUT

#### ACC-C10 — servis garmen pelanggan
- **M**: 5288 — "Garment servis masih milik pelanggan"
- **Fixture**: garmen milik pelanggan (bukan FG perusahaan) diservis kecil (ganti kancing).
- **Hasil per leg**: tidak ada FG perusahaan tercipta, tidak ada AR/refund, tidak ada entitlement produksi (BOM mandor); biaya aksesori dicatat sebagai konsumsi servis biasa, terpisah dari alur produksi/FG/AR.
- **Dilarang**: FG/AR/refund/entitlement tercipta dari servis ini.
- **Kebijakan**: ACC-DEC04 (akun biaya servis vs kapitalisasi) belum diputus → default aman: catat sebagai cost servis polos, tolak kapitalisasi FG/AR.
- **Status**: PENDING_POLICY_VALUE / NEEDS_OWNER_INPUT (negative invariant "no FG/AR/entitlement" tetap ORACLE_READY)

#### ACC-C11 — dua pola kembali akhir tahun
- **M**: 5289 — "Fisik kembali dahulu, inspeksi akhir tahun; atau fisik baru kembali akhir tahun"
- **Fixture**: Pola A — fisik kembali November, inspeksi baru terjadi saat tutup buku akhir tahun. Pola B — fisik baru benar-benar kembali di akhir tahun.
- **Hasil per leg**: Pola A — tanggal fisik tetap November (tidak dibackdate/fabrikasi ke akhir tahun); availability baru terbuka setelah klasifikasi nyata terjadi. Pola B — tanggal fisik memang akhir tahun, didukung sebagai state nyata berbeda dari Pola A.
- **Dilarang**: tanggal fisik dikarang untuk unit yang masih di tangan mandor; sistem memaksa satu pola berlaku universal.
- **Kebijakan**: ACC-DEC01 belum diputus; fitur ABSENT → default aman: dukung dua keadaan berdasar input operator nyata, jangan menebak.
- **Status**: PENDING_POLICY_VALUE / NEEDS_OWNER_INPUT (aturan "dua pola nyata, tidak dikarang" ORACLE_READY)

#### ACC-C12 — opname baseline, sumber tidak lengkap
- **M**: 5290 — "Opname baseline historis, sumber tidak lengkap"
- **Fixture**: opname pembuka aksesori dengan sebagian dokumen sumber hilang (qty diketahui, harga/dokumen asal tidak).
- **Hasil per leg**: baseline dicatat sebagai entri opening/adjustment, bukan nota/PO palsu; stok ditetapkan sekali (tidak dobel dengan entri "susulan" untuk item sama); nilai yang tidak bersumber jelas ditandai pending, bukan final.
- **Dilarang**: sistem mengarang nota/PO untuk membenarkan qty opening; item sama dihitung dua kali (opname + penerimaan normal berikutnya).
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

## D. Aksesori — kelompok D (race, keamanan, fail-closed, UI)

#### ACC-D01 — dua sesi rebutan stok 7
- **M**: 5296 — "Dua sesi issue/pemakaian pada stok 7, masing-masing ambil 4"
- **Fixture**: stok=7; dua sesi konkuren, masing-masing minta 4.
- **Hasil per leg**: tepat satu sukses (stok→3), yang lain ditolak atomik; saldo akhir tidak pernah negatif.
- **Dilarang**: kedua sesi sukses (stok→-1); request kedua diam-diam disesuaikan jadi 3.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D02 — transfer vs issue lokasi sama
- **M**: 5297 — "Transfer vs issue/pemakaian lokasi sama"
- **Fixture**: transfer-out dan adjustment pemakaian menyasar lokasi/unit sama secara konkuren.
- **Hasil per leg**: lock bersama efektif, hanya satu operasi berjalan pada saat sama atas unit sama; barang tidak dikeluarkan dua kali.
- **Dilarang**: kedua operasi sukses independen, over-draw lokasi.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D03 — posting vs edit draft
- **M**: 5298 — "Posting vs edit DRAFT, harga/UOM berubah ketika menunggu lock"
- **Fixture**: POST antre di lock; draft yang sama diedit (harga/UOM) konkuren; atau nota sudah POSTED dicoba diedit.
- **Hasil per leg**: POST menilai state DRAFT terbaru saat commit (revalidasi atau ditolak stale, tidak pernah posting dengan snapshot lama); dokumen POSTED tidak pernah bisa diedit in-place.
- **Dilarang**: POST commit dengan harga/UOM pra-edit yang sudah stale; qty/harga/UOM POSTED berubah lewat jalur "edit".
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D04 — retur/inspeksi vs payroll/reversal
- **M**: 5299 — "Return/inspection vs return lain, payroll, reversal source"
- **Fixture (BASELINE)**: reversal nota dicoba konkuren dengan nota itu masuk payroll. **(CR)** dua event retur/inspeksi konkuren atas source nota/receipt sama.
- **Hasil per leg (BASELINE)**: hanya satu sisi menang (reversal atau payroll capture), tidak ada orphan jurnal/payroll yang menunjuk source yang sudah dibalik.
- **Dilarang**: reversal dan potongan payroll sama-sama berlaku atas nota sama; baris orphan dengan referensi menggantung.
- **Kebijakan**: retur/inspeksi konkuren adalah ACC-04b (ABSENT); begitu dibangun, total kredit/klasifikasi tidak boleh melebihi kapasitas sumber (over-credit ditolak).
- **Status**: BASELINE=ORACLE_READY; retur/inspeksi konkuren=NEEDS_OWNER_INPUT

#### ACC-D05 — replay/mismatch/refetch
- **M**: 5300 — "Request sama ulang, key sama payload beda, timeout setelah commit"
- **Fixture**: (a) UUID+payload sama diulang; (b) UUID sama payload beda; (c) commit sukses server tapi client timeout lalu refetch.
- **Hasil per leg**: (a) replay tepat ke hasil commit asal. (b) ditolak (mismatch), bukan diterima sebagai edit. (c) refetch rekonsiliasi ke transaksi yang sudah commit, bukan posting UUID baru.
- **Dilarang**: (b) payload baru menimpa diam-diam; (c) dua dokumen posted untuk satu niat transaksi.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D06 — role tidak sah
- **M**: 5301 — "Null/inactive role, revocation, lintas lokasi/source, direct table/API"
- **Fixture**: role=null, role inactive, role baru dicabut, role sah untuk lokasi lain, panggilan langsung ke tabel/API melewati facade — masing-masing terhadap SAVE_DRAFT/POST/REVERSE/edit harga.
- **Hasil per leg**: setiap kasus ditolak nyata di lapisan Auth/HTTP/RPC (server-enforced), bukan hanya UI disembunyikan; kontrol diuji dengan role sungguhan, bukan satu fixture OWNER yang lolos semua.
- **Dilarang**: panggilan tabel/API langsung sukses padahal facade akan menolak (RLS/grant tidak cocok); tes "membuktikan" otorisasi hanya lewat fixture OWNER.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D07 — gagal di tengah multi-line
- **M**: 5302 — "Kesalahan sengaja di tengah command multi-line"
- **Fixture**: POST nota 3 baris, baris 2 sengaja dibuat gagal (format harga invalid).
- **Hasil per leg**: seluruh command rollback — tidak ada stok baris 1 berkurang, tidak ada jurnal/potongan payroll parsial; state persis seperti sebelum percobaan.
- **Dilarang**: baris 1 committed sementara baris 2/3 ditolak, nota setengah-posted.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D08 — tanggal WIB lintas UTC dan closed period
- **M**: 5303 — "Tanggal WIB lintas UTC, backdate dan closed period"
- **Fixture**: post nota dekat batas hari WIB/UTC (23:30 WIB = beda tanggal UTC); nota backdate; nota bertanggal periode tertutup.
- **Hasil per leg**: `physical_at`, `system_created_at`, tanggal buku tetap tiga fakta berbeda memakai waktu bisnis WIB; backdate tidak merusak prefix qty/value; periode tertutup memakai controlled adjustment (D01 §4), bukan backdate bebas; laporan as-of sebelum koreksi diakui tidak mengklaim READY palsu.
- **Dilarang**: jam device/UTC dipakai langsung sebagai tanggal bisnis WIB (salah hari); posting langsung ke periode tertutup tanpa jalur controlled adjustment.
- **Kebijakan**: tidak ada (D01 sudah diputus tertulis).
- **Status**: ORACLE_READY

#### ACC-D09 — UI desktop/HP, 7 PCS tanggung
- **M**: 5304 — "Desktop/HP, reload, double click, empty/error/loading, 7 PCS tanggung"
- **Fixture**: `ConnectedAccessoryIssuePage` di lebar desktop dan mobile; reload di tengah alur; double-click tombol POST; simulasi list kosong/RPC error/loading; input 7 PCS ganjil.
- **Hasil per leg**: semua state memakai saldo/RPC server nyata (tidak ada seed/local fallback); double-click tidak menghasilkan dua nota (debounce klien + idempotency server); 7 PCS tampil dan posting benar di kedua ukuran layar; state error/empty/loading berbeda tampilannya dari data sukses.
- **Dilarang**: double-click menghasilkan nota ganda; UI fallback ke data seed/lokal saat RPC error dan menampilkannya seolah nyata.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D10 — refetch gagal setelah commit
- **M**: 5305 — "Refetch gagal sesudah commit"
- **Fixture**: POST sukses server; refetch konfirmasi klien gagal (network error).
- **Hasil per leg**: pesan UI menyatakan "tersimpan, gagal konfirmasi — retry aman", bukan "transaksi gagal"; lock/draft state dilepas/ditandai sehingga retry aman (UUID sama) dan rekonsiliasi tanpa duplikasi.
- **Dilarang**: UI mengklaim gagal padahal sudah sukses; retry menghasilkan dokumen posted kedua.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D11 — upgrade/rollback exact restore
- **M**: 5306 — "Upgrade/replay refusal, rollback sebelum/sesudah use, exact restore"
- **Fixture**: terapkan paket migrasi aksesori sebelum dan sesudah dipakai transaksi nyata; rollback di kedua skenario.
- **Hasil per leg**: definisi fungsi/tabel, owner objek, ACL/grant, trigger, data, marker install/rollback, dan ketiadaan orphan terverifikasi exact kembali ke sebelum upgrade (setara bar "127/127"); guard (mis. stok negatif, kapasitas) tidak melonggar akibat siklus upgrade+rollback.
- **Dilarang**: rollback meninggalkan tabel/fungsi/grant orphan; guard jadi permisif setelah siklus upgrade+rollback.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### ACC-D12 — performa list besar
- **M**: 5307 — "Performa query/history dan daftar besar"
- **Fixture**: katalog/histori nota ≥5.000 baris; search/filter dan paging.
- **Hasil per leg**: search dan pagination dieksekusi server-side (limit/offset/filter ke RPC); saldo berjalan dihitung server-side, bukan dijumlah dari seluruh histori yang di-fetch ke browser.
- **Dilarang**: klien fetch seluruh tabel histori untuk difilter lokal; saldo dihitung dari halaman klien yang tidak lengkap.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

---

## E. Laundry T01–T15

#### LAU-T01 — dua vendor, komponen nama sama harga beda
- **M**: 4339 — "Vendor A/B mempunyai komponen bernama sama tetapi harga berbeda"
- **Fixture**: Vendor A proses "Garment" = Rp5.000/pcs; Vendor B proses "Garment" = Rp8.000/pcs (nama sama). Kirim 100pcs ke Vendor A.
- **Hasil per leg**: resolver hanya memakai tarif Vendor A (500.000 total); tarif Vendor B tidak pernah bocor ke perhitungan/tampilan transaksi Vendor A.
- **Dilarang**: harga tercampur (misal rata-rata A+B); UI menampilkan tarif vendor lain saat memilih Vendor A.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T02 — paket fixed sudah termasuk komponen
- **M**: 4340 — "Paket fixed Rp12.000 sudah memuat beberapa komponen"
- **Fixture**: Paket A tetap Rp12.000/pcs mencakup Garment+Spray+Whisker; kirim 100pcs pakai paket.
- **Hasil per leg**: total = 100×12.000 = 1.200.000, satu baris tagihan; komponen included (Garment/Spray/Whisker) tidak muncul sebagai baris tambahan (LAU-R04).
- **Dilarang**: komponen included ditagih lagi terpisah di atas 1.200.000.
- **Kebijakan**: fitur paket (LAU-05b) ABSENT; desain sudah disetujui M:3730.
- **Status**: ORACLE_READY (spesifikasi jelas dari LAU-R04 meski fitur belum dibangun)

#### LAU-T03 — susun komponen, qty fisik tidak triple
- **M**: 4341 — "Garment 5000 + Spray 1000 + Whisker 1000, 100 PCS"
- **Fixture**: mode Susun Komponen, 3 komponen dipilih untuk 100pcs sama.
- **Hasil per leg**: tarif/pcs=7.000, total=700.000; qty fisik tercatat 100 (bukan 3×100=300 akibat 3 baris komponen).
- **Dilarang**: qty fisik tergandakan sejumlah komponen yang dipilih.
- **Kebijakan**: fitur komponen ABSENT.
- **Status**: ORACLE_READY

#### LAU-T04 — empat komponen owner, tidak hardcode
- **M**: 4342 — "Semua empat contoh owner dipilih, 100 PCS"
- **Fixture**: Garment5000+Spray1000+Whisker1000+Wipping5000=12.000/pcs×100=1.200.000; lalu tambah komponen ke-5 di master dan uji ulang.
- **Hasil per leg**: total=1.200.000 untuk 4 komponen; saat komponen ke-5 ditambahkan ke master dan dipilih, total berubah sesuai — membuktikan daftar komponen data-driven (LAU-R03), bukan enum 4 nama hardcode.
- **Dilarang**: kode memakai daftar tetap 4 nama komponen; komponen baru di master tidak terpengaruh perhitungan.
- **Kebijakan**: fitur ABSENT.
- **Status**: ORACLE_READY

#### LAU-T05 — coverage sebagian per komponen
- **M**: 4343 — "Garment 100 PCS dan Spray 40 PCS"
- **Fixture**: Garment 100×5.000=500.000 + Spray 40×1.000=40.000.
- **Hasil per leg**: total=540.000; coverage Spray tidak melebihi 40pcs yang benar dikerjakan.
- **Dilarang**: Spray ditagih untuk seluruh 100pcs (600.000, salah); coverage otomatis menyamakan seluruh kiriman.
- **Kebijakan**: fitur ABSENT (LAU-R06).
- **Status**: ORACLE_READY

#### LAU-T06 — included dan extra sama dipilih ulang
- **M**: 4344 — "Paket included dan extra yang sama dipilih ulang"
- **Fixture**: paket mencakup Spray; operator juga memilih Spray sebagai komponen extra untuk kiriman/qty sama.
- **Hasil per leg**: sistem menolak duplikasi biaya untuk coverage sama, ATAU extra disahkan sebagai pekerjaan berbeda dengan lineage eksplisit (alasan/coverage berbeda) — dua-duanya sah selama tidak dobel diam-diam.
- **Dilarang**: Spray extra ditambahkan di atas total paket tanpa lineage, dobel biaya untuk coverage fisik sama.
- **Kebijakan**: fitur ABSENT.
- **Status**: ORACLE_READY

#### LAU-T07 — favorit lalu tarif master berubah
- **M**: 4345 — "Favorit/recipe tersimpan lalu tarif master berubah"
- **Fixture**: favorit Garment+Spray disimpan saat versi tarif V1 (7.000/100pcs=700.000, sudah posted). Master naik ke V2 (mis. Garment 6.000).
- **Hasil per leg**: transaksi baru memakai favorit di V2 memakai tarif V2 baru; transaksi T1 yang sudah posted tetap persis 700.000 (LAU-R24: master baru tidak mass-reprice histori).
- **Dilarang**: dokumen T1 posted dihitung ulang otomatis ke V2; favorit menyimpan harga beku alih-alih rujukan ke master (LAU-R07).
- **Kebijakan**: fitur favorit ABSENT; bagian "posted lama exact" BASELINE.
- **Status**: ORACLE_READY

#### LAU-T08 — rate tidak valid
- **M**: 4346 — "Rate negatif/NaN/Infinity/format ambigu/overflow"
- **Fixture**: -1000, NaN, Infinity, "12,34.56", 1e309.
- **Hasil per leg**: setiap input ditolak atomik (CHECK ≥0, FX:3351); tidak ada partial commit baris lain.
- **Dilarang**: nilai dikoreksi jadi 0 atau positif; komando lain di batch tetap committed sebagian.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T09 — rate UNKNOWN sungguhan
- **M**: 4347 — "Rate benar-benar UNKNOWN, proses/vendor/source valid"
- **Fixture**: kiriman/vendor/proses sah, tidak ada versi tarif aktif, belum ada owner_estimate.
- **Hasil per leg**: fisik (qty, tanggal, custody) tercatat normal; status harga=UNKNOWN (bukan 0); HPP/laporan ditandai incomplete; preflight tutup buku memblokir (`LAUNDRY_PRICE_UNKNOWN`) sampai `erp_set_laundry_rate_owner_estimate_v1` mengisi ESTIMATED.
- **Dilarang**: cost Rp0 diposting diam-diam; laporan mengklaim final/READY saat unknown.
- **Kebijakan**: LAU-DEC01/04 (izin final sales/close) belum diputus → default aman: tolak finalisasi, izinkan fisik pending.
- **Status**: ORACLE_READY untuk perilaku blokir; NEEDS_OWNER_INPUT/PENDING_POLICY_VALUE untuk izin finansial final

#### LAU-T10 — ESTIMATED/AGREED tanpa invoice
- **M**: 4348 — "ESTIMATED/AGREED tetapi invoice belum ada"
- **Fixture**: kiriman 100pcs, estimasi diposting 700.000 (7.000×100), status akrual ACCRUED_MANUFACTURING/AP_VENDOR provisional; belum ada invoice vendor.
- **Hasil per leg**: status harga (ESTIMATED/AGREED) dan status invoice (NOT_INVOICED) adalah field berbeda; akrual dibukukan sekali 700.000, tidak digandakan saat invoice datang kemudian (rekonsiliasi, bukan akrual kedua).
- **Dilarang**: kedatangan invoice membuat akrual kedua di samping estimasi pertama tanpa reversal/rekonsiliasi.
- **Kebijakan**: alokasi invoice n:m (LAU-DEC06) ABSENT.
- **Status**: ORACLE_READY untuk non-duplikasi akrual; NEEDS_OWNER_INPUT untuk mekanisme alokasi invoice penuh

#### LAU-T11 — FREE vs rate missing
- **M**: 4349 — "FREE configured dengan alasan dibanding rate missing"
- **Fixture**: Kasus A — cuci ulang (rework ke LAUNDRY) tanpa tagihan vendor by design (0 dengan alasan desain, jurnal hanya untuk CONTRACTOR, 20av:739). Kasus B — tarif sekadar belum dikonfigurasi (missing).
- **Hasil per leg**: dua state ini harus terbedakan secara eksplisit (bukan sama-sama tampil "0"/kosong); FREE butuh jejak alasan/otorisasi; missing rate memblokir tutup buku (LAU-04).
- **Dilarang**: rate missing diam-diam diperlakukan sebagai gratis/0; FREE tidak melalui kontrol approval.
- **Kebijakan**: enum FREE/WAIVED formal adalah usulan semantik LAU-R09, belum ada di enum existing → default aman: selain jalur rework-vendor-gratis yang sudah didesain, perlakukan sebagai UNKNOWN/diblokir.
- **Status**: NEEDS_OWNER_INPUT/PENDING_POLICY_VALUE untuk enum FREE formal; distingsi dasar rework-vs-missing ORACLE_READY

#### LAU-T12 — satu komponen null
- **M**: 4350 — "Salah satu komponen null, sisanya berharga"
- **Fixture**: 3 komponen, 2 diketahui (5.000+1.000=6.000/pcs×100=600.000), 1 null.
- **Hasil per leg**: subtotal diketahui=600.000 tampil; `total_complete=false`; laporan yang bergantung kiriman ini ditandai pending (LAU-R12, LAU-R23).
- **Dilarang**: subtotal diketahui disajikan sebagai total final; komponen null didefault 0 lalu dilipat ke total "complete".
- **Kebijakan**: mode komponen ABSENT, tapi aturan completeness (LAU-R23) eksplisit di kontrak.
- **Status**: ORACLE_READY

#### LAU-T13 — error tarif ≠ unknown
- **M**: 4351 — "Query tarif timeout/malformed/overlap"
- **Fixture**: simulasi timeout lookup tarif, baris tarif malformed, dua versi tarif overlap untuk vendor+proses+periode sama.
- **Hasil per leg**: tiap kondisi muncul sebagai ERROR sistem berbeda, bukan disimpan/ditampilkan sebagai state bisnis UNKNOWN yang sah; overlap ditolak oleh guard tulis (unique, FX:9681), bukan ditoleransi saat baca.
- **Dilarang**: error ditelan lalu dilabeli UNKNOWN seolah keputusan bisnis; overlap dipilih salah satu secara sembarang.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T14 — reprice akibat tanggal kembali berubah (defect lama, harus diperbaiki)
- **M**: 4352 — "Harga kirim/agreement versi 1; master naik sebelum penerimaan"
- **Fixture**: kirim di T1 saat tarif v1=7/pcs; sebelum fisik diterima di T2, master naik ke v2=9/pcs.
- **Hasil per leg**: biaya aktual saat terima tetap dihitung pada v1=7 (tarif saat KIRIM), bukan v2=9 (bukti probe `LAU_T14:RECEIPT_AFTER_A_LATER_RATE_VERSION`: tanpa perbaikan=9 salah, dengan perbaikan=7 benar).
- **Dilarang**: penerimaan reprice memakai tarif yang berubah setelah kirim.
- **Kebijakan**: tidak ada — ini defect lama BASELINE (M:1697), wajib diperbaiki di CP6, bukan CR yang bisa ditunda.
- **Status**: ORACLE_READY (kanonik — harus diverifikasi benar-benar terperbaiki, bukan sekadar didesain)

#### LAU-T15 — proses aktual ≠ diminta
- **M**: 4353 — "Proses aktual berbeda dari yang diminta"
- **Fixture**: diminta "Cuci Kering" (5.000/pcs) tapi vendor benar-benar melakukan "Cuci Basah" (6.000/pcs), 100pcs.
- **Hasil per leg**: instruksi original ("Cuci Kering") tetap utuh tersimpan; penyesuaian actual/source tertaut sebagai record terpisah dengan tarifnya sendiri (600.000); UI/laporan menampilkan requested vs actual untuk direview, bukan ditimpa.
- **Dilarang**: field instruksi original ditimpa oleh proses aktual, menghilangkan jejak selisih.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

---

## F. Laundry T16–T30

#### LAU-T16 — invoice di atas estimate
- **M**: 4354 — "Invoice 750000 atas estimate 700000 untuk scope 100 PCS"
- **Fixture**: estimasi 100×7.000=700.000 accrued; invoice vendor datang 750.000 untuk scope sama.
- **Hasil per leg**: final cost=750.000; delta=+50.000 diposting ke akrual/AP dan turunan HPP/COGS sesuai lokasi unit (WIP/FG/COGS) dan tanggal per aturan D01 (max(tanggal ekonomi invoice, tanggal fisik) selama periode terbuka); qty fisik 100 tidak berubah.
- **Dilarang**: 700.000 dan 750.000 dua-duanya dibukukan penuh (double count 1.450.000); qty fisik ikut berubah karena koreksi harga.
- **Kebijakan**: LAU-DEC06 (akun variance) belum diputus → default aman: delta diposting ke baris variance/adjustment berlabel jelas, tidak dilipat diam-diam ke akun tak terkait.
- **Status**: NEEDS_OWNER_INPUT/PENDING_POLICY_VALUE untuk akun; hukum rekonsiliasi (700k+50k=750k, fisik tetap) ORACLE_READY

#### LAU-T17 — invoice bertahap
- **M**: 4355 — "Invoice awal 40 PCS, sisa 60 PCS menyusul"
- **Fixture**: kiriman 100pcs; invoice1 cover 40pcs (280.000); invoice2 kemudian cover sisa 60pcs (420.000).
- **Hasil per leg**: total coverage kedua invoice = persis 100pcs/700.000; akrual dialokasikan proporsional per invoice, tidak diakru ulang untuk pcs yang sama; sisa qty belum-invoiced terlihat (100→60→0).
- **Dilarang**: invoice2 menagih 60pcs yang akrualnya sudah dilunasi invoice1; total invoice melebihi 100pcs terkirim.
- **Kebijakan**: fitur alokasi invoice (LAU-05b/DEC06) ABSENT.
- **Status**: ORACLE_READY untuk hukum konservasi; NEEDS_OWNER_INPUT untuk detail workflow

#### LAU-T18 — n:m invoice-kiriman
- **M**: 4356 — "Satu invoice beberapa kiriman; satu kiriman beberapa invoice"
- **Fixture**: Invoice X alokasi ke Kiriman A (30pcs) + Kiriman B (70pcs); Kiriman C dipecah ke Invoice Y (50pcs) + Invoice Z (50pcs).
- **Hasil per leg**: tiap baris alokasi tertaut exact ke kiriman+qty+nominal; sisa belum teralokasi selalu terlihat per sumber; sum(alokasi per sumber) = total dokumen invoice = total AP/GL, untuk setiap sisi (n dan m).
- **Dilarang**: total alokasi melebihi total invoice atau qty sumber; sisa belum teralokasi disembunyikan/dinolkan diam-diam.
- **Kebijakan**: fitur alokasi n:m ABSENT (LAU-05b).
- **Status**: ORACLE_READY untuk hukum konservasi; NEEDS_OWNER_INPUT untuk bentuk UI/workflow

#### LAU-T19 — source sama, request ID baru
- **M**: 4357 — "Source component/attempt sama ditagih dengan request ID baru"
- **Fixture**: baris kiriman/receipt sudah full-invoiced/allocated; percobaan tagih kedua dengan UUID baru (bukan retry).
- **Hasil per leg**: ditolak karena kapasitas source (bukan UUID) sudah habis — guard bisnis-level, bukan hanya idempotency replay (M:4357 eksplisit).
- **Dilarang**: diterima hanya karena UUID berbeda dari percobaan pertama.
- **Kebijakan**: sisi penagihan (invoicing) ABSENT; sisi kapasitas kirim/terima BASELINE dan bisa diuji sekarang.
- **Status**: ORACLE_READY untuk prinsip kapasitas sisi receipt; NEEDS_OWNER_INPUT untuk penegakan penuh di invoice

#### LAU-T20 — borongan, diterima bertahap
- **M**: 4358 — "Borongan 100000 pada 100 PCS diterima 40+60"
- **Fixture**: kesepakatan lump-sum Rp100.000 untuk batch 100pcs; diterima 40pcs lalu 60pcs.
- **Hasil per leg**: total biaya di kedua penerimaan = persis 100.000 (bukan 100.000 per penerimaan = 200.000); alokasi parsial (mis. 40.000 di penerimaan pertama, 60.000 di kedua) dan residual harus exact menjumlah 100.000.
- **Dilarang**: lump sum ditagih ulang di penerimaan kedua (jadi 200.000).
- **Kebijakan**: LAU-DEC01 (satuan borongan/batch) belum diputus, fitur ABSENT → default aman: tolak aktivasi tarif batch sampai satuan dikonfigurasi; hukum konservasi (total tetap 100.000) berlaku begitu dibangun.
- **Status**: PENDING_POLICY_VALUE/NEEDS_OWNER_INPUT (hukum konservasi tetap ORACLE_READY dan wajib)

#### LAU-T21 — diskon/rounding multi-line
- **M**: 4359 — "Diskon invoice/global rounding/multi-line"
- **Fixture**: invoice 3 baris total 1.000.000, diskon global 10% (100.000) dialokasikan pro-rata per baris, lalu dibulatkan ke rupiah.
- **Hasil per leg**: sum(baris setelah diskon+rounding) = total invoice = payable AP = total jurnal GL, exact ke rupiah; sisa pembulatan dialokasikan deterministik (mis. ke baris terakhir), tidak diserap diam-diam.
- **Dilarang**: sum baris berbeda dari total invoice walau Rp1 tanpa aturan sisa rounding eksplisit; sen/rupiah tercipta atau hilang.
- **Kebijakan**: LAU-DEC03 (diskon/pajak/rounding) belum diputus, fitur ABSENT → default aman: tolak fitur diskon/rounding sampai aturan ditetapkan; hukum konservasi tetap wajib begitu dibangun.
- **Status**: PENDING_POLICY_VALUE/NEEDS_OWNER_INPUT

#### LAU-T22 — delta cost lintas WIP/FG/terjual
- **M**: 4360 — "Sebagian WIP, sebagian FG, sebagian terjual sebelum invoice final"
- **Fixture**: batch 100pcs dicost pada ESTIMATED; saat invoice final, 30pcs masih WIP, 40pcs jadi FG belum terjual, 30pcs sudah terjual (COGS diakui); invoice final naikkan tarif +500/pcs.
- **Hasil per leg**: delta 500×30=15.000 tetap di valuasi WIP; 500×40=20.000 tetap di valuasi FG; 500×30=15.000 masuk COGS (bukan FG/WIP), bertanggal sesuai D01 (max(tanggal ekonomi invoice, tanggal perpindahan unit) selama periode terbuka); total delta=50.000 tanpa unit terlewat/dobel.
- **Dilarang**: seluruh 50.000 delta dilempar ke satu akun (mis. semua ke COGS) tanpa mengikuti lokasi fisik tiap unit.
- **Kebijakan**: invoice final (LAU-05b) ABSENT; hukum routing delta diturunkan langsung dari D01 §2 yang sudah diputus tertulis.
- **Status**: ORACLE_READY untuk hukum routing; NEEDS_OWNER_INPUT untuk implementasi fitur invoice final

#### LAU-T23 — invoice terlambat 1–3 bulan
- **M**: 4361 — "Invoice datang 1–3 bulan kemudian, reversal/replacement"
- **Fixture**: kiriman/receipt fisik selesai bulan-1 pada ESTIMATED 700.000; invoice vendor datang bulan-3 dengan koreksi 750.000, perlu reversal+replacement akrual.
- **Hasil per leg**: fisik (qty, tanggal, custody) bulan-1 tidak berubah; entri ESTIMATED asli tetap tersimpan sebagai histori (tidak dihapus), reversal+entri baru diposting sesuai aturan tanggal buku D01; laporan bulan-1 yang sudah difiling tetap seperti diajukan (ditandai `changed_since_filing`); tidak ada laporan antara bulan1–3 yang mengklaim READY/final untuk kiriman ini selagi harga masih outstanding.
- **Dilarang**: entri ESTIMATED asli ditimpa/dihapus; laporan mengklaim READY untuk periode yang biayanya belum lengkap.
- **Kebijakan**: LAU-DEC06 (mapping koreksi) belum diputus, fitur ABSENT — tapi invariant fisik-tetap/histori-utuh/no-false-READY ORACLE_READY sekarang.
- **Status**: NEEDS_OWNER_INPUT untuk mekanisme koreksi; invariant inti ORACLE_READY

#### LAU-T24 — tarif SKU khusus vs template vs paket dasar
- **M**: 4362 — "Tarif SKU khusus vs template SKU vs paket dasar"
- **Fixture**: tarif dasar paket 7.000/pcs; tarif override SKU "ABC-RED-M"=8.000/pcs; kiriman berisi SKU ABC-RED-M dan SKU XYZ-BLUE-L, proses & vendor sama.
- **Hasil per leg**: tepat satu dasar tarif berlaku per unit coverage — ABC-RED-M pakai override (8.000), XYZ-BLUE-L pakai dasar (7.000); tidak ada unit ditagih dua dasar sekaligus; tarif yang brand/proses/vendor-nya tidak cocok dengan kiriman aktual ditolak/direview, bukan diterapkan diam-diam.
- **Dilarang**: override SKU diterapkan ke SKU yang tidak cocok; dasar+override dijumlahkan untuk unit sama.
- **Kebijakan**: LAU-DEC05 sepenuhnya belum diputus, fitur ABSENT → default aman: tolak tarif ber-scope SKU sampai aturan scope dikonfigurasi.
- **Status**: PENDING_POLICY_VALUE/NEEDS_OWNER_INPUT

#### LAU-T25 — WIP tanpa SKU final
- **M**: 4363 — "WIP belum mempunyai SKU final"
- **Fixture**: kirim 100pcs WIP potongan tanpa SKU/brand/warna final ke vendor; terima kembali dengan QC (GOOD/BS) tanpa SKU final juga.
- **Hasil per leg (BASELINE)**: POST_DELIVERY dan POST_RECEIPT sukses tanpa memerlukan record SKU/FG; field rujukan SKU/recipe tetap opsional (boleh null); hasil QC (GOOD/BS) diposting normal dan authoritative terlepas dari SKU belum ada.
- **Dilarang**: kirim/terima diblokir error "SKU wajib"; sistem auto-membuat placeholder FG/SKU untuk memenuhi constraint.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY (bukti T3 browser AU, 10 kasus WIP)

#### LAU-T26 — batch campuran, override SKU tidak menyebar
- **M**: 4364 — "Batch campuran tujuan SKU/ukuran dengan rate khusus"
- **Fixture**: satu batch fisik 100pcs terbagi ukuran S=30, M=50, L=20; hanya ukuran M punya override (9.000/pcs), S/L pakai dasar (7.000/pcs).
- **Hasil per leg**: biaya = 30×7.000+50×9.000+20×7.000 = 210.000+450.000+140.000 = 800.000; override M tidak diterapkan ke porsi S/L.
- **Dilarang**: override M diterapkan ke seluruh 100pcs (salah, jadi 900.000); "rate tertinggi menang" diterapkan tanpa dasar.
- **Kebijakan**: LAU-DEC05, fitur ABSENT → default aman: tolak sampai scope override dikonfigurasi; hukum konservasi di atas tetap wajib begitu dibangun.
- **Status**: PENDING_POLICY_VALUE/NEEDS_OWNER_INPUT

#### LAU-T27 — retry network vs attempt baru sungguhan
- **M**: 4365 — "Paid failed-wash attempt, retry HTTP, actual new attempt"
- **Fixture**: attempt#1 gagal cuci, ditagih (mis. 2.000/pcs); POST_FAILED_WASH UUID U1, respons hilang di jaringan, client retry dengan UUID SAMA U1. Terpisah: attempt#2 yang benar-benar baru (UUID U2 berbeda, kejadian nyata kedua).
- **Hasil per leg**: retry U1 → replay ke hasil committed asal, hanya satu attempt/charge tercatat. Attempt#2 (U2) → posting sebagai attempt baru yang sah dan bisa ditagih terpisah karena benar-benar kejadian kedua. Tidak ada attempt manapun memfabrikasi status GOOD/BS tanpa QC nyata.
- **Dilarang**: retry U1 menagih dua kali; attempt#2 nyata diperlakukan sebagai retry dan digugurkan/digabung; status GOOD/BS dikarang.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T28 — rewash fee 0 tidak diwarisi
- **M**: 4366 — "Rewash dengan policy fee 0"
- **Fixture**: tarif paket normal=7.000/pcs; item BS dikirim rewash via SAVE_REWORK tujuan LAUNDRY.
- **Hasil per leg (BASELINE)**: rewash posting dengan produk tidak berubah, tanpa baris tagihan vendor otomatis menyalin tarif normal 7.000 (saat ini memang tidak ada jurnal biaya vendor untuk rework, hanya jurnal CONTRACTOR, 20av:739 — ini desain, bukan harga hilang). Bila fee rewash eksplisit suatu saat diaktifkan, harus punya versi & otorisasi sendiri, tidak otomatis mewarisi 7.000 dari paket normal.
- **Dilarang**: rewash diam-diam ditagih tarif paket normal; perubahan fee rewash tanpa versi/audit trail.
- **Kebijakan**: LAU-DEC03/06 (fee rewash eksplisit) belum diputus → default aman: fee tetap 0/absent sampai owner mengotorisasi.
- **Status**: ORACLE_READY untuk invariant no-inheritance; PENDING_POLICY_VALUE untuk fee eksplisit itu sendiri

#### LAU-T29 — klaim aktif lalu barang kembali/credit/invoice
- **M**: 4367 — "Claim aktif lalu barang datang/credit vendor/invoice"
- **Fixture**: item BS diklaim MISSING (SAVE_CLAIM), kompensasi diakrual (mis. 50.000). Kemudian item fisik ditemukan/kembali telat, dan/atau vendor menerbitkan credit note, dan/atau invoice terkait datang.
- **Hasil per leg**: pool custody/klaim/settlement tetap konsisten — kembalinya fisik memicu REVERSE_CLAIM_RESOLUTION atau rekonsiliasi eksplisit yang mengurangi/membalik kompensasi, bukan membiarkan "barang pulih di stok" DAN "kompensasi penuh tetap dibayar" berdiri bersamaan diam-diam.
- **Dilarang**: kompensasi 50.000 tetap dibukukan penuh sementara item fisik sudah kembali ke stok pakai; histori klaim dihapus.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T30 — dua operator rebutan kapasitas source sama
- **M**: 4368 — "Dua operator menagih kapasitas source yang sama"
- **Fixture**: satu source (receipt/delivery) sisa kapasitas 100pcs; dua sesi konkuren masing-masing klaim 60pcs (total diminta 120 > 100).
- **Hasil per leg**: pemenang ditentukan lock row-level; total teralokasi lintas kedua sesi tidak pernah melebihi 100pcs; permintaan yang melebihi batas ditolak atomik dengan error kapasitas jelas, bukan dipotong diam-diam.
- **Dilarang**: kedua sesi sukses total 120pcs (oversubscription); satu sesi dipotong diam-diam jadi 40 tanpa penolakan eksplisit.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY (bukti T2 AR `cp6_laundry_qc_concurrency`)

---

## G. Laundry T31–T36

#### LAU-T31 — master/draft berubah saat posting antre lock
- **M**: 4369 — "Master/draft berubah ketika posting menunggu lock"
- **Fixture**: preview harga berdasar versi tarif V1; saat POST antre di lock, master diedit ke V2 (atau draft/source berubah).
- **Hasil per leg**: begitu lock didapat, sistem merevalidasi source/harga/versi sebelum commit; bila versi berubah, preview ditolak STALE_VERSION, tidak pernah posting diam-diam dengan angka V1 lama tanpa memberi tahu operator.
- **Dilarang**: commit memakai angka preview stale seolah tidak ada perubahan.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T32 — respons commit hilang, refetch error
- **M**: 4370 — "Lost commit response, refetch error, reload/two-tabs"
- **Fixture**: POST UUID U1 commit sukses server tapi respons hilang; refetch klien juga error; user reload/buka dua tab dan mencoba lagi.
- **Hasil per leg**: retry dengan UUID sama rekonsiliasi ke transaksi yang sudah committed (replay idempotent), tidak pernah membuat dokumen posted kedua; UI menampilkan "tersimpan, menunggu sinkronisasi" bukan "gagal, ulangi"; pembacaan tidak terkait tetap bisa dilakukan sepanjang proses.
- **Dilarang**: duplikasi transaksi posted karena UUID baru dikira gagal; seluruh app terkunci untuk pembacaan tidak terkait.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T33 — role tidak sah menolak aksi laundry
- **M**: 4371 — "Role null/inactive/revoked/lokasi lain/view-only"
- **Fixture**: 4 state role × aksi laundry (edit tarif, approve invoice, post pembayaran, post QC): (a) role=null, (b) inactive, (c) baru dicabut, (d) valid untuk lokasi lain/view-only.
- **Hasil per leg**: server (Auth/RPC nyata) menolak tiap kombinasi tidak sah langsung; operator lapangan/fisik bisa post QC tapi tidak bisa edit harga/approve invoice/bayar tanpa hak.
- **Dilarang**: keamanan bergantung hanya pada UI menyembunyikan tombol sementara RPC tetap menerima; izin lama yang sudah dicabut masih diterima (cache stale).
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY (bukti matriks HTTP auditor 10 facade × 4 role)

#### LAU-T34 — pending price/recost gagal lalu report/close
- **M**: 4372 — "Pending price/recost gagal lalu report dan close"
- **Fixture**: kiriman punya `LAUNDRY_PRICE_UNKNOWN` atau `RECOST_FAILED_EXHAUSTED` outstanding; jalankan laporan periode dan coba tutup buku melalui tanggal itu.
- **Hasil per leg**: laporan menampilkan kiriman terdampak sebagai unknown/incomplete terlihat (tidak dihilangkan/dinolkan); `erp_accounting_close_preflight_v1` memblokir close untuk tanggal/scope terdampak dengan kode blocker spesifik; tidak ada laporan mengklaim READY/final untuk scope yang mengandung item ini.
- **Dilarang**: close berhasil selagi harga unknown tersisa; laporan membulatkan item unknown jadi 0 agar total seimbang.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY (bukti AW T1 P-02/P07)

#### LAU-T35 — legacy snapshot lintas upgrade/rollback
- **M**: 4373 — "Legacy snapshot dan upgrade/rollback sebelum/sesudah penggunaan"
- **Fixture**: transaksi laundry posted legacy (mis. akrual 700.000) sebelum paket T3/BA diterapkan; terapkan upgrade; lalu jalankan rollback paket itu.
- **Hasil per leg**: setelah upgrade, nilai 700.000 legacy terbaca persis tidak berubah; transaksi baru pasca-upgrade memakai logika baru (mis. perbaikan LAU-T14) dengan benar; bila ada refusal/guard baru menolak suatu operasi, histori legacy tidak dihapus/rusak; setelah rollback, objek sumber/izin(ACL)/trigger/marker cleanup kembali persis ke keadaan pra-upgrade (setara bar "127/127", tidak ada orphan).
- **Dilarang**: upgrade menulis ulang angka posted lama diam-diam; rollback meninggalkan tabel/grant orphan atau menghapus histori legacy.
- **Kebijakan**: tidak ada.
- **Status**: ORACLE_READY

#### LAU-T36 — UI desktop/HP, mixed coverage, switch mode/vendor
- **M**: 4374 — "UI desktop/HP, mixed coverage, mode/vendor switch, search large dataset"
- **Fixture**: `ConnectedLaundryPage` di lebar desktop & mobile; coverage campuran (sebagian komponen atas sebagian qty kiriman); ganti vendor di tengah form; ganti mode harga (paket vs komponen, setelah dibangun); search katalog vendor/komponen besar (≥500 baris).
- **Hasil per leg (BASELINE)**: basis harga (per PCS, per batch bila ada) tidak ambigu di layar; ganti vendor/mode membuat form/preview lama invalid dan refresh (tidak ada angka basi tersisa dari vendor/mode sebelumnya); setiap aksi lewat RPC/route nyata (`erp_get_laundry_qc_workspace_v1` dst), tidak pernah fallback fixture/demo klien; search/listing dipaginasi/difilter server-side, bukan memuat seluruh katalog ke browser.
- **Dilarang**: harga basi tampil setelah ganti vendor; fallback diam-diam ke data mock lokal saat RPC error.
- **Kebijakan**: mode per-batch dan switch mode paket/komponen adalah LAU-05b (ABSENT/CR-TUNDA).
- **Status**: ORACLE_READY untuk portion UI existing (baseline); NEEDS_OWNER_INPUT untuk portion per-batch/mode-switch

---

## Ringkasan status

| Keluarga | ORACLE_READY | NEEDS_OWNER_INPUT | Total |
|---|---|---|---|
| ACC-A (A01–A08) | 8 (A08 sebagian) | 1 sebagian (dalam A08) | 8 |
| ACC-B (B01–B07) | 3 penuh (B03,B05,B06) + 4 sebagian (B01,B02,B04,B07 — invariant ready, UI/return pending) | 4 sebagian | 7 |
| ACC-C (C01–C12) | 2 penuh (C08 recost linkage, C12) + sisanya invariant-only | 10 (C01–C07,C09–C11) | 12 |
| ACC-D (D01–D12) | 11 penuh (D01,D02,D03,D05,D06,D07,D08,D09,D10,D11,D12) | 1 sebagian (D04) | 12 |
| LAU-T01–T15 | 13 penuh (T01–T08,T13,T14,T15) + 2 sebagian (T09,T10,T11,T12 invariant ready) | 4 sebagian | 15 |
| LAU-T16–T30 | 6 penuh (T22 law,T25,T27,T28 sebagian,T29,T30) | 9 (T16–T21,T23,T24,T26 penuh/sebagian) | 15 |
| LAU-T31–T36 | 5 penuh (T31–T35) + 1 sebagian (T36) | 1 sebagian (T36) | 6 |
| **Total kasus (75)** | **≈50 murni ORACLE_READY** + **≈16 ORACLE_READY sebagian (hukum/invariant tetap, fitur CR menahan sisanya)** | **≈25 kasus dengan bagian NEEDS_OWNER_INPUT / PENDING_POLICY_VALUE** | **75** |

Catatan penghitungan: banyak kasus punya status ganda (invariant inti ORACLE_READY, tapi fitur CR-TUNDA atau KEBIJAKAN yang menahan sebagian oracle) — ini dicatat eksplisit di setiap blok kasus alih-alih dipaksa satu kategori. Kasus yang murni bergantung pada nilai kebijakan (ACC-DEC03/04/05, LAU-DEC01/03/05/06) diberi tag `PENDING_POLICY_VALUE` dengan default aman kontrak: tolak/pending, tidak pernah nol palsu atau OTHER_INCOME otomatis, tidak pernah harga eceran/tarif dikarang.

## Ambiguitas kontrak yang ditemukan

1. **Bukti concurrency nyata belum didefinisikan presisi.** M:5311 — "Dua sesi harus benar-benar koneksi terpisah dengan bukti blocking/winner/commit, bukan urutan sequential yang disebut concurrency" — kontrak tidak menetapkan ambang teknis (mis. berapa lama overlap, mekanisme bukti apa) yang dianggap cukup sah untuk D01/D02/T30 dsb.
2. **Enum status harga UNKNOWN/ESTIMATED/AGREED/FREE belum ada bentuk konkret.** M:4029 (LAU-R09) — "label ini usulan semantik, bukan enum existing" — memengaruhi LAU-T09/T11/T12 karena bentuk storage/nilai enum yang tepat belum diputus, hanya perilakunya.
3. **Batas pemakaian angka contoh owner sebagai fixture vs seed.** M:3739 — "Jangan otomatis menyebarkan tarif contoh ke seluruh vendor" — namun LAU-T02–T06 secara harfiah memakai angka Garment5000/Spray1000/Whisker1000/Wipping5000 sebagai skenario resmi acceptance; ambigu apakah angka ini boleh dipakai sebagai fixture test literal (sintetis, berlabel) atau harus diganti angka lain agar tidak "disebarkan" — di sini dipakai sebagai fixture berlabel sintetis mengikuti M:4335.
4. **"Batas sen" (ACC-A08) vs kebijakan pembulatan rupiah yang belum diputus (ACC-DEC06/D06).** M:5261 vs M:4460 — kontrak menuntut ketepatan sampai sen pada nominal transaksi, tetapi rupiah secara operasional tidak punya sub-unit resmi beredar dan aturan pembulatan resmi belum disahkan; ambigu apakah "sen" di sini berarti 2-desimal internal (20ap:520, harga manual) atau benar-benar diharapkan match ke José denominasi resmi begitu ACC-DEC06 diputus.
5. **Ketegangan cakupan CP6 antara M:1691–1699/1757 dan lampiran §0.** Master menempatkan CR aksesori/laundry sebagai "direkomendasikan sebelum audit final gabungan", bukan blocker otomatis (M:1697); lampiran C6 §0 mengutip owner "gw mau semuanya dibikin sekarang... termasuk all 22" sebagai dasar memasukkan SEMUA CR-TUNDA ke scope CP6 — instruksi tugas ini secara eksplisit menyatakan §0 BELUM disahkan owner secara tertulis (beda dengan D01–D05 yang sudah ditandatangani di addendum induk bagian 9). Ini membuat status scope CR (ACC-04b, LAU-05b, LAU-06b) untuk 75 kasus ini formally undecided sampai D06 disahkan.
6. **Nilai barang rusak (bukan "bekas") pada inspeksi penerimaan tidak eksplisit diatur.** ACC-C01 (M:5279) memisahkan 80 layak vs 20 rusak, tetapi ACC-DEC03 (M:4456/4457) hanya membahas nilai "barang bekas/pemulihan", tidak eksplisit membahas status finansial 20 unit "rusak" (write-off senilai berapa, kapan diakui). Perlu klarifikasi apakah "rusak" masuk cakupan ACC-DEC03 yang sama atau kategori terpisah.
7. **OTHER_INCOME sebagai akun lawan: dua konteks berbeda bisa tertukar.** D05 (addendum bagian 7, disahkan) menetapkan OTHER_INCOME sebagai akun lawan untuk **FG tanpa sumber produksi** (lot non-PO). M:4456/ACC-DEC03 secara eksplisit MELARANG OTHER_INCOME otomatis untuk **nilai pemulihan aksesori bekas**. Kedua konteks "barang tanpa sumber jelas" ini mirip secara permukaan; kontrak tidak secara eksplisit menandai perbedaannya sehingga berisiko writer mengaplikasikan preseden D05 secara salah ke ACC-DEC03 (harus ditolak — beda keputusan, beda status ratifikasi).
8. **Dasar alokasi biaya untuk borongan (LAU-T20) tidak dijelaskan bentuknya.** M:4358 hanya menetapkan hukum konservasi total (100.000 tetap 100.000 pada penerimaan 40+60), tapi tidak menyatakan apakah pengakuan biaya harus proporsional per qty (40% di penerimaan pertama), murni di penerimaan terakhir, atau metode lain — hanya batas atas/bawahnya (tidak boleh melebihi total, tidak boleh 0 sebelum ada penerimaan) yang pasti dari teks.
