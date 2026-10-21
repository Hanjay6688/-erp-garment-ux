# Native87 exact product: actual API/race/browser PASS

Product is exactly the Native87-qualified b3e6119e core; transport candidate is
b20e4e00. Native87 is reused with exact core/installer/probe/declaration/receipt
binding, not rerun or counted as transport cases.

- run39602658043/job119230812630: HTTP18/18, retained SQL races6/6,
  source-inverse races2/2, exact final gate PASS.
- run39602658042/job119230812506: browser5/5 through the actual Enteng build,
  real Auth and loopback API. All declared journeys retained.
- All report boundaries, CP6 restore/advisor/package gates and Auth/copy/session
  cleanup pass. Case counts are read from the original report JSON, not job color.

Both original artifact ZIPs were downloaded and client SHA256 verified. Every
acceptance JSON report is retained as gzip of unchanged original bytes, including
separate HTTP-completed and race package/restore reports. Auxiliary copied
browser-fixture snapshots are listed by hash but are not acceptance reports and
are not duplicated here. No UI screenshot or trace is claimed by this receipt.

Used-install restore remains a separate INCOMPLETE scenario. Full OW04, operator
entry for all backend fixtures, broader inverse/correction/APPLY/performance,
P21 acceptance and production remain open. No audit or production GO.
