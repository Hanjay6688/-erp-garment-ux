# Tinjauan Independen: CP6 BA Audit Closure

File sumber ditinjau (bukan hasil generate di `supabase/migrations/`, yang tidak ada di checkout ini):
- `supabase/dev/cp6_ba_t1_family.sql` (T1_FAMILY dev install, isi logika asli, 1309 baris)
- `supabase/release/cp6-t3-src/20260925010000_erp_v2_6_20ba_cp6_audit_closure.sql` (release source; badan fungsi identik dengan dev file, dibungkus guard T3)
- `supabase/release/cp6-t3/20260925010000_erp_v2_6_20ba_cp6_audit_closure.sql` (release final, hash tertanam)
- `scripts/cp6_ba_probe.py`, `scripts/cp6_ba_build.py`
- `git diff 9add57e a095a9d -- src` (A2)
- `git show 35612d6` (T2 regression fix, sudah tergabung di dev file yang saya baca)

Catatan struktural: klaim menyebut `supabase/migrations/20260925010000_...sql`; file itu **tidak ada** di path tersebut. BA baru berupa T1_FAMILY dev install + T3 release-candidate di `supabase/release/`, belum dipindah ke `supabase/migrations/`. Ini bukan bug fungsional tapi mempengaruhi bagian "idempotent/rollback-safe" di bawah.

---

## A1 [CP6-09] — Identitas impor lintas-batch

**(a) Guard**: `supabase/dev/cp6_ba_t1_family.sql:226-272`, fungsi `erp.post_opening_balance` (definisi dimulai baris 51). Kondisi inti baris 236-267, raise di baris 269-271.

**(b) Predikat**: Hanya berlaku jika `h.migration_batch_id is not null` (baris 226). Untuk setiap tipe saldo, dicari baris `o` dari header POSTED lain dengan `migration_batch_id` **berbeda** dan identitas yang sama:
- `CASH_BANK`: `i.cash_account_id=o.cash_account_id` (baris 237) — identitas berbasis id akun kas, bukan `coa_account_id` di baliknya.
- `MATERIAL`: `material_id`+`location_id` sama dan `i.roll_id is not distinct from o.roll_id` (baris 238-240) — perbandingan null-safe, benar untuk roll maupun non-roll.
- `FINISHED_GOODS`: `product_id` sama **dan** ada `fg_stock_movements` OPENING dari `o` dengan `location_id=coalesce(i.location_id,default)` dan `quality_grade=coalesce(i.quality_grade,'GRADE_A')` (baris 246-251) — grade beda dianggap identitas beda.
- `WIP`/`BS`: identitas berbasis model/stage/holder (dan vendor untuk BS), **kecuali** kedua sisi punya `initial_import_production_sources` (PO impor sendiri) — maka dianggap sumber berbeda dan tidak diblok (baris 252-267).
- `MATERIAL` khusus: dikecualikan jika `o` terikat pada `initial_import_receipt_lines` (uninvoiced receipt) **dan** `i` punya `initial_import_opening_stock_sources` yang mengarah ke baris staging `UNINVOICED_RECEIPT` yang cocok (baris 241-245) — bukti stok fisik nyata dari dokumen berbeda.

**(c) Percobaan bypass**:
1. *Casing/whitespace pada kode master* (`material_sku`, `location_code`, dsb.) — **diblokir**: perbandingan dilakukan pada `*_id` (UUID) yang sudah diresolusi via lookup master data saat staging, bukan pada teks mentah, jadi variasi huruf besar/kecil tidak relevan pada tahap ini.
2. *Roll vs non-roll* — tidak ada celah nyata: fabric wajib roll (`AE_FABRIC_OPENING_REQUIRES_ROLL`, baris 140-142), non-fabric tidak pernah roll, jadi `roll_id is not distinct from roll_id` selalu membandingkan dua item dengan disiplin tipe material sama.
3. *Grade beda* pada FG — **tidak diblokir (dengan benar)**: grade berbeda dianggap stok fisik berbeda, ini diverifikasi lewat kolom `quality_grade` pada `fg_stock_movements`, bukan input mentah — sulit dipalsukan tanpa benar-benar memposting grade lain.
4. *Jalur legacy langsung* `erp.post_opening_balance` tanpa `migration_batch_id` — **guard A1 dilewati sepenuhnya** (baris 226 syarat `is not null`). Dua header **legacy** (bukan impor) dengan identitas sama tidak diblok oleh A1 maupun oleh guard AR (`20ar`, baris 372: `(h.migration_batch_id is null)<>(oh.migration_batch_id is null)` — XOR, jadi legacy-vs-legacy = false = tidak diblok). Ini di luar cakupan klaim A1 (yang eksplisit tentang *import batch*), tapi tetap merupakan celah residual yang audit tidak klaim tertutup.
5. *Reversal lalu re-post* — WIP/BS opening items tidak punya jalur "un-post" yang dikembalikan ke DRAFT dalam kode ini (`update ... status='POSTED'` di baris 327 bersifat final untuk header); tidak ada rute reversal-lalu-re-post yang teridentifikasi untuk opening balance itu sendiri (berbeda dari WIP output yang punya REVERSE). Tidak relevan sebagai bypass di sini.
6. *Cash alias GL account* — **celah nyata, tidak diverifikasi tertutup**: identitas `CASH_BANK` dibandingkan pada `cash_account_id`, bukan `coa_account_id`. Jika dua `cash_accounts` (dua kode berbeda) dibuat menunjuk ke `coa_account_id` yang sama, dua batch impor bisa masing-masing membuat opening `CASH_BANK` dengan `cash_account_id` berbeda tapi akun GL sama → A1 tidak mendeteksinya sebagai identitas sama. Skema `erp.cash_accounts` (constraint unik pada `coa_account_id`?) tidak ada di checkout ini (base schema di luar migrasi CP6), jadi status ini **tidak dapat dipastikan** dari source yang tersedia — dicatat sebagai risiko yang perlu kasus auditor tersendiri.
7. *Lokasi lain* — **tidak diblokir (kontrol positif, benar)**: `import_overlap(... other_location=True)` di probe (baris 148-171 `cp6_ba_probe.py`) menunjukkan lokasi kedua yang berbeda tetap boleh diposting; diverifikasi lewat `PLAN` baris 625-626 `MATERIAL_SECOND_BATCH_OTHER_WAREHOUSE_CONTROL`/`FINISHED_GOODS_...`, status harus `PASS`.

**(d) Verdict: PARTIAL.** Predikat inti (material/roll/FG-grade/cash-per-id/WIP-BS) tertutup rapat untuk kasus impor-vs-impor. Dua celah residual di luar bukti tertutup: (i) legacy-vs-legacy tidak dicek sama sekali (di luar klaim, tapi ada), (ii) identitas `CASH_BANK` berbasis `cash_account_id`, bukan `coa_account_id` di baliknya — berpotensi memungkinkan duplikasi ekonomi lewat dua akun kas yang alias ke GL account sama; tidak dapat diverifikasi tertutup dari source yang ada.

**(e) Resep POSITIVE/NEGATIVE**: `scripts/cp6_ba_probe.py:132-171` (`import_overlap`), fixture `cp6_opening_overlap_probe.imported(cur,today,kind)` (`scripts/cp6_opening_overlap_probe.py:21`) membuat batch pertama; `opening_rows(kind,tag)` (baris 134-145) membuat baris kedua dengan identitas sama/beda. RPC: `api.call(cur,'CREATE',...)`, `api.upload(cur,batch,'OPENING_BALANCE_ITEM',[row])`, `api.invoke(cur,'FINALIZE',batch)` (semua dari `cp6_ao_ap_installed` diimpor sebagai `api` di `cp6_aw_probe`). NEGATIVE: `kind='MATERIAL'`, sama `material_sku`/`location_code`/`roll` → harap `BA_IMPORT_OPENING_ALREADY_POSTED`. POSITIVE: sama tapi `other_location=True` → harap `status=='POSTED'` dan `posted_headers==2`. Bungkus dengan `r1.peer.attempt(cur,lambda:...)` dan verifikasi lewat `cases(cur,today)` gaya `cp6_aw_probe.py:861`, `api=cp6_aw_probe.api`.

---

## A3 [CP6-02] — WIP dated remaining vs reversal

**(a) Guard**: `supabase/dev/cp6_ba_t1_family.sql:390-406`, dalam `erp.complete_initial_import_wip_v1` (definisi mulai baris 329), cabang `COMPLETE` (baris 383).

**(b) Predikat**: `v_floor` = minimum sisa pcs pada hari output (`v_date`) **dan setiap hari sesudahnya** yang punya event (output atau reversal), dihitung mundur dari `s.qty_pcs` dikurangi kumulatif output ≤ hari itu, ditambah kumulatif reversal ≤ hari itu (baris 392-403). Jika `v_qty>v_floor` → `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING`. Efeknya: output baru tidak boleh memakai pcs yang baru "kembali" via reversal di kemudian hari — checked di setiap hari ≥ tanggal output, bukan cuma hari ini.

**(c) Percobaan bypass**:
1. *Tanggal tepat sama dengan tanggal reversal* — **tidak diblokir (benar, by design)**: `physical_at` output pada hari reversal dijamin setelah reversal itu via `v_at:=greatest(v_at,(select max(rv.physical_at)+interval '1 microsecond' ... where erp._cp3_business_date(rv.physical_at)=v_date))` (baris 447-449), jadi timeline fisik tidak pernah negatif dalam hari yang sama. Diverifikasi oleh probe `a3_after_reversal` (baris 255-267), kasus `A3:COMPLETE_ON_REVERSAL_DAY_CONTROL`.
2. *Backdated yang tetap pas di semua hari lanjutan* — **diizinkan (benar)**: `a3_backdated_fits` (baris 270-276) — 3 pcs hari ini + 5 pcs mundur 2 hari tetap ≤ sisa di semua hari; kasus `A3:BACKDATED_COMPLETE_FITS_LATER_DAYS_CONTROL` harus `PASS`.
3. *Qty nol/negatif* — **diblokir di validasi input** sebelum guard dated dievaluasi: regex `'^[1-9][0-9]{0,9}$'` (baris 384) menolak `0`/negatif/non-integer.
4. *Reversal lalu re-COMPLETE pada hari yang sama persis dengan qty penuh* — dicakup oleh kasus #1; timeline non-negatif dijamin oleh offset mikrodetik, bukan cuma urutan tanggal kalender.
5. *`expected_remaining` basi (stale) untuk memaksa race* — diblokir terpisah oleh `STALE_VERSION` (baris 355-356), bukan bagian A3 tapi mencegah TOCTOU pada `v_remaining` yang dipakai sebelum guard dated.
6. *Produk/brand berbeda dikombinasikan dengan tanggal untuk lolos guard A3* — tidak relevan, A3 dan A10 independen (predikat berbeda, keduanya dievaluasi berurutan: A3 baris 390-406 sebelum A10 baris 422-441).

**(d) Verdict: CLOSED.** Guard dated (bukan cuma "current remaining") diverifikasi lewat oracle independen `sewing_timeline` (`cp6_ba_probe.py:223-230`, agregasi `wip_stage_events` per waktu fisik) yang membuktikan timeline SEWING tidak pernah negatif — bukan cuma memeriksa kode error.

**(e) Resep**: `wip_batch(cur,today)` (`cp6_ba_probe.py:176-200`) — fixture 8 pcs SEWING teridentifikasi. `wip_output(cur,fx,day,qty,suffix)` (baris 209-213) memanggil `api.call(cur,'WIP_OUTPUT',dict(operation='COMPLETE',...))`. `wip_reverse(cur,fx,output)` (baris 216-220) memanggil `operation='REVERSE'`. Oracle: `sewing_timeline(cur,po)` (baris 223-230). NEGATIVE: output(day-3,8) lalu reverse lalu output(day-1,8) → harap `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING`. POSITIVE: output(day-1,3) lalu output(day-3,5) (pas di semua hari) → harap POSTED dan `sewing_minimum>=0`.

---

## A4 [CP6-03] — Recost sen penuh

**(a) Guard/logic**: `supabase/dev/cp6_ba_t1_family.sql:669-686` (cabang default, non-reversal non-return) dalam `erp.sync_material_cost_revaluation` (definisi baris 580). Cabang supplier-return (fix T2, `git show 35612d6`) di baris 663-668.

**(b) Predikat**: `v_now` = selisih nilai stok **dibulatkan** sebelum/sesudah movement (`material_cost_history`, baris 674-675). `v_posted` = kumulatif yang sudah diposting untuk dokumen sumber yang sama (`source_type`+`source_id`+`movement_type`) sampai movement ini, dibulatkan ke sen (baris 676-683). `v_target = v_now - sign(qty)*v_posted` (baris 684-685) — artinya movement yang mengosongkan stok mengambil **sisa* pembulatan, bukan pembulatan per-movement sendiri.

**(c) Percobaan bypass**:
1. *Kasus BLIND-MONEY-CENT (10.005↔10.014)* — diuji langsung: `a4_cents` (baris 456-496), 4 varian (DIRECT/INVOICE × UP/DOWN). Oracle independen: `MATERIAL_INVENTORY` harus 0 setelah cutting (`row['MATERIAL_INVENTORY']=amount if day<cutting_day else D('0.00')`, baris 487) — dihitung dari GL harian, bukan dari kode aplikasi. `raw_qty` harus 0 (baris 491, 494).
2. *Supplier return "mencuri" pembulatan sen* — inilah bug regresi T2 yang sudah diperbaiki: return sekarang **tidak** memakai cabang whole-cent (baris 663-668 dicek lebih dulu via `elsif r.source_type='MATERIAL_SUPPLIER_RETURN_ITEM'`), memakai formula AZ lama (delta cost langsung). Kontrol: `a4_supplier_return_control` (baris 499-527) — 3 retur split 1 unit @0.015, harap **0 revaluation events** dan inventory balik ke 0 tanpa recost tambahan.
3. *Material dengan beberapa retur/penerimaan sehingga residu ≤0.01 tetap ada* — **diakui eksplisit sebagai known limit** oleh writer (bukan diklaim tertutup); tidak ada bukti tandingan di probe untuk kasus multi-receipt residual. Status untuk sub-kasus ini: **tidak diklaim CLOSED oleh writer sendiri**, konsisten dengan deskripsi tugas.
4. *Reversal pada hari yang sama vs hari berbeda* — dicakup terpisah oleh cabang reversal (baris 642-662, logika AZ rev2.1, tidak diubah oleh A4); tidak bagian dari klaim A4.
5. *Write-off yang direversal (pocket-fabric)* — dicakup cabang berbeda (baris 727-770), juga bukan bagian klaim A4, tidak diverifikasi ulang di sini.

**(d) Verdict: CLOSED untuk kasus tunggal-terima yang diklaim** (satu unit diterima→dipotong→dikoreksi/diinvoice), dengan pengecualian residual multi-receipt yang **secara eksplisit diakui belum tertutup** oleh writer sendiri (bukan celah tersembunyi). Perbaikan regresi supplier-return (35612d6) sudah terintegrasi di dev file yang saya baca (baris 663-668) dan di release src (`git show 35612d6` menunjukkan diff identik di `supabase/release/cp6-t3-src/...`).

**(e) Resep**: `a4_cents(cur,today,kind,old,new)` (`cp6_ba_probe.py:456-496|kind∈{DIRECT,INVOICE}`). Fixture penerimaan: `azp.final_receipt(cur,day,qty=1,price=old)` (DIRECT) atau `estimated_one(cur,day,price)` (INVOICE, baris 439-453). Potong: `azp.cut(cur,fx,cutting_day,1)`. Koreksi langsung: insert `material_purchase_cost_corrections`+`post_material_purchase_cost_correction`. Invoice: RPC `erp.finalize_material_purchase_invoice_v2`. Oracle: `daily(cur,days)` (baris 431-436), kunci `MATERIAL_INVENTORY`/`WIP`/`AP_SUPPLIER`/`GRNI_MATERIAL`. NEGATIVE (harus 0 di endpoint): old=10.005,new=10.014 (dan sebaliknya). POSITIVE: `a4_supplier_return_control` — 3× retur split 1 unit @0.015 → 0 revaluation events.

---

## A6 [CP6-24] — Tutup periode dua kali

**(a) Guard**: `supabase/dev/cp6_ba_t1_family.sql:797-801`, dalam `erp.close_accounting_through` (definisi baris 781).

**(b) Predikat**: Setelah `select closed_through into v_old ... for update` (baris 793), jika `v_old is not null and p_closed_through=v_old` → `CLOSE_ALREADY_CLOSED` (baris 799-801). Kasus `p_closed_through<v_old` sudah ditangani terpisah di baris 794-796 (`raise exception ... gunakan reopen_accounting_through()`), jadi baris A6 murni menangani kasus **tanggal sama persis**.

**(c) Percobaan bypass**:
1. *Tutup ulang tanggal yang sama persis, tanpa reopen* — **diblokir**, `CLOSE_ALREADY_CLOSED`. Diverifikasi lewat oracle independen `filings(cur,day)` (baris 585-587, count di `accounting_close_filings_v1`) — harus tetap 1 setelah percobaan kedua (`a6_close`, baris 590-614, assert `after!=1 → FAIL` di baris 613, bukan cuma memeriksa kode error).
2. *Reopen lalu tutup ulang tanggal sama* — **diizinkan**, filing baru dibuat (`filings_before_second+1`, baris 609). Reopen dilakukan via RPC ordinary `erp.reopen_accounting_through` (baris 602), bukan lewat BA sendiri (BA tidak mengubah fungsi reopen).
3. *Race dua sesi menutup tanggal sama bersamaan* — dicegah oleh `for update` pada baris 793 sebelum pengecekan; sesi kedua akan menunggu, lalu membaca `v_old` yang sudah diperbarui sesi pertama → jatuh ke cabang A6. Tidak ada window TOCTOU yang terlihat pada source ini.
4. *Menutup tanggal earlier setelah tanggal later ditutup* (tanpa reopen) — ditangani jalur berbeda (baris 794-796, arahkan pakai `reopen_accounting_through`), bukan A6, tapi berdekatan dan konsisten.
5. *Alasan (`p_reason`) kosong/whitespace untuk memicu jalur berbeda* — diblokir lebih dulu (baris 792), tidak relevan sebagai bypass A6.

**(d) Verdict: CLOSED.** Predikat "tanggal sama = tolak, reopen membuka lagi" persis sesuai klaim; filing count diverifikasi lewat query independen, bukan status RPC saja.

**(e) Resep**: `a6_close(cur,today,reopen)` (`cp6_ba_probe.py:590-614`), pakai `awp.quiet_seed`, `awp.preflight`, `awp.close(cur,day,reason)` dari `cp6_aw_probe` (fungsi close-nya sendiri, dipanggil lewat RPC ordinary `close_accounting_through`). Oracle: `filings(cur,day)`. NEGATIVE: `reopen=False` → close dua kali tanggal sama → `CLOSE_ALREADY_CLOSED`, filing tetap 1. POSITIVE: `reopen=True` → `erp.reopen_accounting_through(day-1,...)` lalu close lagi → `ACCEPTED`, filing bertambah 1.

---

## A9 [CP6-07, D02] — Kapasitas advance bertanggal

**(a) Guard**: predikat di `erp.initial_prepayment_dated_floor_v1` (`cp6_ba_t1_family.sql:24-49`), dipakai oleh `erp.manage_initial_prepayment_v1` di baris 570-576 (raise `BA_ADVANCE_DATED_CAPACITY`).

**(b) Predikat**: `initial_prepayment_dated_floor_v1(advance_id, p_from)` menghitung **minimum** saldo advance pada `p_from` dan setiap hari sesudahnya yang punya pergerakan (event/pembayaran/reversal pembayaran), berdasarkan `economic_date` jurnal terkait (baris 42-47). Dipanggil setelah operasi (`APPLY`/`REFUND`/`CORRECT` turun/`REVERSE_EVENT` turun) di `v_date` efektif operasi tsb (baris 572-576); jika hasilnya `<0` → tolak. Berlaku untuk `SUPPLIER`/`CUSTOMER`/`VENDOR` (party_type generik, baris 42, 307-308 di probe) — mencakup opening balance, correction, reservation/allocation (via target `OPENING` subledger), refund, reversal (`REVERSE_EVENT` dengan `delta<0`, baris 572).

**(c) Percobaan bypass**:
1. *Refund/pakai tanggal tepat sama dengan tanggal correction yang mendanainya* — floor menghitung `day<=d.day` (baris 46 dalam floor function) dan operasi baru masuk sebagai `moves` pada `v_date`-nya sendiri; correction & use di hari yang sama → dievaluasi lewat GL cumulative pada hari itu, konsisten (tidak ada window negatif intra-hari karena keduanya sudah diposting sebelum guard dievaluasi ulang).
2. *Use/refund tanggal beberapa hari SEBELUM correction yang mendanainya (backdated), disubmit SESUDAH correction* — **diblokir**: `a9_advance(...,backdated=True)` (baris 353-371) — `correction_day=today-2`, `use_day=today-4` (use lebih awal dari correction) → harap `BA_ADVANCE_DATED_CAPACITY`. Oracle independen: `advance_asof(cur,fx,day)` (baris 345-350) membaca `account_daily_balances`, cek `any(v<0 for v in balances.values())`.
3. *Urutan benar (correction dulu, use belakangan)* — **diizinkan**: `backdated=False` (`correction_day=today-4`, `use_day=today-2`), kontrol `PASS`, saldo per-hari dicek sama persis dengan `expected` (baris 370).
4. *Alokasi yang membebaskan kapasitas (REVERSE_EVENT dengan delta<0 = pembatalan correction)* — turut dicek guard (baris 572: `(v_op in('CORRECT','REVERSE_EVENT') and v_delta<0)`), jadi pembatalan correction yang bisa membuat hari-hari lampau negatif juga diblokir, bukan cuma correction positif baru.
5. *Qty/amount nol atau negatif* — diblokir di validasi generik lebih dulu (`amount<=0` untuk non-CORRECT, baris 516; regex 2 desimal, baris 514).
6. *Tanggal sebelum cutover advance* — diblokir terpisah (`v_date<a.cutover_date`, baris 519), sebelum guard dated dievaluasi.
7. *Timezone string tanpa offset dikirim langsung ke RPC (bypass frontend)* — `effective_date` divalidasi dengan regex tanggal murni `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` (baris 517), bukan timestamptz — tidak ada celah offset di sini karena tidak ada komponen jam yang diproses sebagai wall-clock.
8. *Regresi kontrol AUD-S04 (stok, bukan advance, tapi didokumentasikan sebagai analog D02)* — `s04_transfer_back` (baris 395-419): transfer balik sebelum barang tiba diblokir oleh guard AM lama (`AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`), BA tidak menyentuhnya — dikonfirmasi tetap PASS di kedua fase (before/after).

**(d) Verdict: CLOSED** untuk tiga tipe party (SUPPLIER/CUSTOMER/VENDOR) × dua operasi (APPLY/REFUND) × ordered/backdated (8 kombinasi di `PLAN` baris 635-637), diverifikasi lewat oracle GL independen (`account_daily_balances`), bukan cuma kode error.

**(e) Resep**: `advance_fixture(cur,today,kind,target=False)` (`cp6_ba_probe.py:300-337`) — bank 100, advance 67.25 (100 asli, 32.75 terpakai sebelum cutover). `prepay(cur,fx,operation,**fields)` (baris 340-342) memanggil `api.call(cur,'PREPAYMENT',dict(operation=...))`. Oracle: `advance_asof(cur,fx,day)` (baris 345-350). NEGATIVE: `a9_advance(cur,today,'SUPPLIER','REFUND',backdated=True)` → `BA_ADVANCE_DATED_CAPACITY`. POSITIVE: `backdated=False` → POSTED, saldo per-hari cocok formula `67.25+(32.75 if day>=correction_day)-(100 if day>=use_day)`.

---

## A10 [CP6-18, D03] — Pengikatan produk output WIP

**(a) Guard**: `supabase/dev/cp6_ba_t1_family.sql:422-441`, dalam `erp.complete_initial_import_wip_v1`, dieksekusi setelah kandidat produk `v_product` ditentukan (baris 407-421) dan setelah guard A3 dated.

**(b) Predikat**: `v_bound:=coalesce(p.identity_root_id,p.id)` dari produk yang **diisi pada opening item** (`i.product_id`, baris 426). Jika `v_bound is not null` (opening WIP punya produk): output harus punya `identity_root_id` (atau id) yang sama persis → selain itu `BA_WIP_OUTPUT_PRODUCT_BOUND` (baris 427-430), `basis='OPENING_PRODUCT'`. Jika `v_bound is null` (tidak ada produk di opening): dicek brand/warna dari baris staging sumber (`migration_staging_rows.normalized_payload`, baris 433) — **hanya jika field itu terisi** (`nullif(btrim(...),'') is not null`, baris 435-436); field kosong/null di sumber **tidak pernah dianggap match** (`unknown` array, baris 460-461), sesuai instruksi "unknown data never counts as a match". Basis `SOURCE_ATTRIBUTES` jika ada brand/warna diverifikasi, `ASSIGNED_AT_COMPLETION` jika keduanya kosong (baris 439-440).

**(c) Percobaan bypass**:
1. *Produk terikat, coba selesai ke produk lain (brand lain, warna lain)* — **diblokir**, `BA_WIP_OUTPUT_PRODUCT_BOUND`. Diuji: `a10_output(c,t,True,True,'B',...)` (baris 279-295, kasus `A10:BOUND_PRODUCT_OUTPUT_OTHER_PRODUCT`).
2. *Tidak terikat produk, brand/warna source bertentangan dengan output* — **diblokir**, `BA_WIP_OUTPUT_SOURCE_MISMATCH` (kasus `A10:UNBOUND_SOURCE_BRAND_COLOR_MISMATCH`).
3. *Produk terikat tapi versi produk berbeda pada tanggal output (identity_root_id sama, row versi berbeda)* — **diizinkan secara benar** karena perbandingan pakai `identity_root_id` (baris 428, `coalesce(p.identity_root_id,p.id)`), bukan `product_id` mentah — varian efektif-tanggal dari identitas produk yang sama tetap dianggap "produk yang sama". Ini konsisten dengan komentar "the same product identity, i.e. its version on the output date" (baris 422-423) — perilaku yang benar, bukan celah.
4. *Produk aktif dicek di kandidat `v_product`, tapi bagaimana produk INAKTIF?* — kandidat `v_product` sendiri sudah difilter `p.is_active` di query pemilihan SKU (baris 412), jadi produk nonaktif tidak pernah jadi kandidat `v_product` untuk mulai — tidak relevan sebagai bypass A10 spesifik, tapi berarti tidak ada cara memasukkan produk nonaktif lewat SKU langsung.
5. *Brand/warna kosong string (bukan NULL) di payload staging, mis. `""` atau spasi* — ditangani sama seperti NULL lewat `nullif(btrim(...),'')` (baris 435, 439, 457, 460) — whitespace-only dianggap "unknown", bukan match kosong-vs-kosong yang salah dianggap cocok.
6. *Casing brand_code berbeda* (`ABC` vs `abc`) — dibandingkan via `lower(btrim(b.brand_code))<>lower(btrim(v_src->>'brand_code'))` (baris 435) — **case-insensitive by design**, casing tidak bisa dipakai untuk memalsukan mismatch/match.
7. *Tidak ada produk DAN tidak ada brand/warna di source (assigned-at-completion), lalu output ke produk manapun yang match model+size* — **diizinkan** (basis `ASSIGNED_AT_COMPLETION`), sesuai desain: hanya PO model & size yang mengikat (dicek lebih awal di query kandidat, baris 407-419), bukan bagian klaim A10 untuk dibatasi lebih jauh.
8. *Product_sku dengan whitespace/casing beda saat memilih kandidat awal* — kandidat `v_product` sendiri sudah `lower(btrim(p.sku))=lower(btrim(p_payload->>'product_sku'))` (baris 411) — case/whitespace-insensitive, konsisten.

**(d) Verdict: CLOSED.** Kedua guard (`PRODUCT_BOUND`, `SOURCE_MISMATCH`) dan pencatatan provenance (`initial_import_wip_output_identity_v1`, tabel baru baris 10-23) diverifikasi lewat oracle independen `identity(cur,output_id)` (`cp6_ba_probe.py:233-237`) yang membandingkan `(basis, checked, unknown)` persis terhadap tabel ekspektasi `expected` (baris 289-291) untuk 3 kombinasi (product+attrs, no-product+attrs, no-product+no-attrs) — bukan cuma memeriksa kode error refusal.

**(e) Resep**: `wip_batch(cur,today,product,attributes)` (baris 176-200) — flag `product`/`attributes` mengontrol apakah opening item WIP punya `product_sku`/`brand_code`+`color_name`. `wip_output(cur,fx,day,qty,suffix)` memanggil produk `fx['code']+suffix` (A=match, B=mismatch). Oracle: `identity(cur,output_id)` baca tabel `erp.initial_import_wip_output_identity_v1`. NEGATIVE: `a10_output(c,t,True,True,'B','BA_WIP_OUTPUT_PRODUCT_BOUND')` dan `a10_output(c,t,False,True,'B','BA_WIP_OUTPUT_SOURCE_MISMATCH')`. POSITIVE: `a10_output(c,t,True,True,'A')`, `(False,True,'A')`, `(False,False,'A')` — ketiganya harus POSTED dengan record identity sesuai basis yang diharapkan.

---

## A2 [CP6-01] — Waktu fisik dikirim sebagai WIB wall clock

**(a) Lokasi**: `src/cp6BusinessTime.ts:17-27` (`cp6WibPhysicalTimeToIso`, sudah ada sebelum BA) + fungsi baru `cp6WibDateTimeInput` (`src/cp6BusinessTime.ts:29-37`, `git diff 9add57e a095a9d`). Dipakai di `src/ConnectedCuttingPage.tsx` (import baris 19; pakai di baris ~79, 182, 252, `cutAtIso` baris 168-169, kirim `cut_at: cutAtIso` baris 272), `src/ConnectedPickupPage.tsx` (import baris 24; `pickedUpAtIso` baris 123, kirim `picked_up_at: pickedUpAtIso` baris 200), `src/ConnectedBsResolutionPage.tsx` (`toIso`/`validTime` baris 37-40, dipakai di 6 titik waktu fisik: HOLD baris 288, Rework/Rewash kirim baris 291-315, Rework completion baris 234-244, Manual BS baris 69, Claim `openedAt` baris 121).

**(b) Predikat**: sebelum fix, `datetimeLocal`/`nowInput`/`toIso` memakai `date.getTimezoneOffset()` device lokal (`new Date(date.getTime() - date.getTimezoneOffset()*60_000)`) untuk **tampilan**, lalu `new Date(cutAt).toISOString()` untuk **kirim** — ini mem-parse string `datetime-local` (tanpa offset) sebagai *waktu lokal browser*, bukan WIB. Sesudah fix: tampilan pakai `cp6WibDateTimeInput()` (instant + 7 jam lalu slice UTC — matematis identik dengan wall-clock WIB, independen zona device), kirim pakai `cp6WibPhysicalTimeToIso()` yang secara eksplisit menempelkan `+07:00` sebelum parse (`cp6BusinessTime.ts:25`).

**(c) Percobaan bypass**:
1. *Device timezone UTC, Asia/Makassar, Pacific/Kiritimati (UTC+14)* — **ditest langsung** oleh writer: `src/ConnectedBsResolutionPage.dom.test.tsx` (diff, `it.each(['Asia/Jakarta','Asia/Makassar','UTC','Pacific/Kiritimati'])`) memasukkan `2026-09-20T00:30` dan memverifikasi payload RPC persis `physical_at: '2026-09-19T17:30:00.000Z'` (= 2026-09-20T00:30 WIB) di keempat zona — **lolos di semua zona**, membuktikan hasil tidak bergantung `process.env.TZ`.
2. *Value kosong* — `cp6WibPhysicalTimeToIso('')` tidak match regex → `null` → tombol submit disabled (`validTime`), diuji eksplisit ("keeps HOLD disabled for an empty physical time instead of throwing").
3. *String datetime dengan offset eksplisit dikirim manual ke fungsi* (mis. `"2026-09-20T00:30+07:00"`) — regex `localDateTimePattern` (`cp6BusinessTime.ts:6`) di-anchor `^...$` dan **tidak mengizinkan** suffix offset → `null` → dianggap invalid. Ini aman untuk UI (`datetime-local` HTML input tidak pernah menghasilkan string berofset), tapi berarti fungsi ini murni pelindung sisi klien.
4. *Bypass frontend sepenuhnya, panggil RPC langsung (curl/Postman) dengan string tanpa offset* — **di luar cakupan fix A2**: fix ini hanya memperbaiki apa yang dikirim oleh 3 halaman React; tidak ada bukti di source yang ditinjau bahwa RPC backend (mis. `erp_cutting_group_action_v1`/pickup/BS action) memvalidasi format/offset `physical_at` yang diterimanya — Postgres akan menerima string timestamptz apa pun formatnya dan menafsirkan sesuai aturan standarnya. Ini bukan regresi dari BA (perilaku lama sama saja), tapi berarti proteksi "WIB wall clock" hanya berlaku selama jalur UI dipakai.

**(d) Verdict: CLOSED untuk klaim yang diajukan** (3 halaman: Cutting, Pickup, BS Resolution, multi-input) — diverifikasi lintas 4 zona waktu device secara eksplisit oleh test milik writer, bukan observasi tunggal. **Catatan batas**: perlindungan murni di sisi klien; validasi format di sisi server untuk `physical_at` tidak diverifikasi dalam review ini (tidak diklaim oleh A2, dicatat sebagai batas cakupan).

**(e) Resep audit independen**: render halaman dengan `mockedClient.rpc` yang menangkap payload, set `process.env.TZ` ke beberapa zona (termasuk UTC+14 dan UTC-12 untuk margin maksimum), isi input `datetime-local` dengan nilai tetap, submit, dan assert `physical_at`/`cut_at`/`picked_up_at` yang dikirim ke RPC **sama persis** di semua zona dan sama dengan `<tanggal>T<jam>:00.000Z` minus 7 jam dari nilai WIB yang diketik.

---

## Perilaku baru di luar klaim yang diminta

1. **A5 [CP6-04]**, disebutkan di komentar kode (`cp6_ba_t1_family.sql:1293-1295, 1299`) dan diimplementasikan penuh (backend: daftar batch draft tidak lagi dipotong, `get_initial_import_workspace_v1`; frontend: kotak cari di `ConnectedInitialImportPage.tsx` dan `ConnectedBsResolutionPage.tsx` untuk >20/>50 baris) — **tidak diminta ditinjau** oleh instruksi tugas ini, tapi merupakan perubahan perilaku publik nyata (selector laundry sources & import drafts). Dicatat, tidak diverifikasi mendalam di sini.
2. **Tabel baru**: `erp.initial_import_wip_output_identity_v1` (baris 10-23) — RLS **enabled**, dan **semua grant di-revoke** dari `public,anon,authenticated,service_role` (baris 23) — akses hanya lewat fungsi `SECURITY DEFINER`. Tidak ada kebijakan RLS (`create policy`) ditambahkan — dengan grant kosong dan RLS on, tabel efektif tidak bisa diakses langsung oleh peran mana pun kecuali superuser/pemilik, konsisten dengan pola "derived, internal-only" yang dideskripsikan di `assert_new_stock_cutoff_coverage_v1` (baris 836, entri untuk kolom `product_id` tabel ini berclass `DERIVED`).
3. **Grant/fungsi publik**: tidak ada `GRANT` baru sama sekali di seluruh file (`grep '^GRANT\|^grant'` kosong); 8 fungsi **REPLACE** (bukan baru secara nama), 1 fungsi baru (`erp.initial_prepayment_dated_floor_v1`, di-revoke dari semua peran publik, baris 50) — dikonfirmasi silang dengan `REPLACED`/`NEW_FUNCTIONS`/`NEW_TABLES` di `scripts/cp6_ba_build.py:357-361`.
4. Perubahan pada `erp.assert_new_stock_cutoff_coverage_v1` (baris 829-881) menambahkan registry entry untuk 2 kolom baru (`opening_product_id`, `output_product_id` di tabel baru) — bagian mekanis wajar dari penambahan tabel produk-terkait, bukan perilaku bisnis baru.

---

## Idempoten / rollback-safe

Diperiksa lewat `supabase/release/cp6-t3/MANIFEST.json`, entri `key:"BA"`. File aktual **tidak ada** di `supabase/migrations/`; hanya ada di `supabase/release/cp6-t3-src/` (source, hash `3c10c1c5...`) dan `supabase/release/cp6-t3/` (final, hash package `135facce...`) plus rollback capsule di `supabase/release/cp6-t3-rollbacks/20260925010000_..._ba_....rollback.sql`.

Guard idempoten di source (`cp6-t3-src/...ba....sql:24-27`): `BA_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED` menolak instalasi jika `erp.schema_migrations` sudah punya `v2.6.20ba` **atau** `erp.initial_import_wip_output_identity_v1` sudah ada — ini adalah proteksi re-run yang benar (tidak bisa dijalankan dua kali). Guard `BA_EXACT_PREDECESSOR_REQUIRED` (baris 29-31) menolak jika ada migrasi lebih baru dari `20260924010300` — memaksa posisi tepat di rantai. Guard `closed_admission` (baris 6-14) mewajibkan database drained (tanpa koneksi lain) sebelum jalan — konsisten dengan paket T3 sebelumnya.

Namun **catatan status**: `source_sha256`/`package_sha256` di `MANIFEST.json` untuk BA sudah terisi (bukan placeholder nol), tapi hash antar-predecessor yang **dirujuk dari dalam** file BA sendiri (`jsonb_to_recordset` di baris ~35 dan `jsonb_each_text` di baris ~114/1535 dari release src) masih berisi banyak nilai **placeholder nol** (`"0000...0000"`) untuk `cp6_v2620ao`..`az_rollback_capsule` dan untuk `object_count<>0`/`fingerprint is distinct from '000...'` di catalog guard — dikonfirmasi lewat `diff` `cp6-t3` vs `cp6-t3-src` di atas: versi `cp6-t3-src` memang berisi placeholder nol (belum di-capture), sedangkan versi final `cp6-t3` sudah diisi hash asli. Ini **konsisten dengan proses build normal** (`src` = sebelum capture, final = sesudah), bukan cacat — tapi berarti file `-src` sendirian **tidak** boleh dijalankan langsung terhadap produksi (guard-nya akan selalu gagal/placeholder), hanya versi final `supabase/release/cp6-t3/...` yang siap pakai. Rollback capsule terpisah ada di `cp6-t3-rollbacks/`, tidak diperiksa isinya secara mendalam (di luar cakupan waktu review ini).

**Kesimpulan idempoten**: guard re-run & predecessor-exact **ada dan cukup ketat** (menolak instal ganda dan instal di luar urutan rantai persis) — desain rollback-safe standar family CP6 (identik pola dengan AW-AZ sebelumnya), tidak ada yang mencurigakan spesifik untuk BA.

---

## Ringkasan verdict

- A1 [CP6-09]: **PARTIAL** — identitas material/FG/WIP/BS/cash-per-id tertutup rapat untuk impor-vs-impor; celah residual: legacy-vs-legacy tak dicek (di luar klaim), dan identitas `CASH_BANK` berbasis `cash_account_id` bukan `coa_account_id` (tak terverifikasi aman).
- A3 [CP6-02]: **CLOSED** — dated-remaining diverifikasi lewat oracle timeline independen, termasuk kasus tepat-hari-reversal dan backdated-yang-pas.
- A4 [CP6-03]: **CLOSED** untuk kasus tunggal yang diklaim (endpoint 0 di stok kosong); residu multi-receipt **diakui terbuka oleh writer sendiri**, bukan disembunyikan; regresi T2 supplier-return sudah terintegrasi.
- A6 [CP6-24]: **CLOSED** — filing count diverifikasi via query independen, reopen-lalu-close tetap berjalan.
- A9 [CP6-07/D02]: **CLOSED** — 8 kombinasi party×operasi×ordered/backdated diverifikasi via saldo GL harian independen.
- A10 [CP6-18/D03]: **CLOSED** — kedua guard plus tabel provenance diverifikasi field-per-field terhadap tabel ekspektasi, termasuk kasus whitespace/casing/kosong.
- A2 [CP6-01]: **CLOSED** untuk 3 halaman yang diklaim, diuji lintas 4 zona waktu device; batas cakupan: tidak menjamin validasi format di sisi server bila RPC dipanggil di luar UI.
