# Single physical-root model history — private component

The existing immutable model history capture reads at most1,000 current global
products. This new source selects one explicitly named identity root before
the Native completeness checks. It does not raise or modify the global bound.
Both root and size identify the request; size is checked after reading the root,
so a second active version with another size cannot be hidden by the filter.
Stock and sales from previous product versions remain in the same root.

The generated raw reader preserves every Native projected field, both visibility
clocks, posted/inverse journal and return association, and all50,000 non-stock
collection limits. More than50,000 stock rows retains raw INCOMPLETE. The existing
full stock digest and SQL stock summary process every selected movement; the
existing demand and reservation kernels calculate the same history/current stock.
No model, profile, target, buffer, finance calculation or model consumer is called.
The scope is explicitly SINGLE_CURRENT_PHYSICAL_ROOT, never a complete global
factory report. Queries use closed WIB days and the existing model366-day bound.

Source identity includes all non-stock facts, the full stock-row digest/count and
producer definitions. Capture time remains the actual server clock and the
earliest possible availability knowledge. Clock text alone does not retire an
unchanged source. Equal aggregate totals cannot conceal changed physical rows.

Four private invoker functions, no public facade/table/old replacement. This is
source code only: no installer/default registration or immutable capture runtime.
The current v1/v2 model/history callers and their bounds remain unchanged.
Persistence, exact UUID replay, actor/current access, current-source rechecks,
Native catalog/races/Auth/browser and model-consumer integration remain open.

Controlled SQL8 PASS: exact whole-Native row/current-stock parity,5504 product
universe, ambiguous root/wrong size, previous identity versions and both clocks,
equal-total metadata change,50005 stock rows versus a controlled full-array
oracle, non-stock incompleteness refusal, private ACL and known zero versus
unavailable. Relational fixtures and the large full-array oracle are synthetic;
no actual Native posting, past knowledge, positive model admission or factory SLA
is claimed. Initial local audit-sequencing error and5PASS/3FAIL snapshot/scope
binding comparison retained; corrected result in ow11/model-history-scope-local.json.
