# Oracle, bukti lintas CP, dan definisi selesai

> **Revisi2 aktif:** baca `06_RUSUK_KEBUTUHAN_OWNER.md` terlebih dahulu. Kontrak AnalysisResult v2 menggantikan bentuk v1; pin/head dan receipt v1 di bab ini adalah sejarah persiapan, bukan accepted base. WA readiness dibawa ke CP7; aktivasi live tetap punya gate tersendiri.

Semua angka di sini **fixture sintetis**, bukan data/tarif/kebijakan pabrik. Expected dihitung dari kontrak dan aritmetika yang bisa diperiksa. Penyusunan paket hanya memvalidasi dokumen/vektor; semua pengujian ERP CP7 berstatus NOT_RUN. Kode runtime nanti harus membuktikan expected melalui jalur sah.

## 1. Golden vectors yang sudah berisi angka

| ID | Input | Expected yang tidak boleh bergeser |
|---|---|---|
| O01 | FG18; target48; directed12 on time; allocated candidate10 | Q_base18, Q_conditional8; FG tetap18; candidate label bersyarat |
| O02 | Demand4/hari; L7,R3,B2; FG18; directed12 hari3; candidate10 hari6; new8 hari7 | Target48; demand horizon10hari40; buffer akhir8. End balance:14,10,18,14,10,16,20,16,12,8 |
| O03 | O02 tetapi directed12 pindah dari hari3 ke8 | End14,10,6,2,−2,4,8,16,12,8; gap awal hari5=2 masih ada meski akhir8. Mode BACKLOG diberi label |
| O04 | GapA42+B30; satu kandidat60 size compatible | AllocateA42+B18=60; gapB12. FilterA tidak memberi60 baru; alternatif tanpa kandidat72 tidak dijumlah dengan12 |
| O05 | Target100; FG10; directed laundry60 tepat waktu; kandidat40 | Base30; jika kandidat terkonfirmasi minimal 30 tepat waktu maka tambahan0. Tidak menyebut FG menjadi110 |
| O06 | FG100; draft sale24; residual future demand20 | Available76; projected56; draft→posted tetap56; cancel draft mengembalikan sesuai source, bukan posting dua kali |
| O07 | Kebutuhan sizeS10/L20; FG S25/L5 | S surplus15, L gap15, totalSKU30 tidak menghapus kekuranganL |
| O08 | Net need8; explicit fixture batch multiple12 | Suggested12, rounding extra4; exact size distribution harus feasible. Tanpa policy multiple12 tidak dipaksakan |
| O09 | BOM need100; installed60 proven; unused allocated20 eligible | Not installed40; external additional20. Hanya issue80 tanpa linkage → UNKNOWN, bukan20 |
| O10 | Gap100; material/capacity hanya60 | Needed100, feasible60, unresolved40; tidak menulis shortage60 atau schedule pasti |
| O11 | 14 hari tersedia, sales140; 14 hari stockout | Naive calendar rate5; availability-conditioned10 dengan label asumsi keterwakilan. Lost sales140 tidak diklaim sebagai fakta |
| O12 | Valid sales observations 0,10,0; dua hari lain unknown | Observed periods3, total10, conditional mean10/3; unknown tidak menjadi dua zero tambahan. Rate hasil tetap berlabel sesuai sampling |
| O13 | Revenue1000→1200; margin27%→24%; baseline growth0 | Growth20%; margin change−3pp; growth atas baseline0=N/A, bukan0%/infinite |
| O14 | Internal cash transfer1000, customer receipt300, supplier payment200 | Total cash net+100; transfer net0, revenue tidak disimpulkan300 |
| O15 | Parent100; childA60,childB40. A: sewing20,outstanding10,awaitQC10,FG15,BS5; B: WIP40 | Total WIP80, FG15,BS5=100. DO40+receipt30+QC20+FG15 tidak dijumlah sebagai85 supply |
| O16 | Scenario SOURCE40, capacity36; Aneed30,Bneed30; A prioritas lebih tinggi | A30,B6; unresolvedB24; source unused4. Conditional feasible36, bukan total60 tertutup |
| O17 | SKU STOP, target100, FG10, directed20 | Gap70 tetap terlihat; start_new0; WIP20 tetap harus ditinjau. Sibling brand unaffected |
| O18 | BE pocket fixture denominator10 WIP5/FG3/sold2; cost11.25→15 | Existing expected awal5.62/3.38/2.25; corrected7.50/4.50/3.00. Stock issue tidak terulang; expense direklasifikasi. Mengikuti rounding native, bukan formula round bebas |
| O19 | FG unknown; target48; directed12 | Actual recommendation UNKNOWN/DATA_BELUM_CUKUP. Simulasi FG0 boleh separate dan labeled; bukan actual36 |
| O20 | Nilai forecast horizon constant training, actual all0 | MASE denominator0=N/A; MAE0 jika forecast0. Tidak crash, NaN, atau menganggap akurasi pasti |

O02/O03 berasal dari keluarga BR-T04/T05; O04 dari UX32/WIP-T02; O18 diwarisi exact expected BE, bukan hasil test CP7 baru. Fixture machine-readable memisahkan stage facts dari presentation, mode backlog dan asal policy.

## 2. Invariant yang diuji dari dua arah

- **Conservation:** sum physical positions+terminal outcomes sesuai source lineage; tambah movement tahap tanpa sumber baru tidak menambah supply. Pecah sumber menjadi child setara tidak mengubah total quantity/value.
- **Idempotence:** rerun read/calculation dari snapshot sama menghasilkan semantic hash sama; repeat command key/payload sama satu effect; key sama payload beda atomically rejected.
- **Permutation/pagination invariance:** urutan ingestion atau page size tidak mengubah hasil jika chronology/domain order tetap sama. Sorting bisnis dengan prioritas sah tidak boleh dipermutasi dalam canonical hash.
- **Temporal non-leakage:** menambah fakta `known_at` setelah cutoff tidak mengubah run as-known lama. Restated current boleh berubah dengan revision berbeda.
- **Late-supply rule:** memundurkan supply tidak memperbaiki gap sebelum arrival baru; shortage size lain tidak hilang karena surplus size yang tak dapat dikonversi.
- **Monotonicity yang terbatas:** tambah FG eligible pada size sama, policy/sumber/constraint tetap → raw net need tidak bertambah. Jangan memaksakan monotonicity ke ranking/rounding/capacity/model selection yang bisa berubah karena policy.
- **Permission noninterference:** data scope lain tidak muncul dalam payload, totals, prompt, cache atau reasons. Global constraints tetap diperiksa; response terbatas bisa menjadi unavailable-for-scope.
- **Financial separation:** perubahan payment tidak menciptakan work entitlement/HPP lagi; perubahan cost certainty nol rupiah tetap mengubah readiness bila kontrak menyatakan demikian.
- **No business side effects:** read/compute/filter/report/ACK/export before-after compare **seluruh operational tables dan relevant sequences/events**, dengan allowance tepat pada analysis/attention metadata; tidak cuma saldo akhir.

## 3. Alur end-to-end yang wajib benar-benar dijalankan

| ID | Cerita pabrik / titik pemeriksaan | Jembatan CP | Minimal evidence |
|---|---|---|---|
| E01 | Opening sah → receipt material → cutting → pickup → sewing → laundry partial → QC/FG per size → sales draft/post → payment → report | ALL/CP5/CP6→CP7 | Native reconciliation di setiap boundary; satu browser journey real Auth |
| E02 | Dua child dari parent; laundry partial, stuck/missing claim, susulan, BS/rework/rewash, partial QC | CP5/6→WIP | Parent/child/counter conservation, stage timestamps, no duplicate incoming |
| E03 | FG → sales return partial → customer service → accessory use → returned good/BS → refund | Sales/ACC/finance | Ownership, custody, inventory, AR/refund terpisah; no fake company FG/customer entitlement |
| E04 | Ganti merek/rework SKU baru/redye → sold child → supplier/vendor invoice correction | BE/BD→cost/report | Source cost transitive ke FG/COGS; no labor/BOM/qty double; zero delta certainty |
| E05 | Payroll attendance APPROVED → paid partial/full; accessory deduction/advance; reverse | CP3/ACC/finance | Expense once, denominator immutable, remaining entitlement/cash conserved |
| E06 | Fisik akhir Desember, invoice tiga bulan kemudian, recost pending/final, historical report, close | D01/AW/BD/BR | Physical/economic/accounting/known separate; as-known archive unchanged; close race guarded |
| E07 | Historical pocket import + native/Afui result → allocation → sale/return/conversion → invoice delta | ALL-C04/BE→HPP/BR | Exact source roundoff, expense reclass, no phantom sewing/material movement |
| E08 | Stok → Planner → panel Potongan → BR → Reminder → V1 pada run/scope/scenario sama | Seluruh consumer | Operand/reason/status parity; actions unique; no hidden formula |
| E09 | Report lama dibuka setelah source/policy/calendar/permission berubah | Snapshot/Auth | Stale/denied tepat; archived/current distinguished; apply revalidates |
| E10 | Dua browser apply source sama, key sama/different payload dan draft berbeda | Scenario/domain | One authorized source consumption; loser stale/refusal, no orphan |
| E11 | Dua run berbeda sama-sama usulkan produksi baru untuk gap sama | Planner→cutting | Target/dependency conflict and linked intent; no duplicate plan-induced start |
| E12 | Commit sukses balasan hilang; reload; dari tab lain coba Laundry/QC/sales pada source terkait | Recovery/CP5/6 | Request envelope stable, source fence, same replay, no false failure/new UUID |
| E13 | POSTED immutable; reversal/late correction sesudah penggunaan turunannya | Semua ledger | Linked facts, exact inverse atau lawful refusal; no deletes/overwrites |
| E14 | Role null/inactive/revoked; viewer; cross-location/source; authenticated browser and raw HTTP | Auth/CP4.5 | Server rejection, data no leak, state before-after exact; no service-role shortcut |
| E15 | Query source timeout/partial page/malformed/conflict; good qty bad cost | Readers/BR | Domain partial honest, no seeded fallback or false zero/READY |
| E16 | Report publish doubleclick/retry, concurrent current pointer, later revision | BR/storage | Same request replay, unique revision/current, original immutable |
| E17 | Manual reminder edit/DONE/CANCELLED+reload; automated condition ACK/snooze/recover/recur | Reminder | Persistence, episode once, attention≠source resolved, no real delivery |
| E18 | Clipboard denied/pop-up blocked/ChatGPT offline; malicious-looking source note | V1/UI | Manual fallback, successful copy message honest, escaped text, no URL data/AI call |
| E19 | UI desktop/HP/iPad keyboard/touch; dirty cutting form; detail-back/filter/ranking stale | UX32 | Real screen/interaction no lost input, scroll/filter stable, no nested modal trap |
| E20 | Large source spanning multiple pages; one candidate shared across visible/hidden scope | Completeness/perf/Auth | Full aggregates, capacity conserved, redaction, bounded query/run |
| E21 | Upgrade from qualified base → T2 on installed candidate → rollback pre-use → reinstall → post-use refusal → restore | CP2/CP7→CP7.5 | Catalog/data/ACL/history/markers match required level, unchanged primary, cleanup receipt |
| E22 | Read/compute/export/ACK over whole fixture with poisoned mutator privilege controls | Analysis separation | No operational table/counter change; compute principal cannot invoke writers |
| E23 | New/paused/stopped/active status bulk by brand/range; past review date; stale draft | Master/Planner | No auto-reactivate/cancel-existing; authorized action only; atomic multi-row version check |
| E24 | Receipt/warehouse transfer/inactive location/backdated prefix; late price and source return | Procurement/CP6 | Exact qty/value, complete server list, no false average/stock, branch/source correct |

Setiap journey mencatat checkpoints domain, tidak cuma halaman tampil. E01 dapat membuktikan beberapa requirement; dicatat sebagai satu eksekusi dengan mapping, bukan digandakan menjadi puluhan test count.

### Worksheet E01/E03: satu produksi sampai penjualan dan retur

Fixture qualification lebih dahulu menetapkan satu brand/size, seluruh 60 PCS GOOD, tanpa yield loss, kurs/pajak/diskon, serta sumber biaya sah: raw600, sewing120, aksesori60, laundry120. Total900, HPP15/PCS. Angka adalah konfigurasi disposable yang harus didukung domain existing; setup ditolak jika source/entitlement tidak bisa dibentuk secara sah. Jangan mengisi hasil HPP langsung di tabel atau mengganti expected agar cocok dengan kode.

| Checkpoint | Jumlah dan nilai yang diperiksa |
|---|---|
| Receipt dan cutting | Raw100 unit×10=1000; konsumsi60 unit=600; raw sisa40 unit bernilai400. Konversi yield fixture60 PCS valid dan tercatat |
| Sewing/laundry/QC partial | Dua leg30+30 dan QC20+40; jumlah yang sama berpindah tahap, total output60. Biaya sumber lain300 diakui sesuai tahap/kontrak, tidak diulang saat invoice/payment |
| Semua FG | FG60 bernilai900; WIP fisik produksi itu0; HPP15/PCS; source biaya600+120+60+120=900 |
| Draft sale20 | Availability FG40; tidak dipotong20 lagi ketika menjadi posted. Timing GL sementara mengikuti domain accepted, bukan diasumsikan oleh UI |
| Posted sale20 pada 25/PCS | Net sales sebelum return500; final COGS300; FG40 bernilai600. Financial readiness harus final atau tampil pending yang menahan claim ini |
| Customer payment200 | Cash+200, AR300; omzet tetap500; COGS tetap300; payment tidak mengubah stock/HPP |
| Return5 eligible GOOD pada harga asal, credit applied ke AR | FG45 bernilai675; COGS net225; revenue net375; AR175; cash tetap200. 200+175=375. Return yang sama diulang tidak memberi5 lagi |

Cabang E03 customer-owned service/refund memakai fixture sumber sendiri. Jangan menganggap barang pelanggan menjadi company FG, atau memaksa refund uang jika transaksi hanya menimbulkan pengurangan piutang dan belum memiliki refundable credit yang sah. Setelah final flow, report dan source detail harus menjelaskan375 revenue,225 COGS,150 gross profit dari operand yang sama; bukan menghitung margin dari cash200.

## 4. Model evaluation scenarios

| ID | Skenario | Expected |
|---|---|---|
| M01 | Histori pendek terhadap H; beberapa unknown days | Eligibility menolak model yang tidak punya fold valid; fallback beserta alasan |
| M02 | Mean/SES/Holt/SBA/TSB menerima prefix training sama | Predictions finite/nonnegative dengan parameter/domain bounds; zero updates sesuai availability |
| M03 | Future rows dan backdated-known-later ditambah ke dataset | Predictions/model choice pada cutoff lama identik; input immutable |
| M04 | Challenger lebih baik validasi tetapi kalah outer holdout | Laporan menunjukkan keduanya; holdout tidak dipakai retune agar tampak menang |
| M05 | Baseline tie/lebih baik, seasonal data tidak cukup siklus | Baseline dipertahankan; no invented season or fake calibrated confidence |
| M06 | Buffer hari versus statistical target, quantiles with proper horizon | Satu mode aktif; forecast/service/WIP confidence tidak dicampur |
| M07 | Kalender/lead time/yield berubah, capacities unknown/overload | New version/stale, ETA assumption label, no unsupported feasibility |
| M08 | Plan version dibanding actual setelah partial/reversal/late entry | Comparison attributable to plan version; future knowledge tidak dipakai menilai keputusan awal sebagai pasti salah |

## 5. Fixture qualification dan oracle independence

Fixture valid harus punya actor role aktif, sumber benar, chronology masuk scope, window close benar, version/policy tepat, request ID unik per intent, lineage dan UOM sah. Setup writes dihitung; baseline catalog tidak boleh berubah karena grant fixture yang lupa dicabut. Clone berisi seed tidak diseed ulang tanpa precondition yang benar.

Expected datang dari kontrak/numeric ledger worksheet, bukan memanggil helper produksi lalu membandingkan helper itu dengan dirinya sendiri. Regression fix membutuhkan failure pada predecessor atau mutant yang representatif. Fitur baru yang memang tidak punya route before diberi NO_ROUTE/NOT_APPLICABLE sesuai charter; itu bukan bukti counterexample bisnis predecessor.

Verifier memisahkan setup failure dari product failure. Screenshot/DOM dengan mocked RPC membuktikan interaksi saja; hosted/disposable Auth+HTTP+native source mempunyai evidence berbeda. Review code bukan runtime audit. Native auditor yang tidak bisa menjalankan satu kasus pun harus berkata INCOMPLETE.

## 6. Coverage dan ledger status

Registry menjaga **35 CP7 +40 BR +12 WIP +12 UX32 +36 RMD**, lalu audit33, ACC39, LAU36, CROSS6 dan ALL22 sebagai kewajiban warisan/interkoneksi. Banyak overlap; angka itu kelompok requirement, bukan jumlah test baru. Setelah generator dijalankan, angka aktual hasil parsing ada di validation report. Tidak menjumlahnya menjadi klaim 271 tes lulus.

Status per requirement: NOT_RUN (CP7), UPSTREAM_ACCEPTANCE_PENDING (CP6), FUTURE_CP7C (seam diuji sekarang), OPTIONAL_NOT_SELECTED, atau WRITER_VERIFIED/INDEPENDENT_ACCEPTED setelah bukti nyata. Hasil case: PASS/CONTROL_PASS/COUNTEREXAMPLE/FAIL/INCOMPLETE/BLOCKED/POLICY_BLOCKED/NOT_APPLICABLE dengan alasan. Status CI success dan result per case wajib dibaca bersama.

CP6 yang masih HOLD tetap dilaporkan terpisah. T2 BE memiliki historical dispositions; original results tidak diubah jadi PASS. Saat CP6 diterima, P00 mengimpor keputusan per-ID dengan source acceptance; tidak menghapus 12 HOLD hanya karena nama phase sudah CP7.

## 7. Definition of done per feature

Satu feature selesai bila memiliki input authoritative dan lengkap, source/provenance/quality, behavior business dan permission server, entry UI connected, failure/replay/stale yang jujur, test positive/negative/cross-domain sesuai risikonya, serta source-bound evidence yang dapat dijalankan ulang. Tidak cukup karena code compile atau route ada.

CP7 kandidat siap acceptance bila seluruh mandatory rows CP7 selesai dengan bukti, conditional capabilities mempunyai valid+unknown path, optional/future dipisah tanpa menghapus kewajiban, semua interkoneksi E01–E24 relevan teruji, dan tidak ada confirmed material correctness/security defect atau required INCOMPLETE yang ditutupi.

Independent acceptance membutuhkan auditor terpisah atas exact candidate/runtime; full dummy flow dan financial reconciliation tidak digantikan writer claim. Rilis membutuhkan T3. Production GO tetap owner pada checkpoint/cutover yang benar. Tidak ada jaminan software sempurna; yang diberikan adalah definisi terukur yang mencegah “kelihatan jalan” disebut selesai.

## Delta kasus revisi2

32 kasus X01–X32 ditambahkan pada registries/cases.json, menjadi84 kontrak kasus NOT_RUN. Sepuluh OWN28 adalah kelompok kebutuhan owner yang beririsan dengan271 kelompok lama; jangan menjumlahnya sebagai281 kebutuhan unik atau84 tes lulus. Pemeriksaan offline revisi dilaporkan tersendiri.
