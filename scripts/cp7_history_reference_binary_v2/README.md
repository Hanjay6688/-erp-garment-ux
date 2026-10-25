# Private stock reference v2 — separate Native qualification

Native4 component qualified at c352db0a/run40190390062, complete Original
12597797025 (all five JSON files/source pins/package and restoration gates checked).
Actual363601 rows: v1/v2/v2/v1=3874.352/1312.545/1333.034/3814.404ms.
This is private encoding qualification, with no caller or request-latency credit.

This helper is not called by the ERP, default installer, model source or staged
analysis. It does not replace the v1 helper. A v2 hash intentionally differs
from v1 and must never be substituted under the v1 contract.

The generator pins the existing 15-field Native projection, both visibility
clocks, root/scope guards, UUID ordering and owner/ACL. The four textual values
become explicit UTF8 bytea before PG17 record_send; UUID, timestamptz and int8
retain their binary types. Field OIDs, signed lengths, NULL markers and exact
bytes are preserved. The outer SHA256 domain includes version, encoding and
layout hash. PG17, UTF8 server encoding and exact builtin type identifiers are
mandatory. Local PGlite18 must refuse the complete helper.

`cp7_ow12b_stock_binary_probe.py` declares four isolated Native cases: exact22
catalog/inverse/ACL; independent Python framing of actual Native raw facts,
all15-field mutations and scope/client-encoding controls; synthetic1200SKUx3size
volume with v1/v2/v2/v1 timings under unchanged8s; and an actual Native late
recorded, physically backdated stock post. Every failed and successful timing
is retained; the fastest result is never selected as acceptance.

These cases qualify only this private encoding. They do not qualify request
latency, full factory capacity, finance/HPP, a new forecasting method or any
caller integration. A separately versioned source/fingerprint/replay/unit
adapter and its complete qualification are required before adoption. Existing
archives and jobs.reference must remain immutable. Any deferred compilation
must use complete frozen captured facts and SQL summaries, never a later live
stock read by clock alone.
