# Used CREDIT/REFUND restore: first failure retained

Candidate `b20e4e00f500e70d65fbd590cc9d2541c43a6529`; run39602658117,
job119230812382. This scenario is **INCOMPLETE**, not a product restore PASS.

CREDIT and REFUND committed; every one of641 non-system table hashes matched
after a fresh full-dump restore. The authoritative-read comparison then failed,
before any restored inverse command. The original clone was fully restored:
all CP6 boundary/public/function-owner-ACL components are true.

The qualifier set the restored session to Asia/Jakarta while the retained source
fixture had set UTC. Review tokens hash timestamp JSON text, which depends on
session timezone even for the same physical instant. A local PGlite control
reproduces that distinction; it does not prove the next Native restore result.
The correction uses UTC for both sessions and records exact before/after reads.
The equality assertion, original fixtures, amounts, source-inverse oracle and
strict OID seal remain in force. No restored source inverse PASS is claimed.

The artifact ZIP digest was client verified. All five JSON reports are preserved
as gzip of their unchanged original bytes; both raw and gzip hashes are in the
receipt. Gzip representation was generated locally with mtime0.
