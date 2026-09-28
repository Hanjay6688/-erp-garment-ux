# Independent HTTP and browser continuation

Candidate product tree: `08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec`. The audit branch adds instrumentation only. No product source is modified.

Run from the CI auditor checkout after exact AC–BD installation and the independently authored master/invoice fixtures:

```sh
npm ci
npm install -g agent-browser@0.31.1
agent-browser install --with-deps
python audits/independent_bd_20260927/http_browser.py
```

Use Node 24. Python requires the same psycopg installation as the native audit. The workflow already provides Docker, Supabase CLI and the isolated runtime. Preserve `if: always()` on the HTTP/browser step; the native FREE probe currently fails and should not suppress this independent evidence. Upload `audit-results/` as usual.

The script starts a separate PostgREST container using the original runtime image and PGRST configuration, preserving its JWT configuration and pre-request hook, changing only its connection to `cp6_rollback`, the port and loopback binding, and the exposed public schema. A loopback proxy on port 54328 forwards Auth to the existing local GoTrue gateway and public RPCs to that clone. The application uses the required disposable build mode, exact guarded UI origin `http://127.0.0.1:4176`, and a local anon key. Browser actions use the real compiled candidate UI and agent-browser. Password login is real; no access token is fabricated and no browser auth state is injected.

The proxy is audit infrastructure. It does not reproduce all Kong gateway features (in particular its API-key authentication/rate limits); HTTP conclusions are about GoTrue identity, PostgREST JWT/role execution and public RPC behavior. They do not certify hosted gateway configuration.

Own checks precede supplemental checks: real Auth/ERP mapping; known value versus unknown null; active viewer positive read and forbidden write; genuine UI login and price display; master creation with SQL and network readback; UI invoice draft and actual page reload with unchanged journals; viewer money hiding. The draft test uses this audit's own prior opening-source fixture and is not proof of the daily physical chain.

Package extras and invoice pagination are explicitly peer-informed. They use this auditor's new browser vendor/package and 55 new public-API drafts. Their results are additive and do not replace the original independently frozen plan. The 200-receipt source cutoff is not covered by the 55-invoice test.

`results.json`, snapshots, screenshots, redacted HTTP events, browser commands and environment identity are written to `audit-results/http-browser/`. Auth tokens/passwords and service keys are omitted or redacted. Setup, build and adapter failures must be distinguished from confirmed product failures. A passed browser smoke test does not replace physical, HPP, concurrency, period, or rollback evidence.
