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
- `UAT_AUTH_SIMULATION` connects Auth, access control, Master Pola, Potongan, Pickup/Distribusi, WIP, Barang BS/Rework, and the CP6 Laundry → QC → exact-size Final SKU candidate to ERP Enteng (`siimvrusnzxexizpyoib`). The legacy Nota FG handoff remains blocked until its authoritative replacement is separately proven; there is no fixture fallback.
- The dedicated UAT release accepts the pinned browser-safe modern publishable key. A production project URL, secret key, service-role key, missing variable, or unknown mode blocks startup; there is no fallback.
- The UAT gate resolves each active mapped user through canonical public facades and the permission catalog. The `erp` schema, domain tables, and private writer functions remain inaccessible from the browser; there is no in-app signup.
- Browser traffic is limited to the source-owned canonical RPC allowlist. Connected reads and writes are server-authoritative, including server-side Pattern filters and optimistic row-version guards.

Copy `.env.example` for the UAT variable names. Do not commit environment files or any server credential.

### Build-time environments

`VITE_*` values are compiled into static client assets; they are not server runtime configuration. Build and retain separate artifacts for each mode:

- Demo artifact: build with no Supabase variables and either omit `VITE_ERP_RUNTIME_MODE` or set it to `DEMO_SIMULATION`.
- UAT Auth artifact: build with `VITE_ERP_RUNTIME_MODE=UAT_AUTH_SIMULATION`, the exact ERP Enteng URL, and one publishable/legacy-anon browser key.

Never relabel or reuse a UAT artifact as a demo or production artifact. `vite.config.ts` explicitly loads and scans `.env*` plus process environment before bundling, so a forbidden secret/service-role name or server key cannot hide in a mode file. `postbuild` always scans `dist`; CI separately reruns the canary regression and output scan.

See [docs/preconnect-security.md](docs/preconnect-security.md) before connecting any screen to backend strings or enabling an RPC. The binding cross-domain safety contract is documented in [ERP reliability invariants](docs/erp-reliability-invariants.md).

## Source ownership

CP3.5 validates the whole repository, not only the attendance candidate:

- every production TypeScript, TSX, and CSS file is reachable from the app entry;
- every stylesheet selector has an owning production component;
- every migration, rollback, SQL regression, proof harness, and UAT provenance
  file is classified and hash-bound;
- recorded v2.6.10–v2.6.13 source filenames use their exact ERP Enteng ledger
  versions, while the four reviewed CP3 migrations remain unchanged.

Run `npm run check:source`, `npm run check:css`, and `npm run check:backend`.
See [docs/cp3-5-code-ownership.md](docs/cp3-5-code-ownership.md) for the short
source map and the migration replay boundary.

## Production build

```bash
npm run build
```

Output directory: `dist`. A successful `npm run build` already includes the mandatory client-artifact secret scan; `npm run scan:dist` can be rerun independently.

## Cloudflare Worker

This repository is connected to the Cloudflare Workers build for the `erp-garment-ux` script. Pull-request branches receive preview deployments; a gated merge to `main` triggers the canonical production deployment at:

`https://erp-garment-ux.zrpf6sbtjb.workers.dev/`

- Framework preset: Vite
- Build command: `npm run build`
- Build output directory: `dist`

`wrangler.jsonc` serves `dist` as static assets and uses SPA fallback for unknown routes.
