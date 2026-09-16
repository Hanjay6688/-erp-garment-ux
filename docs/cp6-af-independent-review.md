# CP6 AF independent review

Candidate AF is frozen at f46699865501b03f9fba3a8b188f3fd01eedf404, tree
f4dad6a6bccfffa1ba01f542cac36ac1d100c63f. Review harness commits are separate
identities. The native runner checks out original AF and its immutable AC base;
all AF runtime, grants, SQL, original tests and fixture dependencies stay exact.

The independent question is whether a reserved sales draft can change product,
warehouse, customer, physical date, or draft owner without rebuilding its stock
facts, and then be posted inconsistently. Price/notes changes, proper RPC edits,
idempotent draft replay, cancellation and quantity-refusal are controls. Five
opening parent controls check the AF repair. These are hypotheses until the new
native results exist; no source-only finding is counted as a business bug.

Every operation uses a synthetic ordinary OWNER session. Fixture administration
creates master records and temporarily supplies the already disclosed missing
schema USAGE. No additional table writes are granted; no posted row is altered
by the fixture administrator. The entire transaction, schema privilege and
runtime catalog must return exactly to their original state.

Original AF Native10 passed 7 admission, 30 focused, 11 report, 134 combined,
4 two-session, 20 maintenance and 8 rollback cases. Exact artifact 10429202482,
SHA256 f35be1721e99df6ce2c03662b1ae6856f38e9886dcfc8fe5165ba12e2737696c,
is verified before reusing those results. Both old workflow bodies are restored
byte-for-byte by the scope checker. Unknown source changes cannot use this route.
The new native runner uses the same pinned PostgreSQL17.6 image and CLI2.116.0.
Routing SUCCESS is not independent acceptance or a new historical matrix run.

One material root cause is one family, even with multiple variants. Finish all
related fixes before a relevant combined gate. Notify the owner before starting
a large matrix, explaining invalidated prior evidence and affected families.
Only the competition branch may advance, fast-forward; check it before writing
and before push. CP6 only, production_go:false. HTTP, UI, and CSV end-to-end
reachability remain BELUM TERUJI. A successor writer needs another reviewer.

Reliable data adalah dewa. Keuangan, laporan, stok, dan HPP adalah raja.
VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
