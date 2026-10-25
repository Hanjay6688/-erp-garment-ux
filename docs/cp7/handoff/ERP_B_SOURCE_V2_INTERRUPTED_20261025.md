# ERP B — titik lanjut setelah lingkungan kerja terputus, 25 Oktober 2026 WIB

Permintaan owner: lanjut dari chat “Ambil alih konteks ERP”, pahami konteks/scope/tujuan lalu lanjut tanpa bertanya. Scope dan pembagian dua penulis tetap berlaku. Ini titik simpan akibat layanan eksekusi tidak tersedia, bukan penyelesaian scope.

## Otoritas dan status

- Repo Hanjay6688/-erp-garment-ux; branch B `astra/d17-14-produksi`.
- Parent kode yang sudah dipublikasikan: `0243e23b4cd1e2cb6d5ff4958c071d2f013f8072`; tree `374a6206ff227dfeccd820ada0500c76a16ced30`.
- B: OW16, OW10, OW11a/b, OW12b, OW13a/b/c, OW14a/b tampilan/aturan. A: finance/stok/HPP/laporan, OW06/07/08/09, shared installer/default bundle/generated types/registry dan integrasi/audit.
- Tidak mengubah main/integrasi/cabang A, frozen audit, supabase/**, produksi/hosted/Enteng/WA nyata. Formal 5/16, CP7C belum diterima, independent acceptance false, production_go false.
- AGENTS.md: lanjut melewati checkpoint/commit/CI; pertahankan kegagalan pertama, jangan rerun untuk angka hijau. Jangan spawn agent. Model rumit hanya aktif dengan histori dan kebijakan eksplisit yang cukup; UNKNOWN tidak menjadi nol.
- Posted history immutable; kedua jam fisik/pencatatan; latest corrected wins; method/actor/UUID/payload persis; akses kini diperiksa setelah tunggu/replay; satu target kernel; tidak ada stok/WIP/cadangan ganda.

## Bukti baru yang sudah dibaca

### Physical binding Native4

Head 7b70bb2e5b34180c5767d50fb643ad53880b7cd3; run 40128497581; job 120974960124.
Complete JSON artifact 12574910914, 158852 bytes, SHA256
c402171c72f249f5f32a84ba4a0ddc3d8552579286cb18af0c28fc03b744eb90.

Archive diunduh dan SHA/ukuran diverifikasi, seluruh JSON diparsing. Empat case PASS:
exact22 inverse/partial refusal; draft-post-return-inverse Native; dense2000/202000;
actual backdated physical/new system clock. Target dense 101 baris stok, 95.292/86.769ms (bukan SLA).
Enam source pin dibandingkan dengan exact head dan working source. Semua package gate,
CP6/advisor, boundary, public schema, session leak nol, business day, auth user sebelum/sesudah
sudah diperiksa. Job success dan database disposable dihapus. Receipt ringkas tersimpan bersama catatan ini.

### Version selection Native4

Head 8ab4b7e1a1d2a623d5557502ae581f52caedee39; run 40127943408; job 120973286538.
Complete JSON artifact 12573938163, 158554 bytes, SHA256
2fb4da1ad59dc05b76e990c066e7969efc8ca9827d15bda43374c98f05b3de57.

Archive diunduh, SHA/ukuran diverifikasi, JSON diekstrak. Main Original dan semua empat body case
sudah dibaca: exact22 inverse, actual v2/v3 same request UUID with distinct run namespace,
newer v2 displaces older v3, source after SALE/current access, dense2000/202000 472.39ms.
CP6/advisor true; job success dan database disposable dihapus.

**Verifikasi akhir seluruh source pin exact-head/current dan seluruh package gate belum dieksekusi**:
lingkungan putus tepat sebelum perintahnya. Observation dipisahkan dari receipt selesai.
Jalankan verifikasi itu sebelum memberi kredit release penuh. Jangan rerun CI yang sudah lulus.

## Perubahan lokal yang BELUM dipublikasikan

Workspace terakhir:
`/workspace/scratch/282188edcd04/erp-produksi`.
Bukti privat:
`/workspace/scratch/282188edcd04/evidence-private`.

Environment `ccarenv_b64_Y2NhcmVudl82YThmN2VhODU4ZTQ4MTkxOTE3M2I2ODk5NzFkMGI2NQ`
dinyatakan unavailable oleh platform. Percobaan read-only terakhir ditolak dengan
“No usable execution environment is available. Wait for an environment to become available before using this tool.”
Tidak bisa membaca diff atau menyelamatkan berkas lokal setelah itu. Jangan menganggap kode
di bawah sudah tersimpan di commit atau paket permanen. Periksa keberadaan workspace terlebih dahulu.
Jika masih ada, jangan reset/clean: pertahankan semua perubahan dan log pertama.

Berkas baru/berubah:

- scripts/cp7_model_target_source_v2/{stock.sql,non-stock.sql,physical.sql,source.sql,reorder.sql,__init__.py,MANIFEST.json}
- scripts/cp7_ow11_model_target_stock_batch_local.mjs
- scripts/cp7_ow11_model_target_nonstock_batch_local.mjs
- scripts/cp7_ow11_model_target_source_v2_local.mjs
- docs/cp7/d17-14/ow11/model-target-{stock-batch,nonstock-batch,source-v2}-local.json
- scripts/cp7_ow11_model_target_source_v2_{cases,probe,preflight}.py
- .github/workflows/cp7-ow11-model-target-source-v2.yml
- scripts/cp7_f05_analysis_probe.py (own Native4 route only)
- Local physical-binding receipt (remote checkpoint has a compact fully verified equivalent).

### Batch source implementation

Private schema cp7_model_target_source_v2; no default caller/public RPC/table replacement.
stock_digests reads complete selected-root stock once, keeps full Native row framing, product
versions and both visibility clocks, exact parity with cp7_history_reference.stock_digest.
non_stock_rows validates global caps first and groups sales/returns/original journals/reversals
once; multi-item invoices must not duplicate journals. physical_rows binds every selected-root
reference to the exact same single-root physical identity, independently verifies complete
raw stock, and preserves INCOMPLETE/raw omitted status rather than inventing empty stock.

capture(c,p_limit) binds all current products to latest actor-owned immutable evaluation across
GLOBAL_V2 and SCOPED_V3, exact method and run namespace. Newer baseline/stale displaces older winner.
Global v2 delegates to unchanged legacy source. Scoped v3 binds stored input/history/query/hash,
calls existing current_guard and compares target physical source. Rechecks live global capture,
batched full stock digests, latest selection, access, policy, engines, producer and WIB day before
returning stable cp7.model-target-source.v2 identity. No forecast math is added. Alias actor was
renamed v_actor to avoid PL/pgSQL column collision.

capture_for_reorder preserves warehouse-only permission. Without all four model read rights,
it returns explicit baseline/current-access-required rows and NULL model/policy/history,
not archives from another role. It still checks source boundary, current warehouse access and clocks.

Installer candidate composes unchanged four legacy source functions verbatim plus seven new
batch functions, two private schemas, no tables/RPC/replacements. Strict22 predecessor catalog,
function body/owner/ACL/settings and pinned dependencies, atomic RESTRICT inverse.
**Review inverse external caller detection for BOTH owned schemas**: draft currently searches
only cp7_model_target_source_v2 references; it should also protect legacy source callers.
Review engine identity before future consumer integration: include future consumer-v2 definition
in source engine hash when that consumer is introduced.

Latest observed file SHA256:
- stock.sql: 41fad9ed186091b4a374ae094a5ce49235ae7d4e18d8ac2bc517b8c0e8a5e95d
- non-stock.sql: 4e69abb0083104bc6a7ba5aec3919bc8e6de79c1d00ea8a53969b2fa83bb9393
- physical.sql: ddbff254a17b6068ac5d2306c4f12355a148809054e8820b219862f075b0f121
- source.sql: 4d6b2d92c82faf17410390c8cfd218a7e5d49ffe5b058c9c77b96098467ddbfd
- reorder.sql: ab1619d8ba4b35a1026af8d11611e02316b4875d91a171e5fd65c397b124c352
- __init__.py: cd624bf0a1277208b221648be32aaf1979fba877552bba04559f113397cc6af9
- MANIFEST.json: 7fe26d862e1bfd60048674a28ae4dd7cbf8ad933305501bc38d478475d478ba5

### Local verification already executed

Actual PGlite SQL with synthetic rows/controlled parents, **not Native/Auth/concurrency credit**:
- stock batch: 4 PASS; exact single-root parity, product versions/empty target, both clocks/full row fields/bounds/private ACL.
- nonstock + physical batch: 7 PASS; journals/reversals, global caps, empty vs unknown, exact single-binder references, scope/clock/digest refusal.
- full source + warehouse wrapper: **7 PASS**, last report read directly from disk after fourth run.
  No model explicit NULL; scoped baseline runtime/source; controlled eligible exact forecast and stable
  clock-independent hash; newer global baseline replaces older scoped winner; physical/access/new-model
  changes during controlled recapture refused; corrupted stored binding refused; warehouse-only no disclosure.
  Actual shared assessment/current_guard SQL used; positive history is explicitly synthetic.
- Installer verify_sources import passed; Native installer/catalog execution NOT YET DONE.
- New Native4 cases/probe/workflow/F05 edits were written but NOT YET preflighted/run/committed.
- Native declaration docs/cp7/d17-14/ow11/MODEL_TARGET_SOURCE_V2_NATIVE_CONTRACT.json
  **has not yet been generated**. Do not publish/trigger the incomplete candidate as ready.

Retain logs:
model-target-stock-batch-first.log;
model-target-nonstock-batch-first.log;
model-target-physical-batch-first.log;
model-target-source-v2-first.log (test-script illegal await in default parameter, fixed);
model-target-source-v2-second.log (5 PASS / one fixture invalid policy state REVOKED);
model-target-source-v2-third.log (6 PASS after using real SUSPENDED state);
model-target-source-v2-fourth.log (7 PASS including warehouse boundary).
These are test-fixture faults, not relaxed product assertions.

### Native4 candidate intended checks

cp7_ow11_model_target_source_v2_cases composes selection parents + private binding + new source.
Cases: exact22 inverse; actual v2/v3 latest + SALE and old-capture refusal; actual current access,
foreign actor and warehouse-only null disclosure; dense2000/202000 with two actual scoped model captures,
all global products represented, exact source hashes and elapsed <8s (not SLA).
Helper resets session authorization then SET LOCAL ROLE cp7_capture retaining actual JWT claims.
No synthetic positive Native winner/backdated recorded history is invented.

Before run: check all helper field names, producer recipe exactness, installer ACL/function settings,
both-schema inverse protection; pglast/PL clash; old F05 admissions and new route; YAML; source/declaration pins.
The copied workflow preserves the existing isolated PG17/package/bootstrap authority and old budgets.
New flag requires scoped evaluation and rejects selection/binding/browser/transport combined routes.
Do not change A-owned shared default installer, generated types or RPC registry to make checks green.

## Next steps, in order

1. Recover workspace access. Inspect git status and diff without reset; compare the parent to the new
   documentation-only checkpoint. Preserve local code and first logs before integrating this checkpoint.
2. Finish source/package verification of selection Native4 Original. Binding receipt is fully verified.
3. Read all source-v2 draft code; fix both-schema inverse protection; generate exact Native4 declaration,
   pin source/probe/helper files; run preflight/SQL clash/YAML and only necessary local retests.
4. Commit/push the exact reviewed source candidate to B with expected-head guard, monitor Native4 until
   Original is available, retain first failure and fix its cause. No rerun merely for green numbers.
5. Continue new versioned consumer/provenance/resolution/cache/hooks/client integration; existing
   cp7_model_target_source v1 / consumer v1 only consumes GLOBAL_V2. Do not alias scoped history into
   global history or relabel old immutable archives. One existing projection kernel only.
6. Actual target Auth/lock/browser and after-use composed restore still required. Current browser proof
   uses existing paged staged entry, not new bounded RPC/full3600 proof. Activation needs actual
   chronological data and explicit policy; no invented winner.
7. A-owned source ownership registry remains open (24 preexisting + 4 scoped RPC omissions);
   KOORD127 already requests A integration. Keep shared registry unchanged.

## Earlier durable evidence

Stable evidence package libfile_ce3c35e57b4081918379ceb7dd6f10b8 version66:
557 entries, 62815798 bytes, SHA256
229adf561e0277e6e2a3e3d026d28e52e8a9c2931cd2e540e524374f82429293.
No version67 upload occurred in this segment. Do not replace it from a stale local version.
Latest published complete scope details are KOORD133–137 and parent receipts.
Scoped Transport7, Dataset4, Browser2 and earlier target Native6/Transport11 evidence remain as recorded.
Both newly checked server jobs are finished; no chat task continues in the background while environment is unavailable.
