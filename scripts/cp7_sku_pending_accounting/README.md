# Prepared pending-PO accounting reader

The current money candidate uses its final-cost admission rule when reading
the ledger too. A posted conversion with numeric PO costs can therefore block
accounting merely because the PO or laundry costing remains incomplete.

This separate successor derives two private accounting readers and changes
only `cost_scope_value_v3` to consume them. A genuine PO must retain its current
finite numeric HPP, unique posted/reversed conversion allocation, positive
quantity and exact finite source costs. Its source proof explicitly reports
whether cost is final. Known zero and signed cost credits remain actual facts.
Missing amounts cannot become zero. Non-PO monetary custody stays strict.

The original strict cost root, pool quotations, transaction admission, business
writers, permissions and recovery remain unchanged. The derived functions
have no direct PUBLIC, anon, authenticated or service_role execution grants.

Eighteen isolated PostgreSQL 17.5 reader controls reproduce the old pending-PO
refusal, then check provisional values, all four accounting scopes, later
invoice cents, missing/invalid sources, strict non-PO cents and private ACLs.
They use actual retained column types and exact candidate reader bodies with
explicitly modeled PO/laundry completeness providers. They grant no ERP or
Auth acceptance.

This successor is not wired into the product installer. All 44 existing money
product files remain exact at parent f1674ae84739f577571d68415beabfca3f3b832b.
Automatic rework/redye posting, inverse and full lifecycle tests remain open;
this reader repair alone does not close those blockers.
