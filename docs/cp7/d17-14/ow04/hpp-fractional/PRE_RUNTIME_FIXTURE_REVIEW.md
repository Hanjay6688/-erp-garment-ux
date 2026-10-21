# Three setup corrections before the first Native run

The initial proposed EXPECTED bytes are retained in
INITIAL_FIXTURE_EXPECTED_PROPOSAL.json, SHA256
007fc0cf2ef00ff2abd385a6bc02c0e3df36d1bcfd0a3cb60d889acdcf4d2a52.
No Native test was executed against that proposal. These are pre-runtime
source-review corrections, not a failed run relabelled PASS.

1. The positive-snapshot zero-vector refusal case originally requested a
  20.00 financial return and CREDIT. That would create a nonzero revenue/AR
   journal and would not require a NO_JOURNAL absence proof. To exercise the
   explicitly retained unproved NO_JOURNAL boundary, the setup now requests
   refund0 and settlement=null. Source quantity, actual unit snapshot and the
   independently computed zero HPP target vector are unchanged. Product guard
   was not broadened to reject a valid positive financial return.
2. Actual Native `compute_po_hpp_gl_book_v2620e` returns only FG/COGS/OTHER.
   The fixture retains those raw three fields and derives total H solely by
   summing those actual book values, without taking it from target or cache.
3. The two-product example sells2/1 pieces. Its allocation check now requires
   those exact per-product quantities and two distinct lots. The distinct-lot
   same-SKU example still requires1/1. Both examples return1 per allocation.

Revised EXPECTED SHA256:
f53001d8ec87289a7fc7ca1a6f69752f994480418256923133329e6395a37d4c.
Revised Native fixture module SHA256:
f0a54e720c16c97adf603c5add2ad95cd8cacd7be925102f7723d15ddfc88abf.
No existing44 expected files or money/date oracles changed.

Root ran actual repository imports in each explicit32/44/58 mode with every
psycopg connection constructor trapped. All declared counts matched, the new14
case registrations matched exactly, and database calls were0. This is an
import/registration check, not a Native or financial-flow pass. The module's
fourteen rational literal checks and real writer execution remain separate
evidence. CI must run all58 cases and the complete restoration/advisor gates.
