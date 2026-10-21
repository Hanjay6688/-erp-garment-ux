# Writer review: preserve the complete nominal input

The initial consumer UI draft incorrectly limited typed amounts to16 integral
digits and the HTML input to20 characters. The retained backend accepts the
Native18-integral-digit cent maximum,999999999999999999.99 (21 characters).
A new literal counterexample failed on that draft: the client returned null.
The original failing log is retained. The frontend lexer and reader cents now
retain exact arbitrary-length decimal strings using BigInt, and the HTML amount
field has no maxlength that can truncate cents. Source/date/amount capacity,
Native poster and actual complete financial command guards remain unchanged.

All104 relevant protocol/parent/recovery/dependency regression tests pass after
the fix. The existing synchronous-edit DOM case now also requires no maxlength.
The current browser lost-reply journey additionally fills the exact Native cent
maximum and checks every character survives; this fixture's target remains500,
so review/save must remain disabled. It then restores the ORIGINAL80.00, starts
a fresh review and continues the same frozen money/date/recovery case. No new
large financial amount is posted and no old EXPECTED.json byte is changed.

The first current-product browser8 candidate f41acbaee77ef20b3a498317103d2d16b9507ce0
remains frozen/running independently. This review is a subsequent source change;
its actual browser proof must be collected on the updated source. Local104 tests
use declared stand-ins and are not actual Auth/Native/browser qualification.
