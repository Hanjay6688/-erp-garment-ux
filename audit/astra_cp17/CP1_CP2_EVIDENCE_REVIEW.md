# CP1 / CP2 evidence review · Astra · 14 October 2026

Candidate `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Neither historical phase is silently omitted.

## CP1: reconstructed baseline and retained history

Independent execution of the candidate's G-01 workflow: run **38525347357**, job **115724292447**, attempt 1. The complete artifact 11875532346 has SHA-256 `7b308da33f1b8c601ab8709347bc8a3d30ea3c6024ccf632c7317009779f2109`.

The aligned disposable v2.6.20 catalogue matches all 15 populated non-platform-ledger categories against the committed historical hosted measurement. Both platform ledgers have 70 entries, but their digests differ: hosted `70101c86a76c027079b6ccec793cde92`, reconstructed `5c62742300c1b4b7059b134fdbd6b052`. This is the exact, previously documented fixture difference: repository version stamps and empty bootstrap ledger statements. It is not a new unexplained runtime drift and is not an all-ledgers-byte-identical result.

I independently hashed every one of the 19 repository SQL files mapped by `docs/evidence/cp6-g01/ledger_content_order.json`: 18 match historical statement bytes; one matches with its declared final-newline difference. `CP1_LEDGER_BYTE_CHECK.json` retains every current byte count, MD5 and SHA-256. Historical order is evidenced by the committed mapping. The remaining 51 historical ledger entries have no separate local SQL file and are structurally covered by the frozen catalogue bootstrap. This test does not independently replay those 51 historical commands.

`check-backend-ownership-v3.mjs` freezes reviewed predecessor manifests and SQL bytes, but the current `check:backend` command deliberately checks that script in a detached CP5 predecessor worktree. Its PASS alone does not prove the current overlay. In integration run **38527771239**, the current source guard passed for **291 runtime files and 243 owned RPCs**, without orphan RPCs or direct frontend reads; predecessor ownership passed for **89 effective unique owners and 66 byte-bound CP5 files**; all `check:cp6` static guards passed. Full logs are in artifact **11876413432** (SHA-256 `a1252b841ed76247e7cac7885bb4347e3b571c1c30105f409a7a7c7a22f8af2b`) and the preserved job log. These are static ownership/history checks, separately identified from G-01 and the business runtime cases.

No fresh hosted query was made. CP1 historical acceptance reports remain absent as separate full reports; the evidence is the retained schema/ledger metadata, source guards, and the new disposable reconstruction. Disposition: **VERIFIED WITH THE STATED HISTORICAL LIMITS**, not certification of the current hosted system.

## CP2: archival recovery is evidenced; database restore is not

The forwarded Fable summary says there is no accessible backup/key/restore set. That accurately describes the current audit session's available payloads, but **“there is no CP2 evidence in the repository” would be incorrect**.

The immutable candidate contains `docs/cp7/evidence/writer-resume-20261005/CP2_ENCRYPTED_RECOVERY.json`, explained in `WRITER_RESUME_20261005.md` and `RESUME_QUALIFICATION_20261005.md`. The writer records two byte-identical encrypted sources, successfully opened with AES-256-CBC / PBKDF2-HMAC-SHA256 / 600000 iterations. Its evidence inventories all **149 members**, comprising **146 parseable JSON members and three UTF-8 SQL members**, with individual hashes and CRC checks. Encrypted SHA-256 is `f4a7e060b3d9d60b9e04ed6bf2afd3f15e6b8af74f030fb4c11914d070ed75a1`; decrypted archive SHA-256 is `e176cac94d78915cb5fd73a065f58150184ee0b37801e6eb70fbc8fcfa29ef53`, 886497 bytes.

The receipt explicitly sets `old_business_results_semantically_reaudited:false`, `key_values_exported:false`, and `decrypted_database_rows_exported:false`. It is a writer-origin archival-recovery receipt, **not an Astra re-decryption or a demonstrated PostgreSQL restore**. No secret/key was requested, retrieved, or exported by this audit. Source identifiers are not key values.

Missing independent evidence: an authenticated original ciphertext payload/hash check by the auditor; the exact restore recipe and target engine; an isolated restored database's complete inventory and schema/owner/ACL comparison; data/control totals and baseline business invariants after restoration; first-failure logs and cleanup proof. Catalogue reconstruction for CP1 and the modern CP7 backup drill do not substitute for this historical recovery set.

Disposition: **ARCHIVE-OPENING RECEIPT REVIEWED; HISTORICAL DATABASE RESTORE CANNOT BE VERIFIED FROM THIS SESSION**. Recommendation: the writer/owner who already holds the original set can produce a disposable CI restore receipt with the secret remaining in their controlled environment. Do not label CP2 PASS, request keys, or weaken the existing CP7C/Drive hold.
