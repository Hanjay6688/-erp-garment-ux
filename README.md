# Atelier Garment ERP UX

Lightweight React + Vite prototype for the ERP Garment project.

## Current UX slice

- Owner dashboard focused on cash, receivables, HPP, finished-goods stock, WIP, and operational exceptions.
- Responsive sidebar arranged by business flow: Produksi → Gudang → Penjualan → Keuangan → Master Data.
- Penjualan & Invoice screen with visible stock per size, flexible dozen/PCS entry, editable size composition, and stock validation.
- Kartu Stok FG as factual per-SKU chronology.
- Mutasi Barang Jadi with owner-controlled display order while preserving factual stock/time data.
- Responsive tablet/mobile layout with no heavy UI or chart framework.

## Quantity convention

Backend/stock truth remains PCS. The UI accepts human-friendly input such as `2 lusin`, `18 pcs`, or `1 lusin 6 pcs`; one dozen equals 12 PCS. SKU defaults to three size slots unless configured otherwise.

## Local development

```bash
npm ci
npm test
npm run dev
```

## Runtime contract

- With no environment variables the app runs as `DEMO_SIMULATION`.
- `UAT_AUTH_SIMULATION` connects Auth only to ERP Enteng (`siimvrusnzxexizpyoib`). Business data and actions remain local simulation.
- UAT accepts one browser-safe publishable key (or legacy anon key). A production project URL, secret key, service-role key, missing variable, or unknown mode blocks startup; there is no fallback.
- The UAT gate verifies the Auth user and reads only `public.v_erp_my_profile`, a self-filtered security-invoker/security-barrier facade over the private profile table. The whole `erp` schema stays private. Only active `OWNER` or `ADMIN` roles are currently allowed; there is no in-app signup.
- The business RPC allowlist is intentionally empty during this phase.

Copy `.env.example` for the UAT variable names. Do not commit real credentials.

### Build-time environments

`VITE_*` values are compiled into static client assets; they are not server runtime configuration. Build and retain separate artifacts for each mode:

- Demo artifact: build with no Supabase variables and either omit `VITE_ERP_RUNTIME_MODE` or set it to `DEMO_SIMULATION`.
- UAT Auth artifact: build with `VITE_ERP_RUNTIME_MODE=UAT_AUTH_SIMULATION`, the exact ERP Enteng URL, and one publishable/legacy-anon browser key.

Never relabel or reuse a UAT artifact as a demo or production artifact. `vite.config.ts` explicitly loads and scans `.env*` plus process environment before bundling, so a forbidden secret/service-role name or server key cannot hide in a mode file. `postbuild` always scans `dist`; CI separately reruns the canary regression and output scan.

See [docs/preconnect-security.md](docs/preconnect-security.md) before connecting any screen to backend strings or enabling an RPC.

## Production build

```bash
npm run build
```

Output directory: `dist`. A successful `npm run build` already includes the mandatory client-artifact secret scan; `npm run scan:dist` can be rerun independently.

## Cloudflare Pages

Import this Git repository in Cloudflare Workers & Pages.

- Framework preset: Vite
- Build command: `npm run build`
- Build output directory: `dist`

`wrangler.jsonc` serves `dist` as static assets and uses SPA fallback for unknown routes.
