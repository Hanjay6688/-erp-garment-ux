# Pre-connect security boundary

## Allowed browser surface in phase 0

- Auth targets ERP Enteng UAT only.
- The only database read is `public.v_erp_my_profile` for the current authenticated user.
- The view must remain `security_invoker` + `security_barrier`, include an explicit `auth_user_id = (select auth.uid())` predicate plus `LOCAL CHECK OPTION`, grant `SELECT` only to `authenticated`, and revoke `PUBLIC`/`anon`/`service_role` before that grant.
- The private `erp` schema must not be exposed for this profile read.
- Static source ownership forbids every browser business RPC or private-schema
  call until CP4 introduces an independently reviewed contract.

## Static build secrets

Vite compiles `VITE_*` values into JavaScript. `src/main.tsx` therefore copies only four allowed names rather than passing the full `import.meta.env` object. `vite.config.ts` calls `loadEnv(mode, ..., '')` so `.env`, `.env.local`, and mode-specific files are scanned before Vite's normal injection. `scripts/build-preflight.mjs` rejects secret/service-role names and server-key values. The `postbuild` lifecycle always runs `scripts/scan-client-artifacts.mjs` as an independent output check, including deploy/preview scripts that invoke `npm run build`.

Build demo and UAT as different artifacts. A client artifact cannot safely change modes after it has been built.

## Rendering boundary

The superseded imperative HTML renderers were removed in CP3.5. Procurement,
QC/final SKU, and BS/rework now render only through React components. Runtime
source must not introduce `innerHTML`, `insertAdjacentHTML`, or
`dangerouslySetInnerHTML` for business data.

This restriction is independent of RLS: row authorization does not prevent
client-side HTML injection.
