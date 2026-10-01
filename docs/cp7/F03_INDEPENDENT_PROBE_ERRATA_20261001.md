# Auditor probe corrections — 2026-10-01

Product remains frozen at `eb6b8682e97e94c95f89d431ab81974c54ddcbaf`.
No product changes or business expectation reductions accompany these corrections.

First independent run: https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36911271122
Probe commit: `3d3aa55fc2fda3fded11e8fb1efe2858e1f73722`.
Receipt: artifact `11186323645`, SHA256 `400ed758a7ec8d1c0eacd16a07e2a76c98b4faf98ca7306a5eb7e42ae3da07da`.

The first receipt has 20 PASS and 3 INCOMPLETE, with restoration and cleanup intact.
These three incomplete cases are measurement defects in the auditor probes, not
established product findings:

- N14: the impossible date `2026-02-30` is refused by PostgreSQL with `22008`.
  The initial probe only accepted application query errors. The correction
  requires this exact date error and unchanged state; all other malformed
  queries retain their original expectations.
- Desktop and mobile recovery: the pending/reconcile component becomes visible
  while the network request is still running. The initial probe asserted that
  its response-loss callback had already completed. Captured database facts
  already showed the intended one payment of 123.45 and remaining AR 136.40.
  The correction waits for the actual HTTP 200 response and completed response
  abort before checking recovery. It does not mock a success or change money,
  stock, UUID, persistence, or failed-refresh expectations.

Both corrections must pass a new complete execution before acceptance. Preserve
the initial receipt and final receipt together; do not relabel the first run green.
