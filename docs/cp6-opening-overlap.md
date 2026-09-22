# CP6 — legacy opening overlap investigation

Incoming product: `34b03848b03192845ab44dc43c8e28706099397c`, AQ qualified at
`5ae73305e118f3641202ae4070ae2264c92de44b`. CP6_HOLD.

The imported financial source checker already refuses a new import when the
same party has a posted legacy opening. The reverse route calls the canonical
`erp.post_opening_balance(uuid)` after an import and does not consult that source
registry. This probe tests the suspected asymmetric ownership and the adjacent
cash, material, FG, WIP and BS opening family on the committed AQ runtime.

No product definition, grant, policy, migration or historical assertion is
changed. Public imports use the ordinary authenticated actor. The legacy route
uses the native canonical function with the same owner JWT claims in an
administrative test connection; this is not evidence of browser/HTTP access to
the private schema. Each counterexample must restore every ERP table and the
complete AQ function/catalog boundary. The original AN database stays unchanged,
and the clone is removed. A successful probe means a defect was reproduced,
not that the product is corrected or CP6 accepted.

Status: native probe pending. Product repair, concurrency and combined acceptance
remain unfinished. Existing AO/AP/AQ migration and rollback bytes stay immutable.
