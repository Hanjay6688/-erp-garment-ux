# Finance bridge on the complete A/B chain — Native5

A-owned integration tests exercise B's public staged-analysis caller against
A's official finance capture on the complete A/B/quote composition.

Required cases: one job/capture per request UUID; operational completion before
finance with exact official report sections and metric equality; real posting
during scanning refuses stale finance; DEFERRED creates no capture; current
permission loss hides finance and refuses new/replayed STAGED requests.

Every public operation and private capture step uses the ordinary 8s limit.
The private steps carry the requesting actor's claims as the capture owner.
This proves Native integration, not real Auth/browser, scheduling, factory3600
or independent acceptance. No posted business history is edited.

The retained strict runner rolls each case back and verifies catalogs, ERP,
Auth and session cleanup. The whole chain is removed exactly after cases.
Unknown metrics must remain UNKNOWN without fabricated numeric values.
