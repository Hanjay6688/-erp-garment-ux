# HTTP/browser gap completion

Frozen product candidate: `08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec`.

These cases run **after** every original run15 HTTP/browser case. The original
55-invoice scenario, exact desktop date oracle, fixtures and helper behavior
remain unchanged. Only disposable audit data and new test code are added.

## Oracles fixed before execution

- **Revoked OWNER:** create a separate real Auth account mapped to OWNER; obtain
  a genuine password token and authorized policy/draft responses. Another real
  owner revokes and restores its role through `erp_save_app_user_v3` over HTTP.
  The unchanged token must have money hidden on normal reads and fresh UUID
  mutations refused while revoked. Cached policy success and cached invoice
  financial disclosure are separate cases. No expected error code is copied or
  required. Restoration executes in `finally`; repeated-write counts are checked.
- **Mobile emulation:** new Chromium sessions use agent-browser
  `set device "iPhone 14"` plus Chromium's native
  `Emulation.setTouchEmulationEnabled` through the CLI's local CDP endpoint.
  Record viewport, user agent, touch points and coarse-pointer media state.
  All mobile workflow buttons use the CLI's native `tap` operation.
  Real owner/viewer logins, known versus unknown money presentation, master
  creation, invoice draft creation, full-page reload and field persistence, and
  role-based visibility are checked with actual DOM, screenshots, HTTP and SQL.
  The mobile draft uses the independently computed current Jakarta business
  date. This covers its default-date persistence, not mobile date-picker editing.
  It is browser emulation, not a physical iPhone test or an all-device certificate.
- **201 receipt sources:** consume `remaining-fixture.json` from the independent
  native continuation. Its dedicated vendor's receipts must originate from
  public priced dispatch/receipt operations, each GOOD 1 PCS, POSTED, ESTIMATED,
  with known cost and no posted invoice. Compare the exact fixture identifiers
  with HTTP sources and actual new-invoice dropdown options. Any omitted source
  is also submitted through public SAVE_INVOICE_DRAFT as a positive eligibility
  control; these drafts do not post or change journals. Select an existing
  option before recording absence of missing IDs and search/paging controls.
- **Bounded larger-data reads:** five sequential local HTTP workspace reads on
  the 201-receipt dataset; preserve exact native count and returned identities.
  Record response size and wall time. A predeclared audit budget is 10 seconds
  per read. Completeness is assessed by the separate source-cap cases and is
  never inferred from fast responses. No concurrent/unlimited load claim.
- **Redye boundary:** observe actual BD schema, reader keys and HTTP response to
  the UI's SET_REDYE_PRICE action. The service identifier is explicitly a
  sentinel: the BD-only installation has no BE service schema, so a valid BE
  service mutation cannot be exercised without expanding the product scope.
  Separately inspect the actual browser for its latent controls. No response is
  mocked, no BE table is seeded, and no invisible-button click is claimed.

## Origins and execution

Mobile workflows and the bounded read measurement are independent gap
completion. Revocation replay and source-limit cases are labelled peer-informed
continuations. Redye cases are labelled as follow-up to a prior static
observation. Their results supplement the frozen own cases.

Run the new `gaps_native.py` before `http_browser.py` to supply the receipt
fixture. Existing browser installation/build instructions are unchanged.
`results.json`, `events.json`, `http-events.json`, screenshots and native fixture
provenance retain actual failures and adapter failures separately.

A product-only filename search briefly surfaced matching RPC signature and
money-hidden assertion lines in existing writer browser/mode scripts. Those
files were not opened or copied; their assertions were not used. Subsequent SQL
searches were restricted to product `.sql` files. Original cases were already
frozen and executed before this search.

## Run16 adapter finding and correction

Run16 authenticated both mobile accounts, but its environment probe reported
390 × 844, DPR 3 and an iPhone user agent with zero touch points and a fine
pointer. The original touch-support oracle correctly failed; dependent mobile
workflows stayed blocked. This is retained as an audit adapter failure, not
reported as a product failure or mobile success.

The installed agent-browser 0.31.1 implementation of `handle_device` sets
device metrics and user agent but does not enable touch. Its supported
`get cdp-url` exposes the actual browser connection, and `handle_tap` dispatches
native `Input.dispatchTouchEvent` for Chromium. The continuation therefore
attaches a Node24 WebSocket CDP session to the mobile browser's sole page,
enables native touch emulation, and keeps that session alive until the mobile
workflows finish. No package is added, no product JavaScript is injected, and
no navigator property or media query is mocked. Native touch taps replace
mouse clicks only in the added mobile workflows. The original touch-points
oracle remains and coarse-pointer state must additionally be true.

Source trace: official `vercel-labs/agent-browser` tag `v0.31.1`,
`cli/src/native/actions.rs` (`handle_device`, `handle_cdp_url`, `handle_tap`),
`cli/src/commands.rs` (`get cdp-url`), and
`cli/src/native/interaction.rs` (`tap_touch`). The CDP operation is Chromium's
`Emulation.setTouchEmulationEnabled`, with `enabled=true` and
`maxTouchPoints=1`. Actual resulting environment, DOM, HTTP and DB evidence
must pass the next run before any mobile-flow success is claimed.
