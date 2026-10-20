# Source completion must follow the Native header/HPP tail

Retest result: candidateef98e6e6 passed44/44 on
run39489386389/job118858149684, including both previously incomplete cases.
Restore and advisor gates are true; the original44 IDs and monetary/date
goldens remain unchanged. The full runtime and receipt are preserved in
CI_EF98_NATIVE44_RUNTIME.log.gz and CI_EF98_NATIVE44_PASS.json. The first
42PASS/2INCOMPLETE result below remains part of the evidence lineage.

Candidate80b97175, run39486961564/job118849751690, ran all44 declared cases:
42 PASS/2 INCOMPLETE. `P11_READ_NATIVE_LIFECYCLE` and `OW04_NATIVE_EMPTY_N10`
failed with `CP7_NATIVE_EMPTY_FINAL_AR_OR_STATUS` on payment inverse. All12
initial paid settlements and11 of12 new Native EMPTY cases passed. Restore
and advisor gates passed. The complete first log and both traces remain in
CI_80B9_FIRST_RUNTIME.log.gz and CI_80B9_FIRST_FAILURE.json.

The admission transform called PAYMENT_REVERSE completion immediately after
marking the payment REVERSED, before Native recomputed the invoice status.
For the actual80/30/20 fixture the money was already NET60/P0 while its header
still said PARTIAL_PAID. The strict new final closure correctly refused that
intermediate state. This is a product-hook ordering defect, not an oracle or
environment failure. PAYMENT and RETURN_REVERSE had the same early placement.

The correction moves each completion and its following current-authority
recheck to the terminal tail, after Native's actual header, HPP and audit
statements. SALE_REVERSE already had that placement and stays identical.
Current effective-payment calculation remains before the original money
guards and header CASE. After removing only the moved completion/authority
pair, old and new transformed source bodies are whitespace-equivalent. No
Native monetary, physical, chronology, original-authority or replay statement
is removed. Any final exception rolls back the same transaction. The complete
strict Native EMPTY validator is byte-unchanged.

The unchanged P11 reader lifecycle remains the original regression. N10 is
strengthened within the same frozen case/expected: inverse payment30, post a
new Native payment60 at the actual current instant after the inverse, inverse
the return (NET80/P60, PARTIAL_PAID/AR20), inverse payment60, inverse sale.
Both OWNER and genuine null-human variants must return all GL accounts and
stock10 to baseline. No backdated intermediate funding excess is fabricated.
All44 IDs and the original expected money/date files remain unchanged.

Source/fragment controls and their declarations are in `source-completion-fix/`.
Nine isolated checks reproduce the stale-header refusal, accept the final
Native UPDATE result and retain negative-money refusals; these are fragments,
not Native posters or authority tests. Independent internal source counter
also checks3 Native and3 private-copy derivations. The fresh Native44 retest
recorded above was required; previous42 PASS remain historical evidence only.

The UI wire check separately reuses the12 actual initial settlement pairs
from3f7e0329 with the exact inert proposal parser (12 pairs,72 assertions).
This proves source-wire compatibility and fail-closed parsing, not a new
Native execution, active frontend integration, HTTP or browser result.

OW-04 remains open; `feature_complete:false`, `audit_complete:false`,
`production_go:false`.
