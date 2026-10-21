# Actual Native failure and source correction

Run 39553532036 / job 119067883100 on candidate
`8ed949bb4c0ebaacae5cf83653174799936374f4` executed all 63 frozen cases:
59 PASS and 4 INCOMPLETE. Restore and advisor gates passed. Full original log,
case records and their hashes are preserved beside this disposition.

The four source-inverse cases reached the real product function
`cp7_credit.source_inverse_proof_v1` and failed with PostgreSQL `22P02`:
`p_before->'sale'-array[...]` groups the operators incorrectly. The same
unparenthesized extraction existed in the terminal-header proof. This is a
product SQL defect, rather than a passing Native result or a fixture problem.

The correction adds parentheses to the four JSON extraction operands in
`03_native_inverse_proof.sql`. It leaves the permitted header fields, comparison,
money, dates, stock, HPP, permissions and all 63 expected cases unchanged.
The source-pin manifest is regenerated from the same accepted predecessor;
only this source hash and provenance commit change. Local expression execution
reproduces both original failures, then checks both corrected predicates against
identical, lawful mutable-header and three immutable-header changes.

A new Native 63 run on the exact corrected candidate is still required.
Local PostgreSQL 18 checks do not replace Supabase Native 17 qualification.
This subset does not close OW04 and does not authorize production.
