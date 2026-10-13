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

## Retained browser transport preflight

Run36911723469/job110535730417 (`7a7d4c7`) completed only2/8 planned
browser cases. E01, redye and E24 browser hosts refused to start with
`EADDRINUSE 127.0.0.1:54328`; the capacity group later ran2/2 PASS. This
does not establish a failure of the unexecuted business journeys. The exact
owner of the earlier occupied port was not captured, so no specific process is
blamed. Artifact11189611359 SHA256:
`9ae659298add628809e6967238a10db4c978b3f77ad61c423bc036bdf921a81b`.

A separate eight-case recheck reserves4176/54328/54329 against ephemeral-port
allocation before services start on the disposable CI runner. It then requires
those loopback listener ports to be free before installation/probing. It does
not terminate unknown processes, alter any product file, weaken cleanup, or
change the retained business cases. The initial INCOMPLETE receipt remains
preserved; a successful retry is required and reported separately.

## Completed corrections

The corrected independent run36912838566 passes23/23 at120dfe3.
The isolated retained-browser run36915203087 passes8/8 atcc64cb1 with the
same business providers, available reserved ports and full cleanup/restoration.
Both original incomplete receipts remain archived beside the successful receipts.
No product change was needed for either correction.
