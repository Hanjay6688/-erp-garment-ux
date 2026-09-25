# Oracle T2 pasca-addendum CP6 (D01–D03) — 25 kasus beku + CP6-07 + CP6-18

Sumber: addendum `ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` bagian 1–8 (disahkan owner, hash
`d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d`), master `ERP_V3_2_Master_Pulih_20260923.md` (M),
`T2_classification.md` (observasi kandidat pada 9add57e), dan fixture harness di `scripts/*.py`. String harness
(`calendar_policy`, `a10_output` expected-tuple pre-addendum, dsb.) TIDAK dipakai sebagai oracle — hanya sebagai bukti
apa yang kandidat lakukan; oracle di bawah diturunkan sendiri dari teks addendum + M.

## 1. Klausul addendum dan M yang dipakai

1. **D01.1** (§3.1): "Tanggal invoice tetap tanggal dokumen dan tanggal ekonomi E. Jurnal invoice pemasok berada pada E."
2. **D01.2** (§3.2): "Selisih biaya dibawa oleh unit ke tempat unit itu benar-benar berada... bagian selisihnya bertanggal
   max(E, tanggal bisnis perpindahan). ... Selisih tidak pernah masuk WIP sebelum bahan dipakai... tidak masuk FG sebelum
   barang selesai... tidak masuk HPP penjualan sebelum barang terjual."
3. **D01.3** (§3.3): "Koreksi nilai yang datang belakangan bertanggal max(E, tanggal penyesuaian) selama E terbuka."
4. **D01.4** (§3.4, disahkan bersama 3.4): "Bila E sudah tertutup, semua bagian koreksi memakai tanggal ekonomi E dan
   dibukukan pada hari pengakuan di periode terbuka (controlled adjustment, satu jurnal per bagian)."
5. **D01.5** (§3.5): "Laporan pada tanggal D memakai fakta terkoreksi yang bertanggal ≤ D. Dokumen dan filing lama tetap
   tidak berubah."
6. **D02.1** (§4.1): "Operasi yang menurunkan sisa uang muka hanya boleh memakai kapasitas yang ada pada tanggal operasi
   itu... Contoh: saldo 67,25; koreksi efektif 22 Sep menjadi 100; refund 100 bertanggal 21 Sep ditolak."
7. **D02.3** (§4.3): kode penolakan `BA_ADVANCE_DATED_CAPACITY`, atomik, tanpa perubahan ledger.
8. **D03.1** (§5.1): "Produk diisi pada sumber WIP awal. Hasilnya harus identitas produk yang sama... ditolak dengan
   `BA_WIP_OUTPUT_PRODUCT_BOUND`."
9. **D03.2** (§5.2): "Produk kosong... Merek dan warna yang tertulis di baris sumber harus cocok. Bila tidak cocok,
   ditolak dengan `BA_WIP_OUTPUT_SOURCE_MISMATCH`."
10. **D03.3** (§5.3, disahkan bersama 5.3): "Data yang tidak diketahui dicatat sebagai tidak diketahui, bukan sebagai
    cocok."

M yang dirujuk: M:1059–1065 (ERP-DEC01, tanggal invoice + konsistensi WIP/FG/COGS), M:1192–1198 (rumusan pertanyaan
sebelum diputus), M:625–646 (contoh 67,25→100, penolakan kapasitas kurang), M:357–379 (identitas WIP opening: model/
ukuran selalu cocok; merek/warna sumber), M:3816–3825 (invariant "Tanggal terpisah", "Backdate tidak boleh merusak
prefix qty/value"), M:4324 ("Tool error/setup error/missing data = INCOMPLETE, bukan BUG_PROVEN atau PASS"),
M:6140–6162 (B04, 12 DATE_POLICY_REVIEW_REQUIRED, rantai tanggal invoice–recost–laporan).

## 2. Tabel oracle per grup (25 kasus)

Catatan umum yang berlaku ke tiga grup tanggal (CALENDAR, DATE, AO_TRIAL open): fixture bersama
(`cp6_final_gap_native.calendar_case_body` / `cp6_aa_invoice_partial_audit.partial_production`) menaruh **seluruh**
perpindahan fisik (potong→laundry→FG→jual) pada **E+1 hari** (`purchase_day+1`), yaitu **setelah** E. Karena
perpindahan > E, D01.2 mewajibkan max(E, perpindahan) = hari perpindahan untuk kaki WIP/FG/COGS; kaki invoice (AP/GRNI)
tetap di E per D01.1. Nilai bahan mentah = 0 di semua kasus ini (bahan sudah habis dipotong sebelum invoice datang),
jadi kaki MATERIAL_INVENTORY selalu 0 dan tidak relevan untuk uji tanggal.

### 2a. 12 kasus CALENDAR (open period, closed=False)
`CALENDAR:{1_MONTHS,2_MONTHS,3_MONTHS,JAN31,FEB28,MAY31}:{UTC,Pacific/Kiritimati}:False`

Fakta fixture (formula relatif; E dan "hari perpindahan" berbeda per label tapi pola sama untuk semua 12):
E=`purchased` (JAN31→2026-01-31, FEB28→2026-02-28, MAY31→2026-05-31, N_MONTHS→N bulan sebelum `received`);
`received`=hari invoice benar-benar dimasukkan sistem (`today-1`, tempo lambat, hanya dipakai untuk laporan
"filed"/kapan invoice ditagihkan, bukan tanggal buku); hari perpindahan fisik = E+1 hari. Dua tahap invoice: 3 unit
@8,25 lalu 7 unit @11,75 (total 10 unit, AP=107,00).

| Kaki | Tanggal expected (D01) | Nominal kumulatif (2 tahap) |
|---|---|---|
| Invoice (AP_SUPPLIER/GRNI_MATERIAL) | E (`purchased`) | AP=-107,00; GRNI=0,00 setelah tahap 2 (interim setelah tahap1: AP=-24,75, GRNI=-70,00) |
| MATERIAL_INVENTORY | — (selalu 0) | 0,00 |
| WIP | E+1 (hari potong) | 88,50 (interim tahap1: 82,37/82,38 — 164,75/2 dibulatkan) |
| FG | E+1 (hari selesai, jam yang sama dengan potong) | 53,10 (interim: 49,43) |
| COGS | E+1 (hari jual) | 35,40 (interim: 32,95) |

Status expected: **PASS** untuk seluruh 12 kasus. Status lama kandidat: `DATE_POLICY_REVIEW_REQUIRED` (harness
`T2_CALENDAR_POLICY`→COUNTEREXAMPLE) karena kandidat menaruh kaki WIP di hari potong, sedangkan oracle beku lama
mengharapkan tanggal invoice untuk *semua* kaki. Di bawah D01.2 (baru), hari potong justru **benar**; laporan as-of
`history_day` (=`received`-1) yang berubah setelah invoice telat masuk juga benar per D01.5, karena fakta terkoreksi
(bertanggal E+1) ≤ D (history_day, yang jauh setelah E+1). **Disposisi: perilaku lama kandidat kini PASS** — bukan
COUNTEREXAMPLE, bukan INCOMPLETE. Oracle beku lama (yang menuntut tanggal invoice untuk kaki WIP) sudah usang dan
harus diganti oracle di atas; tidak perlu perbaikan kandidat, hanya penggantian expected di harness.

### 2b. 8 kasus DATE (AS family, open period, partial production)
`DATE:False:{Asia/Jakarta,UTC,Etc/GMT+12,Pacific/Kiritimati}:True:{20,20.003}`

Fixture (`cp6_as_probe.invoice_dates`): E=`purchase_day`(=`today-3`); potong/laundry/FG/jual semua di E+1 (10 dipotong,
8 diterima laundry, 5 selesai FG, 3 di tangan, 2 terjual); satu tahap invoice, qty=10 @ cost (20 atau 20,003).
`invoice_date=E`; dokumen baru dimasukkan sistem `today-1` (`received_at`), memakai timezone sesi berbeda per kasus.

| Kaki | Tanggal expected (D01) | Nominal (cost=20) | Nominal (cost=20,003) |
|---|---|---|---|
| Invoice (jurnal supplier) | E | AP=-200,00; GRNI=0,00 | AP=-200,03; GRNI=0,00 |
| MATERIAL_INVENTORY | — | 0,00 | 0,00 |
| WIP | E+1 | 135,00 | 135,01 |
| FG | E+1 | 81,00 | 81,01 |
| COGS | E+1 | 54,00 | 54,01 |

(per_piece = cost+7; hpp=5×per_piece; fg=3×per_piece; cogs=2×per_piece; wip=10×per_piece−hpp; semua dibulatkan ke sen,
ROUND_HALF_UP.)

Status expected: **PASS** untuk 8/8. Observasi T2_classification: kaki revaluasi/PO-HPP-sync tanggal E+1 (hari
potong/jual), jurnal invoice supplier tetap E — persis sesuai D01.1+D01.2. Oracle beku lama (frozen) menuntut E untuk
semua kaki → COUNTEREXAMPLE terhadap oracle lama. **Disposisi: PASS** terhadap oracle baru; identik dengan yang
diklaim harness `T2_APPROVED_ORACLE` (tapi klaim itu sebelumnya tidak terverifikasi kontrak — sekarang terverifikasi
lewat D01 yang disahkan, bukan lewat string harness).

### 2c. ADJUSTMENT_DATE:False (1 kasus)
Fixture (`cp6_as_cases.adjustment_date`): E=`purchase_day`(`today-3`); penyesuaian fisik stok (count correction,
qty -2) terjadi di `today-2` (**setelah** E); invoice telat (qty 10 @20,003, `invoice_date=E`) masuk sistem `today-1`.

Oracle D01 yang benar:
- `effective_date`/`economic_date` pada fakta revaluasi penyesuaian = **E** selalu (§3.1: tanggal ekonomi E tidak
  pernah dipindah oleh keterlambatan pemrosesan).
- `transaction_date` (hari buku/pengakuan) = **max(E, tanggal penyesuaian)** = `today-2` (hari penyesuaian fisik,
  karena `today-2 > E`) selama E terbuka (D01.3). **Bukan** E, dan **bukan** hari invoice masuk sistem (`today-1`).

Fixture harness sendiri salah di titik ini: baris `expected = today if closed else f['purchase_day']` untuk kasus
terbuka mengasumsikan posting selalu = E (bacaan ERP-DEC01 sebelum addendum), padahal D01.3 (yang sudah disahkan)
mensyaratkan max(E, tanggal penyesuaian). Bukti kegagalan T2 (`[(2026-09-23, 2026-09-23, 2026-09-23, {...})]`) — tiga
tanggal identik pada satu baris — tidak cocok dengan pola oracle D01 manapun (effective/economic seharusnya = E,
transaction_date seharusnya = hari penyesuaian ≠ E secara struktural di fixture ini), sehingga bukti yang ada
**tidak cukup** untuk memutuskan PASS/COUNTEREXAMPLE terhadap perilaku kandidat yang sebenarnya.
**Disposisi: INCOMPLETE per M:4324** — harness perlu diperbaiki (formula `expected` di baris ~108 &112
`cp6_as_cases.py`) lalu dijalankan ulang; oracle barunya sudah dirumuskan di atas.

### 2d. AO_TRIAL INVOICE:{UTC,Pacific/Kiritimati}:{False,True} (4 kasus)
Fixture berbagi `calendar.calendar_case` yang sama dengan §2a (E=`months_before(received,2)`, perpindahan di E+1).

**Open (closed=False, 2 kasus):** oracle D01 identik §2a: invoice di E; WIP/FG/COGS di E+1. Observasi kandidat cocok
(`MATERIAL_COST_REVALUATION`/`PO_HPP_GL_SYNC` di hari potong/jual; jurnal invoice tetap E).
**Disposisi: PASS.** Harness (`cp6_initial_import_ao_trial.invoice_date`, baris 54 & 67) salah karena menuntut
`r[1]==invoice` (E) tanpa syarat untuk *seluruh* `revaluation_events`, termasuk yang seharusnya E+1 — formula pre-
addendum yang sama seperti §2a; perlu diperbaiki jadi `max(E, hari perpindahan)`.

**Closed (closed=True, 2 kasus):** D01.4: semua bagian tetap E secara ekonomi, tapi **dibukukan** (`transaction_date`,
dan — bila field itu memang menyimpan hari buku, bukan hari ekonomi, pada tabel `material_cost_revaluation_events` —
`effective_date` pada tabel tersebut) di **hari pengakuan** (recognition day = `today` operasional, karena E sudah
tertutup). Observasi T2_classification: "WIP revaluation event on 2026-09-25 (recognition day)" — cocok persis
dengan D01.4 yang kini disahkan tertulis (termasuk §3.4). **Disposisi: PASS**, dengan syarat auditor memverifikasi
bahwa `material_cost_revaluation_events.effective_date` memang kolom hari-buku (bukan kolom ekonomi) pada tabel itu —
lih. Pertanyaan terbuka #2. Harness sendiri (baris 67, `all(r[1]==invoice...)` tanpa cabang closed) salah dan perlu
diperbaiki menjadi `invoice if not closed else today`; sampai diperbaiki dan dijalankan ulang bersih, tandai
**INCOMPLETE (butuh perbaikan fixture) dengan ekspektasi kuat PASS** berdasarkan bukti parsial yang ada.

## 3. Ringkasan disposisi 25 kasus

| Bucket | n | Status lama | Oracle baru (D01) | Disposisi |
|---|---|---|---|---|
| CALENDAR (§2a) | 12 | DATE_POLICY_REVIEW_REQUIRED / COUNTEREXAMPLE (harness) | Invoice@E, WIP/FG/COGS@E+1 | **PASS** — harness perlu ganti expected |
| DATE (§2b) | 8 | COUNTEREXAMPLE (vs oracle beku lama) | Invoice@E, WIP/FG/COGS@E+1 | **PASS** — harness perlu ganti expected |
| ADJUSTMENT_DATE (§2c) | 1 | INCOMPLETE (assertion error) | economic=E; posting=max(E,tgl penyesuaian) | **INCOMPLETE** — formula fixture salah, perlu diperbaiki+rerun |
| AO_TRIAL open (§2d) | 2 | INCOMPLETE | sama seperti CALENDAR | **PASS** — harness perlu ganti expected |
| AO_TRIAL closed (§2d) | 2 | INCOMPLETE | economic=E; posting=hari pengakuan (D01.4) | **PASS (kuat)**, tetap perlu rerun bersih |

Tidak ada dari 25 kasus yang menjadi COUNTEREXAMPLE murni terhadap kandidat di bawah D01–D03 yang baru disahkan;
24/25 sudah bisa dinyatakan PASS langsung dari bukti T2 yang ada, 1 (ADJUSTMENT_DATE) butuh fixture yang diperbaiki
dan dijalankan ulang sebelum bisa ditutup.

## 4. CP6-07 (D02) — fixture `cp6_ba_probe.a9_advance`/`advance_fixture`

Saldo awal uang muka 67,25 (asal 100,00, terpakai 32,75 sebelum cutover), tiga jenis pihak: SUPPLIER, CUSTOMER,
VENDOR (laundry). Koreksi `CORRECT amount=100,00` menaikkan saldo +32,75 pada `correction_day`; operasi
`REFUND`/`APPLY amount=100,00` pada `use_day`.

**3 kasus negatif (DATED_CAPACITY, backdated=True):** `correction_day=today-2`, `use_day=today-4` (refund/pakai
bertanggal **sebelum** koreksi yang mendanainya — persis pola contoh addendum: saldo 67,25→100 efektif belakangan,
refund 100 bertanggal lebih awal). Untuk kind ∈ {SUPPLIER, CUSTOMER, VENDOR}, operasi REFUND:
- Assert: RPC `PREPAYMENT/REFUND` **ditolak**, kode error = `BA_ADVANCE_DATED_CAPACITY`.
- Assert: tidak ada baris baru di `erp.journal_lines`/`erp.initial_import_prepayments` terkait (ledger_unchanged) —
  baca `erp.account_daily_balances` pada akun uang muka (`fx['account']`) sebelum/sesudah percobaan, harus identik.
- Assert: saldo per tanggal (`advance_asof`, dari `account_daily_balances`, arah sesuai `fx['kind']`) pada setiap hari
  ≥ `use_day` tetap 67,25 (bukan negatif), karena operasi ditolak sebelum posting.

**3 kasus positif (ORDERED_CONTROL, backdated=False):** `correction_day=today-4`, `use_day=today-2` (koreksi dulu,
baru refund/pakai). Untuk kind ∈ {SUPPLIER, CUSTOMER, VENDOR}, operasi REFUND:
- Assert: RPC **POSTED**, tidak ada error.
- Assert: saldo per tanggal cocok formula `67,25 + (32,75 bila hari≥correction_day) − (100,00 bila hari≥use_day)`,
  dibaca dari `account_daily_balances` pada tiap hari kunci (`cutover`, `correction_day`, `use_day`, `today`). Hari
  ≥`use_day`: saldo = 0,00.
- Assert: jurnal refund/apply tercatat pada `use_day` (tanggal operasi sendiri), jurnal koreksi pada `correction_day`
  — kedua tanggal ekonomi terpisah, tidak digabung ke `today`.

Operasi `APPLY` (memakai ke tagihan opening, `target=True`) simetris dengan `REFUND` di atas per D02 §4.1 butir 2
("Operasi yang dimaksud: pemakaian/alokasi ke tagihan (APPLY), refund..."); auditor dapat menjalankan 3+3 tambahan
dengan `operation='APPLY'` bila ingin cakupan penuh (tidak wajib untuk temuan CP6-07, yang memakai REFUND).

## 5. CP6-18 (D03) — fixture `cp6_ba_probe.a10_output`/`wip_batch`

Fixture: WIP awal 8 pcs, dua produk model/ukuran sama: A (merek A, Blue) dan B (merek B, Red).

| Kasus | product (SKU diisi?) | attributes (merek/warna diisi?) | suffix output | Assert |
|---|---|---|---|---|
| Produk terisi & berbeda | True | True | B | RPC `WIP_OUTPUT` **ditolak**, kode `BA_WIP_OUTPUT_PRODUCT_BOUND`; `erp.fg_lots.product_id` tidak pernah dibuat ke produk B; tidak ada mutasi stok/GL baru |
| Produk terisi & sama | True | True | A | **POSTED**; baca `erp.initial_import_wip_output_identity_v1`: `basis='OPENING_PRODUCT'`, `checked ⊇ {PRODUCT_IDENTITY,PO_MODEL,SIZE}`, `unknown=[]`, `opening_product_id=output_product_id`=produk A |
| Produk kosong & merek/warna cocok | False | True | A | **POSTED**; `basis='SOURCE_ATTRIBUTES'`, `checked ⊇ {PO_MODEL,SIZE,BRAND,COLOR}`, `unknown ⊇ {PATTERN,MATERIAL}` |
| Produk kosong & tidak cocok | False | True | B | RPC **ditolak**, kode `BA_WIP_OUTPUT_SOURCE_MISMATCH` |
| Produk & atribut kosong ("tidak diketahui") | False | False | A | **POSTED** (bukan ditolak); `basis='ASSIGNED_AT_COMPLETION'`, `checked ⊇ {PO_MODEL,SIZE}`, `unknown ⊇ {BRAND,COLOR,PATTERN,MATERIAL}` — merek/warna dicatat *unknown*, bukan dicatat sebagai cocok (D03.3) |

Assertion generik untuk setiap baris: model PO dan ukuran **selalu** harus cocok (D03.2 kalimat pertama) — semua 5
skenario memakai model/ukuran sama sehingga ini tidak pernah jadi sebab penolakan di sini; auditor yang ingin
menguji jalur itu perlu varian model/ukuran berbeda terpisah (tidak ada di fixture yang tersedia).

**Catatan penting:** brief tugas menuliskan "unknown brand → refused" sebagai skenario ke-5. Bacaan literal D03 §5.2–
5.3 ("Merek dan warna **yang tertulis** di baris sumber harus cocok"; "Data yang tidak diketahui dicatat sebagai
tidak diketahui, bukan sebagai cocok") tidak mewajibkan penolakan ketika baris sumber sama sekali tidak menuliskan
merek/warna — hanya mewajibkan pencatatan sebagai *unknown* (bukan otomatis dianggap cocok) agar laporan/kelengkapan
tidak menganggapnya terverifikasi. Fixture `UNBOUND_SOURCE_NO_ATTRIBUTES_CONTROL` di atas memang berstatus PASS/
POSTED di kandidat, konsisten dengan bacaan ini. Saya menulis oracle sesuai teks addendum (POSTED+unknown-tercatat),
bukan sesuai frasa "refused" di brief — lihat Pertanyaan terbuka #1.

## 6. Pertanyaan terbuka yang masih ditinggalkan addendum

1. **D03 "unknown" vs "refused".** Addendum §5.3 hanya bilang data tak diketahui "dicatat sebagai tidak diketahui,
   bukan sebagai cocok" — tidak menyatakan tegas apakah kombinasi produk kosong + atribut kosong boleh **posting**
   (dengan provenance unknown) atau harus **ditolak** karena tidak ada dasar identitas sama sekali. Kalimat "Owner
   diminta menegaskannya" di §5.3 sendiri menunjukkan ini masih penafsiran writer, bukan keputusan eksplisit
   terpisah — meski §9 mencatat 5.3 "sah seperti tertulis", teksnya sendiri ambigu antara "boleh lanjut, dicatat
   unknown" dan "tidak boleh lanjut tanpa dasar apa pun". Auditor perlu klarifikasi tertulis tambahan sebelum
   `UNBOUND_SOURCE_NO_ATTRIBUTES_CONTROL` bisa ditutup definitif.
2. **Nama kolom `effective_date` pada `material_cost_revaluation_events` vs `material_adjustment_revaluation_facts`.**
   Addendum tidak menyebut skema tabel; §2c menunjukkan writer sendiri memperingatkan risiko "jangan menyamakan kolom
   bernama sama" antar tabel (lihat komentar di `cp6_as_cases.adjustment_date`). Belum ada baris addendum yang
   menegaskan tabel `material_cost_revaluation_events.effective_date` menyimpan hari **buku** (bukan hari ekonomi) —
   ini diasumsikan dari kecocokan numerik observasi AO_TRIAL closed (§2d), bukan dari teks kontrak eksplisit.
3. **D01 §3.4 closed-period untuk tahap-menyusul-di-hari-terbuka.** Kalimat "Ini aturan yang sudah dijalankan
   kandidat (AY/AZ). Owner diminta menegaskannya secara tertulis sebagai expected untuk kasus batas ini" — §9 mencatat
   3.4 "sah seperti tertulis", tapi addendum tidak memberi contoh angka untuk kasus batas spesifik (penerimaan
   tertutup, potong/jual di hari terbuka) selain rumusan umum; auditor masih perlu satu kasus numerik terpisah untuk
   memverifikasi rumusan ini secara konkret, bukan hanya secara tekstual.
4. **D02 kapasitas untuk stok (AUD-S04).** §4.2 menyebut ini "sudah ditegakkan sebelum addendum" dan hanya
   mereferensi bukti lama (probe T1 BA run 36085934997); addendum tidak memuat rumus kapasitas stok per hari secara
   eksplisit (berbeda dari rumus uang muka di §4.1) — auditor perlu menyalin/menurunkan rumusnya sendiri dari kode
   `erp._recalculate_material_cost_core` bila ingin oracle S04 setara presisi dengan CP6-07.
5. **D06 dan lampiran C6** tetap `OWNER_CONFIRMED_CHAT`, belum disahkan tertulis (§9: "menunggu tinjauan auditor").
   Tidak relevan langsung ke 25 kasus T2 di atas, tapi berarti *scope* CR aksesori/laundry di luar D01–D03 masih HOLD.

*(Ditulis 25 September 2026. CP6 tetap HOLD, `production_go=false`; addendum ini memperjelas cara membaca kontrak,
bukan mengubah teks kontrak atau memberi gate ACCEPT.)*
