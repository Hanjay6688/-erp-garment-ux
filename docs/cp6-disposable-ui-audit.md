# Independent follow-up — consolidated observation pending

R3 harness `1efa64ac2ac2d006717520e156c121e96f6cf394`, tree
`7b19ad95637e87339fd319d5ac261dace303b72c`, Native 35142708437,
artifact 10466152140 (3,372,732 bytes; SHA-256
`478aa0b11f85b9398011dfe0a196e841852511204947565fec519219c6bbaeb7`).
All current invoice totals still reconcile, and all invalid staging variants
refuse preparation. The added historical observer found 12 open-period report
changes. **The artifact's automatic BUG_PROVEN label for those 12 is withdrawn:**
it assumed an open period was an immutable filed snapshot, which is not the
owner contract. The observations remain DATE_POLICY_REVIEW_REQUIRED, not PASS:
a dated invoice changes historical MATERIAL/AP/GRNI while recost/HPP events use
today; intermediate historical material value can be -5.25 or 7 with raw qty0.
No accounting-date policy is rewritten merely to satisfy that faulty oracle.
Closed receipt-date controls preserve the compared history. Import retains two
row-diagnostic gaps, with failed preparation and no money/stock effects.
Native UI rework hit Chromium datetime-local normalization at exactly zero
seconds; only the harness string format is corrected. Auth and clone cleanup
and exact restoration still passed. Product source remains unchanged.

R2 harness `f7ca546c561bbe0ad1685823f5b5096824e5ec25`, tree
`547bde2b288a098f76c5df4808e9a7d1815d088b`, ran in Native 35141866592.
All 24 calendar invoices and four raw-staging controls passed. NONNUMERIC_QTY
and MISSING_COST stop batch validation and leave the row PENDING without
persisted row errors: two GAP_PROVEN, zero business BUG_PROVEN, zero incomplete
native cases. Ledger was unchanged. CSV transport is still untested.
The four real controlled-clock cases passed on exact AI-R2. Real UI completed
48 missing-permission pairs, eight allowed create/hold controls and five legacy
BS UI lifecycle controls. Native UI rework stopped on a harness lookup using
POSTED instead of the source's actual SENT delivery status. That lookup and the
inherited delivery-count observer are corrected; assertions are retained.
Exact AH restore and complete Auth/clone/container cleanup passed. CodeQL
35141866598 succeeded in all four languages. Artifact 10466380365 was checked
at 3,371,084 bytes, SHA-256
`d3c2d677b4146475c775efeb2132d00ae87920903d801a0b5964fc46a1f36f1c`.
The next observation additionally checks the report before invoice receipt
and whether invalid staging is refused by prepare; no business code is patched.

R1 audit harness `f963ca28b6ab02e3db9c8a8e3b40aac9d7e94f31` ran in
Native 35140333202. The existing 142/16/23/12 groups and 43 UI assertions
completed. New tests exposed harness errors: the invoice report selected three
days instead of the complete invoice period; staging identifiers exceeded the
schema length; the clock helper imported from the wrong checkout; and an
unhandled browser response wait prevented Auth cleanup. Therefore new groups
and exact restoration were INCOMPLETE. Whole clone/container disposal passed.
No new business defect is established by R1. CodeQL 35140333204 succeeded.
Artifact 10464827882: 5,251,305 bytes, SHA-256
`ee5cd0ab91c47d67951ed16e124d6feb8695ffad3200a7a90691e215e2e43b4f`;
ZIP CRC and bytes were independently checked. The retry changes only harness
observation, identifiers, imports and promise handling; product code stays fixed.

Incoming report checkpoint: `555d8f29ea2d3f58dc2c7d10e7cd80099cdd3b49`, tree
`da665828227a0a4fd5d17452538edb98754738ad`. This wave changes audit tooling only;
all product and backend source remains identical to that checkpoint.

Incoming artifact 10463056747 was independently matched to its SHA-256,
5,243,788-byte size and 32-entry ZIP CRC. Native and four CodeQL jobs were read
from GitHub and are successful. These are verified incoming writer results,
not a new global acceptance.

New execution is planned on the exact AI-R2 engine: 24 calendar-delay invoice
scenarios, six raw PENDING staging validation scenarios, four controlled-clock
long/fresh transaction controls, and original browser rework/permission paths.
The inherited 142/16/23/12/95/43 assertions remain present. Historical 460 is not
rerun without invalidating drift. Each new independent group persists its own
failures and unfinished cases; none is PASS before execution.

Owner master `ERP_GARMENT_MASTER_CONTEXT_2026-09-15_AD.md` section21.1 requires
preview, row errors, totals, idempotency, manifest and recovery for imports.
No application CSV parser/upload was found. Testing raw normalized staging is
therefore explicitly separate from CSV transport. Three calendar months is a
required supported scenario; no 90-day rejection rule is invented.

One writer, competition branch only. Main confirmed at
`6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`. No hosted target or CP7 work.
`production_go:false`. Current verdict remains **INCOMPLETE** pending this run
and disposition of any newly proven gaps.

---

# Final audit CP6 — CP6_HOLD setelah perbaikan UI

Bukti akhir: 16 September 2026 UTC / 17 September 2026 WIB.
**Writer PASS pada cakupan yang dijalankan; belum independent PASS.**
`production_go:false`. CP7 belum dimulai.

“VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”

Bagian ini merupakan status terbaru. Catatan proses di bawah dan laporan
`cp6-final-audit-checkpoint.md` mempertahankan keadaan pada checkpoint lamanya;
pernyataan lama “tidak ada bug baru” atau “UI belum dapat dijalankan” tidak boleh
dipakai sebagai status kandidat sekarang.

## Keputusan dan penghalang penutupan

**CP6_HOLD.** Dua bug material pada UI asli ditemukan melalui transaksi biasa,
diperbaiki, lalu gate gabungan selesai. Karena auditor ini mengambil giliran
penulis, aturan competition owner mewajibkan pemeriksaan chat independen lain
atas successor. Hasil sendiri tidak boleh diangkat menjadi independent PASS.

Kewajiban yang masih terbuka:

- Audit independen kedua perbaikan, seluruh pemanggilnya, serta serangan baru di
  luar daftar writer. Kandidat yang diserahkan dipin di tabel berikut.
- Bukti aplikasi untuk seluruh cabang BS/rework, penyelesaian rework parsial
  kumulatif, dan kombinasi izin yang belum dicakup 62 pasangan facade-role.
  Jalurnya ada; tidak diberi label N/A atau dipindahkan diam-diam ke CP7.
- CSV/import: tidak ditemukan parser/upload atau pemanggil staging-finalize di
  aplikasi. Tes native memulai dari staging yang sudah VALID. Kontrak opening/
  import owner mengikat preview, error per baris, total, idempotensi dan recovery;
  penugasan upload CSV sebagai deliverable CP6 belum tersurat. Scope ini perlu
  dipastikan dan jalur yang menjadi kewajiban harus dibuktikan.
- Batas keterlambatan invoice hingga tiga bulan belum teruji lengkap oleh 16
  kasus tambahan yang memakai keterlambatan beberapa hari. Empat zona sesi dan
  periode tertutup telah diuji; transaksi panjang yang benar-benar melintasi
  tengah malam WIB belum mendapat bukti baru. Tidak mengasumsikan 90 hari selalu
  sama dengan tiga bulan kalender.

Sales/invoice, payroll/Nota, HPP/Finance/report UI yang masih simulasi dipetakan
sesuai master owner 2026-09-15_AD bagian checkpoint: koneksi sisanya dan alur
owner lengkap adalah CP7. Ini tidak mengecualikan konsistensi backend lintas
modul, ledger, HPP dan laporan dari CP6. CP7 tetap tidak dikerjakan di sini.

## Identitas kandidat dan alat

Repo `Hanjay6688/-erp-garment-ux`; satu penulis; hanya branch
`competition/cp6-j-closure-20260911`, fast-forward. Main, PR24/25, hosted UAT,
legacy, production, merge dan deployment tidak dimutasi.

| Objek | SHA | Tree |
| --- | --- | --- |
| Backend bisnis AI-R2, tetap | `25fa4736329e5148dfdb3572bc169952cba23251` | `a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d` |
| Commit terakhir yang mengubah sumber produk UI | `d7a92f00b0779d614478778bd8f1ddd367122ff7` | `71b281da4455296c6f808ef28557bf4ad8f4daa4` |
| Snapshot akhir yang diuji + alat gate gabungan | `9a919060b1037fe0747515b6ed3b98aebb41b5b1` | `a0121c4f4c1ec6d2fd90852afd6c7d3b6c366859` |
| Checkpoint alat masuk dari owner | `2735703114ab52d605aa0d6cd2aa530b074fb5e9` | `16a7caef2949f50f10544c04616026e22647c6be` |
| Main, tetap | `6d4cda118f5d28d1f039cc0ecf318d0866f55c2c` | Tidak ditulis |

Parent snapshot gate adalah `5285a5f3e17b64ac4ae211c1ac5f6a39d57cd161`.
Sumber `src`, `supabase`, dan package sama persis antara commit produk d7a92f0
dan snapshot gate 9a91906. Tidak ada SQL/migrasi/rollback bisnis yang diubah.
31 berkas sumber alat/UI dipin SHA-256. Selain perbandingan sumber, gate
memverifikasi 690 objek runtime AI, izin asli, pemanggil public RPC, transaksi,
dan hasil ledger/laporan. Kesamaan byte sendiri bukan oracle perilaku.
Commit dokumentasi setelah gate hanya menyimpan laporan, bukan eksekusi ulang.

## CI, CodeQL dan paket bukti

- [Gate gabungan 35133830834](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35133830834): SUCCESS; job 104921105516.
- [CodeQL 35133830900](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35133830900): SUCCESS, Python, JavaScript/TypeScript, C/C++, Actions.
- [Artifact 10463056747](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35133830834/artifacts/10463056747): 5.243.788 byte, 32 entry.

SHA-256 ZIP:

```text
1deeeb830baa39c3c4d43d502fa3ba72a40a0aa5e7e45d4a97d5591188cd252b
```

ZIP diunduh ulang; SHA-256 dan CRC semua entry cocok. Pemindaian pola JWT,
token GitHub, private key dan secret key tidak menemukan kecocokan. Ini
pemindaian pola tertentu, bukan jaminan mutlak semua bentuk rahasia. Data uji
sintetis; tidak ada akun/bisnis nyata yang dipakai. CodeQL bukan oracle uang.

| Cakupan pada snapshot akhir | Rencana / selesai | Hasil dan batas |
| --- | --- | --- |
| Gabungan native warisan | 142 / 142 | PASS, termasuk kontrol detektor; bukan 142 alur bisnis baru |
| Invoice bertahap sesudah produksi/penjualan | 16 / 16 | Ekspektasi nominal mandiri; 0 bug, 0 incomplete |
| Kerja/upah, lineage, role, HPP native | 23 / 23 | PASS terbatas; bukan bukti transport UI |
| Jadwal dua sesi | 12 / 12 | Enam konflik kerja × commit/abort sesi pertama |
| Auth/JWT/HTTP asli | 95 / 95 | Lima facade, tujuh aksi, 62 pasangan facade-role; bukan semua kombinasi izin |
| UI asli desktop dan mobile | 43 / 43 | WRITER_PASS; 0 unfinished; layanan dan DB asli disposable |
| Unit | 230 / 230 | PASS; terpisah dari bukti browser nyata |
| Security/source, build, scan bundle | Semua selesai | PASS |
| Pemulihan AI → AH | 533 fungsi, 223 tabel | Definisi, owner/ACL, data, katalog dan marker cocok baseline |
| Cleanup | Selesai | Auth/sesi, antrean/konteks, clone, layanan dan container diperiksa |
| Matrix historis | 460 historis | REUSED_EVIDENCE; tidak dijalankan ulang sebagai matrix runtime akhir |

Native 142 berlangsung 18:23:47–18:24:54 UTC, seluruhnya tanggal bisnis
17 September WIB; tidak ada retry otomatis atau perubahan oracle tanggal.
Runtime: Supabase CLI 2.116.0, PostgreSQL 17.6.1.165, PostgREST 16.1,
Playwright 1.62.1, Chromium, dan smoke login agent-browser 0.38.0.

File utama dalam ZIP: `writer-ai/crossflow.json`, `final-audit/NEW_CROSSFLOW.json`,
`independent-ai/RESULT.json`, `independent-ai/CONCURRENCY.json`,
`final-audit/HTTP.json`, `final-audit/UI.json`, `independent-ai/EXACT_RESTORE.json`.
Semuanya di bawah `candidate/cp6-proof/`. Case ID dan observasi per tahap ada di
file tersebut; jumlah PASS tidak dijumlahkan menjadi klaim keselamatan global.

## Temuan dan cakupan perbaikan

| Temuan | Reproduksi biasa | Perbaikan dan pembuktian |
| --- | --- | --- |
| CP6-UI-QC-READY-BASIS-01 | Kirim 10, terima 8, QC 5 lalu 3. UI memakai sisa seluruh Potongan 5 dan mengirim PARTIAL_SELECTION; server benar meminta ALL_READY karena ready-for-QC habis. Penolakan atomic, FG 35/WIP 35 tetap. | Mode memakai qty siap QC yang terbukti terlihat lengkap. Filter receipt/size atau truncation tidak dianggap seluruh grup. Pemanggil, tes unit/DOM dan checker lama diperbaiki bersama. UI 5+3+2, filter parsial, Good/BS, dua role, ledger dan laporan diuji. |
| CP6-UI-RECEIPT-PROCESS-02 | POST_RECEIPT sah; workspace HTTP 200 berisi nama proses aktual. Parser asli menganggap nama proses sebagai metadata khusus attempt gagal sehingga halaman Laundry menampilkan kegagalan layanan. | Parser bersama menerima nama proses pada receipt fisik. Tiga metadata khusus attempt tetap dilarang di receipt fisik; attempt wajib lengkap. Unit, fixture browser dan UI nyata mencakup posted/reversal, RETRY_AT_VENDOR serta RETURN_UNPROCESSED. |

Bukti asli pertama: run 35129057885, artifact 10460209095,
SHA-256 `d06eebd9d9089c81b3f5d8f627fbfae5a5c8804331cda4d862b83d7947eb4088`.
Gate akhir memverifikasi ZIP/CRC, hash modul asli, penolakan dan keadaan atomic.
Bukti asli kedua: run 35131279236, artifact 10461242981,
SHA-256 `6106756a15a33287b77463e88c345c06547e96893df33a82808731719f9f10f6`;
ZIP/CRC dipastikan lokal. Parser saat bukti kedua masih byte-identik AI-R2.

Kontrol yang sengaja memutus respons dilakukan sesudah server commit nyata;
reload mengirim ulang UUID dan payload yang sama. Kontrol itu membuktikan
recovery transport, bukan bukti transaksi normal semula merusak data.

Aritmetika UI mandiri: 10 potong × 7 = 70. Desktop akhirnya FG 10/nilai 70,
WIP 0. Mobile menghasilkan Good 8 + BS 2: FG 56, WIP 14, accrual -70.
Retry-at-vendor 4 potong menambah biaya 28 tanpa Good/BS/FG palsu.
Full return 10 mempertahankan biaya 70 dan mengembalikan custody; kirim ulang
berdokumen baru menambah estimasi 70. Reversal biaya lama menyisakan 70 dan
tidak mengubah custody kirim baru. Laporan READY cocok pada setiap checkpoint.

Catatan UX nonmaterial yang terlihat: saat antrean QC sudah habis, pesan
“Master Final SKU atau lokasi FG belum lengkap” dan “cakupan antrean belum cukup”
bisa tampil bersama keberhasilan posting. Tidak terbukti ada master hilang atau
ledger salah; teks keadaan kosong perlu ditinjau dalam audit UI berikutnya.
Field diagnostik lama `posted_delivery` di UI.json menghitung literal status
POSTED, bukan jumlah pengiriman aktif. Pembuktian double submit memakai query
terpisah atas satu dokumen non-REVERSED dan waktu fisik; field lama tersebut
bukan oracle saldo atau cleanup.

## Peta antarmodul, reuse dan batas bukti

| Hubungan | Sumber/pemanggil yang dipetakan | Bukti final / klasifikasi | Sisa cakupan |
| --- | --- | --- | --- |
| Beli → penerimaan → GRNI → invoice → AP → bayar/retur | purchase headers/items, material movements, finalize invoice, supplier allocation/reversal | Native 142 + invoice 16, RECONCILED | Durasi tiga bulan, semua transport aplikasi/import |
| Roll → potong/size → pickup → kerja/upah → payroll | yields/distribution, work snapshots/completion, trigger lineage, jurnal | Native 23 + race 12 + invoice crossflow, RECONCILED | Accrual upah bukan pembayaran payroll; koneksi sisanya sesuai CP7 |
| Laundry → parsial → QC → Good/BS → FG | batch-size facts, public facade, parser bersama, QC allocation, FG lots, report, blockers | HTTP 95 + UI 43, RECONCILED pada successor | Semua cabang rework dan kombinasi role belum lengkap |
| FG → draft → posting → AR → bayar → retur/refund | draft reservations satu kali, sales post/allocation, reversal dan retur tertaut | Kelompok native DRAFT/CASH/RETURN pada 142, RECONCILED | UI Sales masih simulasi dan terjadwal CP7; native bukan bukti UI |
| Koreksi/backdate → WIP/FG/COGS → jurnal/laporan | recalc queue, revaluation events, HPP state/events, financial snapshot/checks | Invoice 16, native 142/23 dan laporan UI 43, RECONCILED | Seluruh batas tanggal dan transaksi panjang lintas tengah malam |
| Maintenance historis F..AB | controller/capsule/rollback dan manifest per target historis | 460, REUSED_EVIDENCE | Bukan pengujian baru runtime AI atau pengganti UI/import |
| PASS UI simulasi lama | payload mock berbeda dari payload receipt nyata | DRIFT; tidak diwariskan sebagai PASS aplikasi asli | Digantikan hanya pada 43 kasus yang benar-benar dijalankan |
| CSV dan role/rework yang belum dicakup | belum ada transport CSV; jalur rework nyata ada | RERUN_REQUIRED / kontrak scope CSV belum tegas | Tidak diberi PASS atau N/A |

Tidak perlu mengulang 460 hanya untuk angka: perbaikan ini tidak mengubah SQL,
trigger, izin backend, controller maintenance atau dependensi runtime historis.
Perubahan pembentukan payload/reader UI dibuktikan ulang dengan layanan asli;
backend gabungan dan race dijalankan lagi. Reuse 460 tetap dibatasi target dan
runtime historis, termasuk perubahan controller/capsule yang sudah dicatat pada
rekonsiliasi sebelumnya; tidak pernah berubah menjadi 460 PASS AI terbaru.

Rekonstruksi lama lengkap: `docs/evidence/cp6-final-audit-reconciliation.json`.
T146 CANCELLED meninggalkan 177/300 hasil PASS dan 123 belum selesai; T147
menyelesaikan 300 pada run lain. 460 = 23 target × 5 operasi × 4 jadwal.
Tidak ada manifest sah yang membuktikan “500-an kasus bisnis unik”. Kegagalan
finalizer/fixture/restore dan sesi alat terputus dibedakan dari transaksi ERP.
Penyebab internal penghentian chat/GPT tidak disimpulkan.

## Pemulihan dan serah-terima

Fixture native memberi schema USAGE sementara dan memulihkannya; bukti itu
bukan bukti izin aplikasi. HTTP/UI memakai ACL asli tanpa grant tambahan.
Fixture UUID historis dibuktikan ditolak parser asli, lalu seluruh clone lama
dibuang. ID sintetis diperbaiki sebelum penyemaian clone baru; SQL yang diterima
dan histori posted tidak diedit untuk meloloskan tes.

Restore AI→AH membandingkan 533 definisi fungsi beserta owner/ACL dan seluruh
223 tabel/data, katalog, marker. Marker AI 0, AH 1, capsule AI tidak tersisa,
690 objek terverifikasi sebelum drain, dan sesi setelah drain kosong.
HTTP: auth users/sessions/identities/refresh tokens, execution context,
jurnal tidak seimbang dan idempotency IN_PROGRESS semuanya 0. UI menutup
browser/proxy/preview, menghapus build disposable dan memastikan 0 auth users/
sessions. Dokumen posted tetap ada sampai clone utuh dibuang. Clone cp6_auth,
clone race, PostgREST dan container database dihapus; residue pemeriksaan 0.

Auditor berikutnya harus membaca bagian status terbaru ini, aturan audit
efisien, invariants, handoff AF–AI, dan rekonsiliasi historis; periksa remote head
sebelum bekerja. Verifikasi artifact akhir dan dua counterexample asli.
Cari masalah di luar temuan writer; prioritaskan sisa kewajiban di atas.
Perubahan bisnis berikutnya kembali berstatus Writer sampai audit independen.

```sh
git fetch origin competition/cp6-j-closure-20260911
git show 9a919060b1037fe0747515b6ed3b98aebb41b5b1:docs/evidence/cp6-disposable-ui-source-pins.json
gh run view 35133830834 --repo Hanjay6688/-erp-garment-ux
gh run download 35133830834 --repo Hanjay6688/-erp-garment-ux --name cp6-final-boundary-audit
```

Unduh ZIP melalui artifact API untuk mencocokkan digest ZIP; hasil ekstraksi
`gh run download` bukan ZIP dengan checksum yang sama. Lanjut hanya pada branch
competition, lingkungan disposable, tanpa CP7 atau production go.

---

# Catatan proses dan checkpoint terdahulu

# CP6 — original UI on a disposable target

Owner approved adding the dedicated disposable UI target after the final-audit
checkpoint reported the UI target-guard gap. This is a frontend writer successor,
not an independent acceptance of its own changes. CP7 is not implemented.
`production_go:false`.

Backend candidate remains AI-R2 `25fa4736329e5148dfdb3572bc169952cba23251`, tree
`a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d`. Starting competition head is
`9f884fbb27bdb92d6ee63f60333e007dc36f3f1c`, tree
`b4cf1e5d6c8aff531470af01dcdb4d146b4fca7f`. Source pins and the CI artifact identify
the separate frontend/harness candidate. No SQL migration or function changes.

The build mode `cp6-disposable-test` only accepts page origin
`http://127.0.0.1:4176`, API origin `http://127.0.0.1:54328`, and a local anon key.
Normal build/deploy rejects this runtime. Its output is a separate temporary
directory removed after testing. A transparent loopback proxy forwards Auth to
the local Auth service and RPCs to the disposable clone's original public API.
No business API responses are mocked. Schema permissions are not expanded.

Planned evidence: original login, anonymous/unmapped/inactive/viewer restrictions;
granular operator on desktop and owner on mobile; ten physical pieces at rate 7,
staged receipts of eight and two, QC postings of five, three and two, parent reversal
blocked by posted children, linked reversal back to zero balances, double submit,
and a paid failed-wash commit whose HTTP response is deliberately lost before
page reload and reconciliation with the original persisted UUID. The lost-response control tests transport
recovery; it is not evidence that an ordinary ERP transaction is inconsistent.
Each completed case is persisted before the next one. Unfinished cases stay
INCOMPLETE. Financial arithmetic is independent of the writer's PASS list.

Cleanup closes browser, preview and proxy; deletes temporary Auth users/sessions;
retains posted business history until the whole disposable clone is removed;
then runs the unchanged AI-to-AH restoration comparison and container cleanup.
Credentials, tokens, traces, browser storage, and database dumps are not artifacts.

Scope correction from the restored owner master context
`ERP_GARMENT_MASTER_CONTEXT_2026-09-15_AD.md` (Library version 1, lines 1960–2004):
CP6 is Laundry → QC → exact-size Final SKU/FG. Remaining Sales/invoice,
payroll/Nota, HPP/Finance/reporting connections and full dummy flow through journals
and reports are explicitly CP7 acceptance. The older blanket UI-gap statement
must be read with that contract. This does not remove CP6's backend accounting,
stock, HPP, correction or report-consistency obligations.

Opening/import rules in section 21 require preview, per-row errors, totals
reconciliation, idempotency, manifest and rollback/recovery. Import obligations
need separate source-to-path inventory; this document does not silently relabel
unproven import work as CP7 or N/A.

Run 35123732959 stopped during the source guard, before browser installation or
database startup: adding local output paths to the frozen predecessor `.gitignore`
was rejected. The predecessor file is restored byte-for-byte; the source guard is
unchanged. All 226 unit cases passed before that failure. No UI/business execution
is claimed for that run. Its cleanup-only artifact is 10457879554 (288 bytes),
GitHub-reported SHA-256 `c1abb38719dee9f087cf1a208ffd55620a978780b56c90964f52b0ceca72ebdc`.

Current execution status: CP6_HOLD — two original UI bugs proven; writer repair under test. The earlier native/HTTP audit and historical
460-case reconciliation remain in `docs/cp6-final-audit-checkpoint.md` and
`docs/evidence/cp6-final-audit-reconciliation.json`. No new PASS is claimed here.

Run 35124061446 completed the native combined 142, staged-invoice 16, work 23,
two-session 12 and Auth/HTTP 95 stages. UI stopped at unmapped-account login after
1/28 cases (anonymous login page). UI cleanup, clone disposal and AI→AH restoration
completed. The test proxy omitted Auth's `X-Supabase-Api-Version` CORS header;
this is a harness transport defect, not a qualified ERP posting bug. The header
is now passed through, browser transport failures are recorded without payloads,
and label selectors use the original accessible names. CodeQL run 35124061384
succeeded. Artifact 10459275971 is 2541090 bytes; GitHub-reported SHA-256:
`539e204978506b71c9f5c4bf31132aa80895ddb0d1a22f33147d51601789a7c0`.
The final runner expands the receipt chain to 8+2 and QC to 5+3+2 (36 planned
cases), including browser reload after the deliberately lost response.

Import inventory: `scripts/cp6_ac_independent_audit.py` inserts synthetic
`migration_staging_rows` already marked VALID, then calls
`erp.prepare_migration_opening_balance`, `erp.post_opening_balance`, and
`erp.finalize_migration_batch`. The combined native family retains direct/import
opening cases. No CSV parser, file input, or staging/finalize browser caller was
found in `src` at this candidate. This is a missing executable application path;
native staging evidence does not close CSV transport. Section 21 of the owner
master binds these rules to opening/import and cutover, without assigning a
separate CSV-upload deliverable explicitly to CP6. Preserve that scope question;
do not infer N/A or implement a new import product during this audit.

Run 35125003066 / candidate a4d45ef4742d2b8b14a92c631a6dd0db84b3accb:
the Auth version-header correction alone did not close browser transport. UI
remained 1/36, with `/auth/v1/token` reporting `net::ERR_FAILED`. The proxy also
combined lowercase upstream CORS headers with mixed-case local headers, leaving
duplicate origin values. It now replaces headers consistently and checks the
real Auth health response and preflight before opening the browser. This still
requires a successful browser rerun; it is not an ERP transaction finding.

The same run crossed Jakarta midnight (combined native stage 16:59:15–17:00:34
UTC). It completed 119 PASS and 23 FAIL: 16 explicit
`AA_INVOICE_DAY_CHANGED_REQUIRES_SEPARATE_MIDNIGHT_CASE`, three cash reversal-date
expectations, and four previously-future payment dates that became today's date.
The latter seven expectations use the phase-start date. These are unresolved
rerun/clock-context evidence, not 23 proven business defects. The frozen oracle
is unchanged. Subsequent runs record the real business date before/after and
preserve the original exit code; there is no automatic retry or changed oracle.
The 16 additional invoice cases, 23 work cases, 12 schedules, HTTP 95, exact
AI→AH restoration and cleanup completed. Artifact 10458598039: 2529732 bytes,
SHA-256 `ed3c7e15d5ef8c34167ddf3e621409e326f3baccd409d63dfa8937747693ace5`.
The downloaded bytes and ZIP CRC matched. CodeQL 35125002987 passed four languages.

Run 35126188260 / candidate 0efabcfb8ee717604c32b07f760237416ec498af:
native 142/16/23 and 12 schedules completed; the combined stage stayed on the
same Jakarta business day. HTTP 95 passed. Real browser Auth passed anonymous,
unmapped and inactive cases (3/36). Viewer workspace did not render its form.
The inherited foundation fixture uses non-RFC UUIDs, rejected by the original
frontend parser; the next run records a direct parser qualification before
disposing the complete HTTP clone and seeding a fresh UI clone with canonical
synthetic IDs. This changes fixture IDs before insertion, not posted history,
product parsing, schema permissions, or admitted SQL. Artifact 10459407523,
2541900 bytes, SHA-256
`1a41825ad876c78412fc60ecdddcf9c95399697d30b49528db436a3e9f5d3e99`;
downloaded checksum, ZIP CRC and token/private-key scan passed. CodeQL
35126188318, exact AH restoration and cleanup passed.

Commits explicitly marked `[cp6-ui-focused]` run a focused HTTP/UI diagnostic
gate while the browser harness is being corrected. RUN_SCOPE.json records the
native 142/16/23/12 groups as NOT_RUN_FOCUSED, never PASS. A final unmarked
commit or workflow dispatch must run the entire combined gate after stability.

Focused run 35127566063 stopped before the fixture qualification/browser cases:
the installed TypeScript 7 package does not expose the older transpileModule
API. HTTP 95, restoration and cleanup completed. The diagnostic loader now
uses Node's built-in type stripping, verified locally against the original
parser. Artifact 10460456192 (313170 bytes), GitHub-reported SHA-256
`f4d5daef6b9126c24ad8b2581c5315e6ab4f86940fabc8ee467e2cb7d931426a`.
Native 142/16/23/12 were intentionally NOT_RUN_FOCUSED; no browser PASS.

Focused run 35128108373 on 6d7312100eb6ff7ac0b6ecb68850a9355edf38a1 confirmed
the inherited fixture's UUID rejection with the original parser. The fresh
qualified clone reached 8/36 UI cases: all four access cases, inert form,
one dispatch despite double submit, receipt of eight, and QC of five.
The next ordinary QC of three received a non-200 response. Its exact rejection
and before/after ledger state are being captured before assigning a product
verdict. Artifact 10459529337 (2490968 bytes), GitHub-reported SHA-256
`60433679cf8561f4ba6c9409953ea88db664db195f49f3c4023b55d4b3e787a8`.
HTTP 95 and restore/cleanup completed; native groups stayed NOT_RUN_FOCUSED.

The local executor disconnected with environment_offline after this run.
Source is checkpointed in Git; GitHub/CI remains available for bounded
diagnostics. No internal cause of the disconnection is inferred. The next
diagnostic changes only harness logging, a READY precondition, and evidence;
the business UI and backend remain the same for reproducing the rejection.

## Temuan baru: CP6-UI-QC-READY-BASIS-01

Status: BUG_PROVEN pada UI asli; perbaikan writer sedang diuji. CP6_HOLD.
Run [35129057885](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35129057885)
pada harness `68db9a5387cb993921476433a964b68fa6d08521`, tree
`e16e6e89e334e9da440d624b4957b4dee1513865`, menyelesaikan 8/36 kasus
UI. POST_FINAL_SKU kedua mengirim Good 3, mode PARTIAL_SELECTION,
expected version 5. Server mengembalikan HTTP 400/P0001 karena sisa
barang siap QC setelah posting adalah 0. Dua potong yang masih di Laundry
membuat sisa seluruh Potongan 5; itulah angka keliru yang dipakai UI.

Ini transaksi biasa pada backend AI-R2, bukan injeksi data rusak. Hash SHA-256
modul QC asli: `7d5ed652ce85d287ee5954800e16c2756633f5df37612e831dac978fb485897c`.
Sebelum dan sesudah penolakan: FG 5 pcs/nilai 35, WIP 35, accrual -70,
satu QC, satu pergerakan FG, empat baris jurnal, nol jurnal tidak seimbang,
nol execution context. Server gagal secara atomic; bug menghalangi alur UI
yang sah, tanpa bukti perubahan parsial.

Artifact 10460209095, 2491309 byte, GitHub-reported SHA-256:
`d06eebd9d9089c81b3f5d8f627fbfae5a5c8804331cda4d862b83d7947eb4088`.
Respons penolakan dan state sebelum/sesudah juga dicatat dalam log job
104905208286 dan UI.json. HTTP 95, restore AH dan cleanup selesai.
Pengunduhan ulang/CRC artifact ini masih belum dilakukan karena executor
lokal terputus; digest di atas berasal dari metadata GitHub.

Keluarga perbaikan:
- Producer: Good receipt per batch/ukuran; consumer: formulir QC dan deklarasi
  completion_mode. Sisa seluruh Potongan tetap ditampilkan sebagai informasi,
  tetapi tidak menjadi jumlah barang siap QC.
- Seluruh Good/BS yang dipilih memakai satu mode berdasarkan jumlah siap QC.
  Jika masih ada barang siap yang terlihat tetapi tidak dipilih, mode partial
  dapat dibuktikan walau daftar belum lengkap.
- Memilih seluruh jumlah terlihat hanya menjadi ALL_READY jika antrean tidak
  terpotong dan pencarian kosong atau cocok dengan metadata bersama PO,
  Potongan, atau Model. Filter receipt/vendor/ukuran, wildcard/escape dan
  kolasi yang tidak dapat dibuktikan tidak dianggap sebagai seluruh sumber.
- Server, facade, izin, trigger, perhitungan HPP/laporan dan rollback tidak
  dilonggarkan. Penolakan server terhadap deklarasi yang salah tetap berlaku.
  CP5 rework mempunyai aturan hasil kumulatif per order yang berbeda;
  halaman QC simulasi bukan pemanggil facade ini.
- Tes lama yang menyamakan remaining Potongan dengan ready QC diganti dengan
  angka fisik 10 keluar → 8 kembali → 5+3 QC, disusul 2 kembali/QC.
  Kasus UI diperluas menjadi 38 dengan kontrol filter receipt versus PO.
  Guard scope dan source pins mencakup modul serta tes yang berubah.

Tidak ada SQL yang diterima diubah. Successor ini tetap hasil writer sampai
diperiksa chat independen. Gate penuh wajib menyusul setelah keluarga stabil.

Run 35130093753 pada writer c59b18117f7a0377826bcaa00cbaeb4d6040f48b
menyelesaikan 228/228 unit test. Pemeriksa statis N03/N04 kemudian menolak
karena masih mewajibkan ekspresi `selectedQty === authoritativeRemainingQty`
yang terbukti menghalangi finalisasi 3 pcs. Browser/database belum dijalankan.
Artifact cleanup-only 10461121371, 288 byte, GitHub-reported SHA-256
`5ece36f491eaf64ffefa89c54f6e44a8c6037d077d7e973846341381578e4e1c`.

Inventaris 27 pemeriksa CP6 menemukan tuntutan lama tersebut hanya di
scripts/check-cp6-deep-business-repair.mjs. Bagian N03/N04 kini mewajibkan
basis ready, bukti cakupan antrean, penguncian saat cakupan tidak cukup,
dan tiga kelompok regresi; ekspresi lama ditolak eksplisit. Seluruh bagian
lain, termasuk immutable migration, role, financial/report checks dan rollback,
tetap identik. Source pins/guard turut mencakup perubahan pemeriksa ini.

Run 35130416443 pada 80e5729e095418d1a0c0c6c66c9649f14400eea4
melewati unit/security/build dan menyelesaikan 10/38 kasus UI. Finalisasi 3
yang sebelumnya ditolak kini berhasil; FG menjadi 8 pcs/nilai 56, WIP 14.
Kontrol filter receipt menahan posting tanpa perubahan ledger. Saat kembali
ke Laundry, halaman menampilkan kegagalan workspace. Akar masalah kedua
belum dikualifikasi: pesan UI bersifat umum. Diagnostik berikut membaca
respons asli dengan parser produk asli, merekam error transport/parser dan
hash payload sintetis; tidak mengganti respons bisnis.

Artifact 10460842458, 2491014 byte, GitHub-reported SHA-256
`6606c380fa3132df700462de220629107d07c950d0c516902d5c6c8378f38747`.
HTTP 95, restore dan cleanup selesai. Kelanjutan UI tetap INCOMPLETE.
Counterexample pertama kini juga diverifikasi ulang di CI dari ZIP asli,
termasuk checksum/CRC, pin modul pada AI-R2 dan kesamaan state sebelum/sesudah;
gangguan executor lokal tidak menjadi alasan mengabaikan bukti masuk.

## Temuan baru: CP6-UI-RECEIPT-PROCESS-02

Run 35131279236 pada `17d4bee4bb8c4efede8d2b35cda2cb46117d4610`
(tree `3d7c3ac49253b1b40a95b1cd6aa2b56858b7f47b`) membuktikan masalah
kedua dari transaksi penerimaan biasa, tanpa injeksi data tidak konsisten.
Workspace Laundry HTTP 200 mengembalikan PHYSICAL_RECEIPT, process_name
`CP6 Race Wash`, serta failed_wash_attempt_id/custody_outcome/attempted_qty_pcs
semuanya null. Parser produk asli menolak nama proses yang sah sebagai
metadata attempt gagal. Halaman lalu menampilkan pesan layanan tidak terhubung.
Produser SQL memang mengambil nama dari actual_wash_process_id untuk penerimaan
biasa maupun attempt gagal. Konsumen bersama adalah parseReceiptSummary melalui
parseLaundryQcWorkspace, termasuk pembacaan ulang dan riwayat reversal.

Perbaikan menerima nama proses aktual pada penerimaan fisik, tetap menolak tiga
metadata khusus attempt di penerimaan fisik, dan tetap mewajibkan metadata lengkap
untuk kedua custody attempt gagal. Model, unit test dan fixture browser lama
(disertai proses aktual) diperbaiki bersama; tidak ada perubahan SQL/ACL/trigger.
Tes unit mencakup receipt POSTED/REVERSED, proses null/nama sah, dua custody,
metadata tercampur, metadata hilang, dan tipe proses salah. Bukti UI asli berikutnya
juga menguji Good + BS pada owner mobile: Good saja masuk FG, biaya BS tertinggal
di WIP sampai resolusinya. Ini bukan klaim bahwa rewash/rework telah teruji.

Run tersebut menyelesaikan HTTP 95 dan 10/38 UI; native 142/16/23/12 NOT_RUN_FOCUSED.
QC bertahap 5+3 sudah lolos dengan FG 56/WIP 14, tetapi penerimaan kedua belum
bisa dibuka. Restore 533 fungsi/223 tabel persis AH dan cleanup PASS.
Artifact 10461242981, 2493952 bytes, SHA-256
`6106756a15a33287b77463e88c345c06547e96893df33a82808731719f9f10f6`.
Executor pulih; ZIP diunduh, checksum/CRC dan pemindaian pola JWT lulus.
CI juga memverifikasi ZIP counterexample QC asli 10460209095 beserta hash sumber,
penolakan backend, dan keadaan ledger sebelum/sesudah yang identik.

Kedua perbaikan adalah pekerjaan writer. Belum independent PASS, belum CP6 lock.

Run 35132647407, kandidat frontend `d7a92f00b0779d614478778bd8f1ddd367122ff7`,
tree `71b281da4455296c6f808ef28557bf4ad8f4daa4`: seluruh siklus operator desktop
melewati penerimaan 8+2, QC 5+3+2, laporan, blocker dan reversal kembali ke nol.
Parser penerimaan fisik sudah bekerja pada respons asli. Fase mobile berikutnya
memakai kembali waktu kemarin sesudah reversal fisik barusan; backend benar
menolak pengiriman sebelum barang kembali. Ini kesalahan kronologi fixture,
bukan bug ERP. Ledger sebelum/sesudah penolakan identik, FG/WIP/accrual nol,
ready 10. Tes tetap INCOMPLETE; kasus yang belum dijalankan bukan PASS.
Artifact 10461899223 (2790813 bytes), digest GitHub
`e84ecb3806d7432fd5021889d2f0a154a81c82f651eb645fcb02d2f24932b8bb`.
HTTP 95, restore AH dan cleanup selesai; native tetap NOT_RUN_FOCUSED.

Penerus harness mempertahankan alur pertama dengan backdate dan zona browser
Honolulu. Siklus setelah reversal memakai waktu fisik WIB yang diambil sesudah
koreksi, dengan jeda satu detik karena input produk menerima ketelitian detik.
Tidak ada backdate buatan yang melewati ketersediaan fisik. Tambahan lima kasus
UI menguji RETURN_UNPROCESSED sepuluh potong, biaya 70, pengiriman baru berbiaya
estimasi 70, reversal biaya lama tanpa menghapus custody, dan reversal pengiriman
baru. Total rencana sekarang 43; angka hasil baru menunggu eksekusi.

## Gate fokus selesai; gate gabungan diwajibkan

Run 35133185235 SUCCESS pada `5285a5f3e17b64ac4ae211c1ac5f6a39d57cd161`,
tree `8742b35e9bfc4cdd7987d93461b091bcb3e56a1d`: UI **WRITER_PASS 43/43**,
HTTP 95/95, unit 230, restore 533 fungsi/223 tabel persis AH, cleanup PASS.
Desktop menghasilkan FG 10/nilai 70; mobile dengan 2 BS menghasilkan FG 8/nilai
56 dan WIP 14. Semua koreksi tertaut mengembalikan saldo nol dan ready 10.
Retry-at-vendor empat potong menambah biaya 28, tanpa barang Good/BS/FG baru;
reload setelah respons hilang memakai UUID lama. Return-unprocessed sepuluh
potong memulihkan custody, mempertahankan biaya 70; pengiriman baru menambah
estimasi 70. Reversal biaya lama tidak menghapus perpindahan fisik atau dokumen
kirim baru. Native 142/16/23/12 tidak dijalankan pada run fokus ini.

Artifact 10462935592, 3016663 bytes, digest GitHub
`3a3393c859e2ef7eed5132f3c7c78d0a342a526c1a787b46c16e2344ccef7c8b`.
Gate gabungan berikutnya wajib dijalankan tanpa marker fokus. Sumber produk
frontend tetap sama dengan `d7a92f00b0779d614478778bd8f1ddd367122ff7`;
harness membedakan parser asli AI untuk diagnosis fixture historis dari parser
successor yang dipakai aplikasi saat ini. Perubahan metadata ini bukan perubahan
oracle atau aturan penerimaan. Hasil gabungan masih menunggu eksekusi.
