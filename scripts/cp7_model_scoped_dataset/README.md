# Scoped immutable observations for model evaluation

Three private functions derive the existing Native model dataset from one
actor's immutable single-product history captures. The target, size, period and
grouping are exact. The existing500-capture and20000-series bounds remain; only
the selected target consumes its capture budget. Unrelated products do not
require the old global1000-product history source to become complete.

The generated Native adapter retains the existing revision algorithm and uses
actual capture times as knowledge times. Repeated identical daily meanings do
not create new revisions. A correction retains the earlier observation and
adds a later revision. UNKNOWN and stockout remain separate from observed zero.

The wrapper reuses the existing reviewed policy binder and assessment kernel.
It checks current actor/access and scoped source before and after building the
input. A policy recorded after the history capture cannot approve that older
capture. Runtime, source and model engines remain bound to the input.

Local8PASS uses actual scoped capture/history/model SQL with controlled ERP and
auth primitives, plus explicitly synthetic duplicate rows for bound controls.
No actual Native/Auth/concurrency qualification is inferred. A separate Native4
suite checks composed catalog inverse, actual policy/knowledge times, actual
SALE and current access, and synthetic2000-product/202000-movement volume.

No public facade, table, old replacement, policy default, forecast application
or model caller is added. The exact22-catalog opt-in installer requires the
scoped-history and v2 policy/adapter parents. A retained model evaluation and
its target consumer require separate integration and after-use restoration.
