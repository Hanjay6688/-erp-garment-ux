# Pre-connect security boundary

## Allowed browser surface in phase 0

- Auth targets ERP Enteng UAT only.
- The only database read is `public.v_erp_my_profile` for the current authenticated user.
- The view must remain `security_invoker` + `security_barrier`, include an explicit `auth_user_id = (select auth.uid())` predicate plus `LOCAL CHECK OPTION`, grant `SELECT` only to `authenticated`, and revoke `PUBLIC`/`anon`/`service_role` before that grant.
- The private `erp` schema must not be exposed for this profile read.
- The browser business-RPC allowlist remains empty.

## Static build secrets

Vite compiles `VITE_*` values into JavaScript. `src/main.tsx` therefore copies only four allowed names rather than passing the full `import.meta.env` object. `vite.config.ts` calls `loadEnv(mode, ..., '')` so `.env`, `.env.local`, and mode-specific files are scanned before Vite's normal injection. `scripts/build-preflight.mjs` rejects secret/service-role names and server-key values. The `postbuild` lifecycle always runs `scripts/scan-client-artifacts.mjs` as an independent output check, including deploy/preview scripts that invoke `npm run build`.

Build demo and UAT as different artifacts. A client artifact cannot safely change modes after it has been built.

## Legacy HTML rendering quarantine

The following legacy simulation renderers use `innerHTML` or `insertAdjacentHTML`:

- `src/qc-final-sku.ts`
- `src/procurement.ts`
- `src/bs-rework.ts`

They currently interpolate only local, controlled simulation fixtures. They must not receive supplier names, SKU text, notes, user names, audit descriptions, or any other backend/user-controlled string.

Before connecting one of these screens, either:

1. rewrite its dynamic rendering in React/JSX or DOM nodes using `textContent`; or
2. introduce an audited, centralized HTML sanitizer and tests covering every interpolation boundary.

Do not call a screen “backend-connected” while an unsanitized backend value can reach these templates. This quarantine is independent of RLS: row authorization does not prevent client-side HTML injection.
