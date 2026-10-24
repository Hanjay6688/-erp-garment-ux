# Private dated-vector target arithmetic prototype

Two private functions, no public RPC/table/caller replacement. This is not a
model selector, current-authority check or activated production target. It is
the next arithmetic component for the future consumer of qualified immutable
model-v2 results. The existing target kernel is called unchanged to validate
its v2 inputs and preserve UNKNOWN, minimum history, explicit service level
and the prohibition on two buffer modes.

For dated point forecasts f1…fn, I(a,b) is the sum over day segments within
[a,b), weighting only a partially covered day. L is lead time, R review time,
H=L+R and B the already selected days buffer. All inputs remain exact PostgreSQL
numeric strings. Final target/ROP alone are rounded upward to whole PCS.

| Mode | Reorder point | Production target |
| --- | --- | --- |
| DAYS | ceil(I(0,L)+I(L,L+B)) | ceil(I(0,H)+I(H,H+B)) |
| STATISTICAL | ceil(I(0,L)+existing lead safety) | ceil(I(0,H)+existing horizon safety) |

The statistical safety values come verbatim from the qualified shared v2
kernel, retaining its explicit historical daily variation and independence
assumption. They are not labelled calibrated model error, prediction intervals
or guaranteed service performance. This prototype creates no new thresholds.
The caller must display that assumption if subsequently integrated.

A changed forecast start date, incomplete vector coverage or unready baseline
returns the original baseline and no projected target. The vector is never
averaged over an unrelated horizon, truncated, shifted or extrapolated. Missing
values are refused, not replaced by zero. Known zero remains zero. The output
always records model_authorized=false, caller_replaced=false,
forecast_applied=false and production_go=false.

Synthetic SQL oracles include an increasing daily vector with ROP30/target70,
fractional L/R/B with ROP7/target10, exact values above JavaScript's safe integer,
last-step PCS ceilings, separate statistical safety, short/old/future vectors,
UNKNOWN and zero, closed input and private ACL. The existing local synthetic
admitted NAIVE100×7 vector yields arithmetic ROP300/target400; this does not
prove historical Native model accuracy or authorize model consumption.

First local setup failure (duplicate existing baseline schema) and first
completed report (1PASS/10FAIL: the synthetic baseline omitted its required
source refs) are retained. Only the fixture setup/refs were corrected; arithmetic
SQL and predecessor validators were unchanged. Final actual SQL: 11PASS.

Remaining integration: server-owned run selection and current checks, exact
source/policy/engine/date/actor binding during staged work and checked save,
manual/own/analog priority, shared ROP/production projections and source hashes,
UI provenance, dense qualification, catalog22/restore and actual Auth races.
