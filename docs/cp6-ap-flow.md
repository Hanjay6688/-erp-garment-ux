# CP6 AP — real Auth, browser and concurrent transactions

Source boundary: `c4ccecfdaadd20081923079c608f83ac494da87d`, carrying the
unchanged permanent package qualified at `4bff4a65a7b93d7888fa77dbcb31bb1c937bbc57`.
This follow-up changes only the disposable proof harness and its documentation.
No new product PASS is claimed until the native run completes.

The new workflow reuses the pinned AC→AN bootstrap, installs the exact permanent
AO/AP migrations through their qualified closed-admission controller, and serves
only the `cp6_rollback` clone through a second local PostgREST container. Real
Supabase Auth stays on the original disposable `postgres` database. Its primary
ERP catalog/data must remain unchanged, all newly created Auth users/sessions
must be removed, and the whole AP clone and temporary REST process are disposed.
No hosted database, main branch, deployment or independent acceptance is involved.

Planned proof: 29 Auth/browser observations and six controlled HTTP schedules.
Browser actions use the original product at desktop and mobile widths; CSV bytes
are uploaded through the real file input. A lost response is induced only after
the server has actually committed. Reload recovery must reuse the exact UUID and
payload, preserve the complete ERP data boundary, and block another writer while
the outcome is unresolved. Every HTTP denial compares every ERP table's data.

Business arithmetic: edit imported receivable 14.25→17.25 after validation;
control totals are not posted; 5→7 accessory PCS at manual 3.25 produces 22.75,
with the 36.00 dozen master unchanged; pocket stock 20→15 creates expense11.25
without product HPP; optional period allocation uses existing posted sewing
events, moves that same cost into production without another stock deduction,
and linked cancellation restores expense before stock reversal.

Concurrent schedules cover same-UUID import finalization, edit before finalization,
accessory stock contention and duplicate requests, pocket stock revision
contention, and a busy period allocation followed by the same-UUID retry.
Waiting requests are admitted by observed PostgreSQL lock waits, not by assuming
that two quickly issued requests overlapped. Setup-only native fixture calls
are explicitly separate from real JWT business commands; no grant, installed
function or policy is changed for the new transport proof.

Existing 105 installed native cases,38 atomic refusals,two full package cycles
and six maintenance schedules retain their earlier evidence. This follow-up
does not reclassify those as fresh transport tests. Legacy opening overlap,
the old global audit source gate, independent review and owner acceptance remain
separate unfinished CP6 work. CP6_HOLD; production_go:false; CP7 unopened.

The prior nine-item archive/master save timed out without receipts. Read-only
reconciliation still shows both master files at v15. No duplicate write was made;
the pending local v16 bytes must not be treated as confirmed persistent masters.

First attempt `70acd4e0089470f41411fed3eee1d18b3fb7c792`, tree
`a3d66756552363d4e39819f975ec55fa13adc977`, run35747092468 is INCOMPLETE.
The browser login-page smoke passed. Fixture setup then attempted two different
role codes with the same active role name; canonical `erp_save_role_v1` correctly
refused the second name with23505/409. The follow-up gives each synthetic role
a distinct name and strengthens ledger observers to compare every account plus
the actual22.75 accessory receivable journal. Product/schema/permissions are
unchanged. The failed attempt remains evidence, not a business PASS.

Second attempt `36afa345be84489f0a65a93e50976e2479b89dba`, tree
`91ff9bf81b9fd6810c4524408dd643cc49640434`, run35747713442 completed17 observations:
login-page smoke,three owner HTTP readers,twelve denied writer calls with complete
ERP data boundaries,and real browser password login. Creating the import draft
also succeeded. The exact-label selector for the implicit `Jenis data` label
failed because its accessible text includes its select options. The retained
screenshot shows the correct empty draft and enabled upload form. Follow-up uses
the combobox role and label prefix; it does not force a click or mock responses.
Both attempts preserved all7148 AP catalog entries,the primary ERP data,and zero
Auth/clone/container residue. Attempt1 ZIP SHA256c6266e092c081fe204ba877c150de9153ba3203270b8249c5ff7f797f99369aa;
attempt2 SHA256b1eb2e9662fb4704de6f437df283371a48df8911faf29a8db83d192af686df59.

Third attempt `7c2f5e045c98bb190407237e0bf17db3c45e7b8a`, tree
`e8b133d729c326fc244c31799343e40054200733`, run35748462817 completed21 observations.
The complete CSV/edit/control/finalize/lost-response/reload/global-lock sequence
passed through real Auth and HTTP, posting exactly17.25 once. The accessory
workspace correctly rejected frozen legacy fixture UUIDs with zero version and
variant bits. Its writer stayed disabled. Follow-up applies the already-used AN
browser fixture transformation before insertion into a new clone, with original
and transformed source hashes and a collision-checked identity map. The frozen
seeds,the product parser,and posted rows are not edited. Artifact10703528329:
2768296bytes,14entries,SHA25616eacbdcaad5b2e761bed3a8f69d9344491978a99adb6d3d48a216f3d4ef52c8.

CodeQL35747713380 identified one `js/file-access-to-http` finding in the new
harness: JSON fixture bytes flowed into a local HTTP request. The fixture file
is now output-only evidence. The runner resolves known synthetic master keys
directly from the verified disposable database before building requests; neither
the browser nor the HTTP race runner consumes fixture files. The existing
CodeQL rule and zero-findings gate remain unchanged. Finding artifact10703687143,
SHA2564f9709822f003cfa4cda4147b4095e9683c14d9565f564dd6c4e0091c0d4b336,remains evidence.
