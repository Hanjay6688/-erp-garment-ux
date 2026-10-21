# Pending two-invoice Native fixture and financial observation

consumer/cp7_ow04_consumer_fixture.py prepares the already-declared source
1000/P1000/return200/I200 and a separate500 invoice for the same customer.
Preparation uses the existing Native settlement, found-stock and public
CREATE/POST writers, with the retained explicit period/master fixture labels.
The two stock lots/products are separate. The helper makes no connection or
commit and is not registered by the Native harness. Its prepare function has
NOT been executed. No consumer command or Native case is claimed.

The nine preimplementation arithmetic expectations remain byte-pinned at
437c6b2f0fe338e96a4880b6acff01e6af2f79d4f9d8ef0de29c0b4676be22ac.
The future observer compares public invoice financials with raw P/U/I and
actual document-owned GL. It retains original/inverse journals, all signed
recognition parts and incoming consumption journals. A customer-wide GL sum
cannot establish each invoice balance when both belong to the same customer.
The fixture pins AR IDs to actual original SALE lines before later operations;
it does not rediscover a new mapping during observation. A note-restatement
family is explicitly outside this bounded fixture and refuses observation.

Validation so far: Python compile, import with zero database calls, frozen
nine-case arithmetic input check, float-oracle refusal, and six local PGlite
controls on the exact extracted document-AR SQL. The latter use a minimal
synthetic ledger, including80+120 use, negative80 restoration, an unrelated
same-customer invoice and Native-style return inverse plus signed I adjustment.
They are SQL-reader controls, not execution of any Native business operation.
The product's APPLY/UNDO writer, UUID/current-rights protocol, complete family
reconciliation, journal provenance and deferred closure remain unimplemented.
