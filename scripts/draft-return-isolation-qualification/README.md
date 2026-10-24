# Sibling draft return isolation candidate

Actual Contract6 at7a7110f7 passes six baseline controls and five current
controls. The sixth current control atomically rejects a wrong-customer draft,
then wrongly refuses a separate valid return on the same sale. The raw Original
is byte/hash verified before this database runs. The positive control remains.

The proposed delta changes one exact condition in locked_source_family: a
DRAFT RETURN's customer is a dependency, not a posted financial assertion.
Its actual row, items and source lock IDs still enter the source hash. Posted
customer proofs, journals, locks, permissions and all other SQL remain exact.
The selected wrong draft still fails the unchanged Native active-source check.
The old source file and old Contract6 tests/results stay unchanged.

Four regression controls run on the unmodified current installation and then
with the delta. Both counterexamples must be reproduced before the fixed group
can pass. Controls retain source-rebinding refusal and the three-piece/refund60
allocation limit. The malformed sibling is never deleted or corrected to make
the valid return pass. Read-side data/sequence equality is checked directly.

Full22 delta admission allows exactly one function definition change and no
metadata or privilege change. Inverse checks all rows and sequences before DDL;
the used positive-control case must refuse inverse without side effects. The
exact pre-use inverse, current predecessor verification, CP6 restore and advisor
and package gates remain mandatory. This candidate is not added to the current
installation entrypoint. Complete after-use backup/restore and broader regression
qualification remain necessary before integration. No independent acceptance
or production permission is claimed.
