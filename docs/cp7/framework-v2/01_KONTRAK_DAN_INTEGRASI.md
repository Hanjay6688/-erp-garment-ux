# Kontrak, batas, dan sambungan CP7

> **Revisi2 aktif:** baca `06_RUSUK_KEBUTUHAN_OWNER.md` terlebih dahulu. Kontrak AnalysisResult v2 menggantikan bentuk v1; pin/head dan receipt v1 di bab ini adalah sejarah persiapan, bukan accepted base. WA readiness dibawa ke CP7; aktivasi live tetap punya gate tersendiri.

## 1. Otoritas dan cara menangani perubahan

Urutan yang dipakai: instruksi owner paling baru → addendum keputusan yang disahkan beserta errata → Master Pulih M/P dengan revisi scope BR V3.1 dan UX32 → kontrak CP7 rev3 → rancangan teknis dalam paket ini. Source membuktikan apa yang tertulis/terpasang, bukan mengganti keinginan bisnis. Bukti runtime hanya berlaku pada versi dan lingkungan yang dicatat.

| Sumber | Isi yang mengikat | Cara memakai |
|---|---|---|
| M: `ERP_V3_2_Master_Pulih_20260923.md` | Seluruh master, BR V3.1, UX32, WIP, Reminder, arsip audit dan CP7 rev3 | Pakai bagian aktif; status AQ di awal adalah historis, telah dilampaui handoff BE |
| P: `ERP_V3_2_Perubahan_Pulih_20260923.md` | Riwayat perubahan dan keputusan | Rujukan asal; jangan menghidupkan kembali status superseded |
| CP7 rev3, 10 Sep | A–G dan 35 acceptance, adaptive, WIP sebelum SKU, V1 | Semua dipetakan, tidak diperkecil menjadi low-stock alert |
| BR V3.1, di M §BR.0.1 | Mandat BR inti, conditional capabilities, batas optional | Mengoreksi perluasan scope pada addendum BR V3 asli |
| UX32, di M | Ranking tindakan, grouping WIP/pola/material, UI desktop/HP/iPad | Bukan formula baru; 12 cross-check memetakan acceptance lama |
| Addendum CP6 25 Sep dan C6 rev4 | D01–D06, ALL22/ACC39/LAU36 dan CR masuk CP6 | Scope CP6 tidak dilempar ke CP7. Nilai policy pending tidak dijadikan nol |
| Handoff Claude/GPT §15.4, §18, §19; paket A+B 23 Sep | Counterexample, fixture sesuai klaim, bukti proporsional, rilis gabungan | Draft A+B bukan otoritas untuk mengembalikan formula AX lama atau status lama |
| Handoff BE 27–28 Sep | Titik produk terbaru dan disposisi T2 | Writer-ready; independent acceptance tetap terbuka |

Identitas byte sumber ada di `source_inventory.json`. Register mencatat asal baris/section sehingga penerus membuka potongan relevan, bukan membaca ulang seluruh master tiap sesi.

## 2. Cakupan selesai CP7

| Kelompok | Deliverable yang wajib berfungsi | Batas |
|---|---|---|
| A | Snapshot as-of, identitas/lineage, completeness, status produksi terpisah | Unknown tidak menjadi nol; tidak ada ledger write dari kalkulasi |
| B | WIP terarah/kandidat/bermasalah, matching fisik, ETA, kapasitas bersama | Satu PCS dihitung sekali; tariff SKU laundry bukan output SKU |
| C | Baseline demand, target, dated netting, exact-size gap, prioritas | Draft sale sudah mengurangi FG; forecast residual tidak menghitung sale lagi |
| D | Kandidat model, rolling evaluation, parameter/model history | Adaptive betul-betul bekerja pada fixture layak; live tipis tetap fallback |
| E | Planner, panel Buat/Bagi Potongan, grouping, skenario/draf, apply bridge | Read/draf bukan reservation; apply memakai command sah dengan revalidasi |
| F | Tanya AI V1, snapshot sesuai izin, copy/open/manual fallback | Tanpa API berbayar, URL berisi data, kirim otomatis, atau auto-writeback |
| BR | Satu menu Business Report, narasi deterministik, panel Stok, periode dan arsip | Satu engine; laporan on-demand; keuangan tidak false READY |
| Reminder | Wiring manual dan evaluator kondisi in-app yang memakai hasil CP7 | Lifecycle manual tetap; ACK/snooze tidak mengubah fakta bisnis |
| Integrasi | Sales/invoice/return/refund/payment, attendance/payroll/Nota, FG handoff, HPP/finance/close/reporting | Source dan alur nyata, bukan demo yang diberi label connected |
| G | Full dummy-flow, predecessor protections, Auth/HTTP/browser, race, scale, audit exact candidate | Semua consumer final masuk kandidat sebelum audit, bukan ditempel setelah PASS |

Kemampuan bahan tersisa, kapasitas, biaya dan plan-versus-actual **wajib memiliki jalur valid dan jalur unknown yang diuji**. Ketiadaan data live tidak membolehkan placeholder. Tidak ada kewajiban baru membuat optimizer global, jadwal setiap mesin, cash forecast dengan kontrak penagihan baru, scorecard vendor/mandor, modul order/CRM/promosi, atau format ekspor baru. Riset EOQ/newsvendor/MILP adalah bahan opsi; tidak otomatis menjadi gate.

CP7.5 tetap cleanup/rebaseline/fresh-install equivalence. CP7C tetap stress operasional, scheduler/outbox/delivery, backup dan restore tanpa GPT. CP8 tetap audit akhir, rehearsal dan cutover atas mandat owner. On-demand bukan scheduled; accepted provider bukan delivered; CP7 PASS bukan production GO.

## 3. Peta semua checkpoint

Status CP1–CP5 di bawah adalah penerimaan historis pada master, bukan audit ulang saat menyusun paket. Perubahan CP7 yang menyentuh kontraknya wajib menguji kembali keluarga terdampak.

| CP | Fondasi yang diwarisi | Dipakai CP7 oleh | Bukti perlindungan |
|---|---|---|---|
| CP1 | Fingerprint repo/target, satu writer | P00 dan semua penerus | Source/branch/runtime receipt; stop pada writer tak dikenal |
| CP2 | Backup terenkripsi dan restore | P19/rilis | Restore proof baru ketika baseline/paket berubah; evidence lama dipertahankan |
| CP3 | Attendance cost pada APPROVED; PAID settlement; denominator SELESAI_DIJAHIT | P10 payroll, P11 HPP, P02 facts | Approve/paid/reversal sekali; QC/rework GOOD tidak membesarkan denominator |
| CP4 | HPP dan Auth owner | Semua RPC/consumer | Actor aktif, scope nyata, biaya per source dan per tanggal |
| CP4.5 | RBAC, production identity, Master Pola snapshot | P02/P03/P04/P08 | Brand+identity version+size, pola/revisi immutable; empty filter benar-benar empty |
| CP5 | Cutting/pickup/WIP/BS lineage, entitlement dan recovery | P03/P04/P12 | Partial/source capacity, lost reply, correction, posting atomik |
| CP6 | Laundry/QC/FG, tanggal, close, opening ALL, ACC/LAU, conversion/redye/pocket | Seluruh read model dan financial chain | Gate BD/BE/C6/ALL tetap; recost/claim/pocket tidak digandakan |
| CP7 | Perencanaan + wiring + BR + full flow | Paket ini | 35 CP7 dan coverage turunannya, runtime final sama |
| CP7.5 | Clean baseline dan arsip | Setelah CP7 accepted | Behavior equivalence, hash/schema ownership, install/restore |
| CP7C | Operasi mandiri dan pengiriman | Setelah CP7.5 | Load, retries, catch-up, delivery ambiguity, DR, egress gates |
| CP8 | Audit/cutover final | Setelah seluruh prasyarat | Rehearsal exact state, owner GO, transaksi live kecil yang diotorisasi |

## 4. Apa yang ada di kode sekarang

Inspeksi statis pada head `2c2fd5e`, bukan klaim query hosted. Package memakai React 19.2.8, TypeScript/Vite, Supabase JS 2.112.4; `wrangler.jsonc` melayani aset SPA. Tidak ada alasan pindah ke Next.js atau menambah layanan AI. Rancangan server menggunakan Postgres existing; lihat ADR-01.

| Area | Berkas nyata | Temuan / pekerjaan CP7 |
|---|---|---|
| Runtime | `src/config/runtime.ts` | `PARTIAL_CONNECTED`; FG handoff `BLOCKED_UNTIL_AUTHORITATIVE`. Jangan mengganti enum menjadi fully-connected sebelum route terbukti |
| Entry/menu/FG stock | `src/App.tsx`, fungsi `StockCard`, `src/productCatalog.ts` | Stok saat ini mengambil katalog/ledger contoh; P09 harus membuat reader FG chronological, pagination/search dan source drill-down |
| Sales | `src/SalesPages.tsx`, `src/sales/*` | `allInvoices`/catalog dan state lokal; helper eligibility bukan persistence; P09 perlu write/read facade sebenarnya |
| Finance | `src/FinancePages.tsx`, `src/financeData.ts` | Array cash/payables/receivables/payroll/journals; tombol UI tidak membuktikan ledger. P10/P11 menyambungkannya |
| HPP | `src/HppPage.tsx` | `hppLots` contoh; P11 tampilkan source HPP/recost/confidence native |
| Attendance | `src/attendance/AttendancePage.tsx`, `domain.ts` | Wiring harus ditelusuri terhadap facade native CP3; tidak menyimpulkan lulus dari perhitungan frontend |
| Reminder/close/audit | `src/OperationsAdminPages.tsx`, `src/reminders.ts` | State lokal/fixture disclosure; source manual reminder backend sudah ada, evaluator kondisi belum merupakan bukti scheduled |
| Potong/pickup | `src/ConnectedCuttingPage.tsx`, `ConnectedPickupPage.tsx`, `cuttingPersistence.ts` | Reuse `erp_get_cutting_workspace_v2`, selector pickup sah, envelope recovery; jangan menjumlah halaman UI |
| WIP | `src/ConnectedWipStatusPage.tsx` | `erp_get_wip_control_v1`; counter layar tidak otomatis menjadi additive supply |
| Laundry/QC | `src/useLaundryQcWorkspace.ts`, `ConnectedLaundryPage.tsx`, `ConnectedQcFinalPage.tsx`, `LaundryBdPanel.tsx` | Read/write connected dan BD pricing; read model harus menelusuri outstanding/source lines, bukan header qty saja |
| BS/konversi | `ConnectedBsResolutionPage.tsx`, `ConnectedProductConversionPage.tsx`, `productConversion.ts` | BE redye/rework/conversion menjaga lot source dan recost; kandidat planner tidak boleh menciptakan rute baru |
| Pocket/opening | `ConnectedPocketFabricPage.tsx`, `BePocketHistory.tsx`, `ConnectedInitialImportPage.tsx` | Denominator historical/native dan cost source; issue stok sudah terjadi, alokasi biaya tidak membuat issue kedua |
| Auth/facade | `src/auth/*`, `src/types/database.preconnect.ts`, `src/lib/requestEnvelope.ts`, `src/productionRecovery.ts` | Reuse allowlist dan guard; JWT sah tidak otomatis berarti izin role masih aktif |

Nama RPC di tabel adalah entry yang ditemukan pada source, bukan janji semua reader cukup untuk CP7. P00/P02 wajib membuat katalog resolved: signature, effective definition hash, table/trigger/caller dependencies, ACL dan per-date semantics pada database accepted. History migration yang menyebut fungsi bukan bukti definisi aktifnya.

## 5. Kontrak lintas domain yang tidak boleh rusak

### Identitas, kuantitas, dan kepemilikan

1. Toko adalah customer. Identitas selalu brand dahulu lalu SKU/version/exact size. Kode SKU yang sama antarbrand tidak bergabung.
2. Tujuan sebelum SKU final memakai calon hasil berbasis pola/revisi/material/rute/size. Tidak membuat ID SKU palsu atau histori jual palsu.
3. Satu physical source+size hanya satu posisi aktif. Parent adalah wadah lineage; jangan menjumlah parent dan child atau kirim+terima+QC sebagai supply terpisah.
4. GOOD, BS, hold, stuck/missing dan rework/rewash tidak saling menggantikan. Goods milik pelanggan/titipan bukan FG milik perusahaan.
5. Quantity, ownership, custody/location, condition, valuation dan settlement adalah dimensi berbeda. Barang pulang belum tentu ready; inspected belum tentu bernilai final.
6. COUNT exact integer; meter/kg/yard mengikuti decimal dan UOM yang sah. Parser tidak clamp/round input invalid menjadi angka valid.

### Biaya, entitlement, dan empat waktu

7. `physical_at`, economic/effective date, accounting/posting date dan `known_at` tetap berbeda. `generated_at` hanya waktu komputasi. Cutoff bisnis Asia/Jakarta; timestamp disimpan ber-offset.
8. APPROVED attendance mengakui biaya sekali; PAID hanya settlement. Rework/konversi tidak menciptakan denominator jahit atau reimburse baru kecuali pekerjaan/komponen tambahan memang sah.
9. Receipt belum invoice memakai status biaya yang sah; UNKNOWN tidak menjadi FREE. Invoice tiga bulan kemudian mengoreksi sumber biaya/GRNI/AP dan turunan HPP/COGS, tidak membuat stok/kerja lagi.
10. Pocket issue memindahkan stok sekali; alokasi periode mengalihkan expense ke WIP/FG/COGS menurut denominator sumber. Jangan memperlakukan seluruh biaya sebagai HPP tambahan tanpa mengurangi expense terkait.
11. Posted immutable. Correction/reversal/successor tertaut; pemulihan angka tidak menghapus fakta bahwa transaksi pernah dipakai. Rollback post-use mengikuti refusal existing.
12. Close/readiness memakai engine preflight per tanggal, bukan saldo total hari ini. Quantity valid boleh ditampilkan saat biaya pending, tetapi margin/ranking profit dan full financial READY ditahan.

### Transaksi dan informasi

13. Draft sale sudah memengaruhi availability. Draft→posted bukan penjualan kedua dan bukan pengurangan stok kedua. Cancellation/return/refund masing-masing mengikuti sumber sah.
14. Membuka, menghitung, mengurutkan, memfilter, mengekspor prompt, atau ACK tidak mengubah ledger, reservation, SKU status, invoice, order, atau source allocation operasional.
15. Menyimpan analysis/skenario/draf/attention adalah write terpisah yang diizinkan. Hak menyimpan analisis tidak memberi hak membuat transaksi.
16. Apply memeriksa actor terbaru, produksi Stop/Tunda, source/version/capacity/date dan request payload setelah lock. Hasil stale tidak dipakai diam-diam.
17. Balasan hilang setelah commit tetap UNKNOWN/VERIFYING, bukan langsung FAILED. Reuse request ID+payload; command lain yang bisa berbenturan tertahan sampai outcome terbukti.
18. Query gagal/partial/malformed/null tidak berubah menjadi empty/0/aman. Reader lengkap dibuktikan count+cursor+snapshot, bukan menaikkan LIMIT.
19. Report archive menyimpan apa yang benar-benar diketahui saat terbit. Backdate kemudian tidak mengarang knowledge sejarah yang tidak pernah direkam.
20. Permission berlaku pada route, RPC, aggregates, detail, cache, history, prompt dan deep link. Revocation harus diperiksa sebelum replay/cache delivery, bukan hanya login awal.

## 6. Jembatan integrasi yang harus punya bukti

| Jembatan | Masuk | Keluar / oracle | Pemilik paket |
|---|---|---|---|
| Pembelian/opening → material | Receipt, source price, opening provenance, lokasi | Qty/value dan prefix tanggal sah; no duplicate opening | P00/P02/P09/P13, CP6 diwarisi |
| Material → potong → pickup | Roll+yields, pola revision, batch exact size | Sisa raw/WIP; source cost conserved | P03/P04/P09 |
| Jahit → laundry → QC → FG | Completion, DO, receipt, claims, GOOD/BS | Unique remaining; SKU final dari command sah; ETA bukan FG | P03/P04/P10 |
| FG → sales draft/post | Eligible lot+size+location | Availability once; sales event unique; AR pada tahap sah | P10/P11 |
| Sales → return/refund | Invoice/source allocation | Restore barang sesuai kondisi; AR/refund/cash terpisah | P11/P13 |
| Attendance/Nota → payroll → cash | Approved period, source entitlement, deductions/advance | Expense sekali, payable/settlement exact | P12/P13 |
| Invoice/recost → HPP/GL/report | Effective source delta; transitive conversion | WIP/FG/COGS/GRNI/AP per-date reconcile; no false READY | P13/P15 |
| Source facts → planner → apply | Snapshot+policy+scenario+intent | Tidak posting sampai explicit action; latest state under lock | P02–P08/P10/P14 |
| Planner → Stok/BR/Reminder/V1 | Same run+scope+scenario+versions | Same operand, wording conditions preserved | P14–P17 |
| Correction → published archive | New knowledge/source version | Current stale, linked revision; original unchanged | P02/P13/P15/P19 |

P00 tidak boleh menutup gap CP6 hanya dengan mengganti label menjadi CP7. Jika ada sengketa scope, lampirkan requirement dan keputusan yang bertentangan; lanjutkan bagian yang tidak bergantung sambil mempertahankan gate yang benar.
