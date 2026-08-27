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
npm install
npm run dev
```

## Production build

```bash
npm run build
```

Output directory: `dist`.

## Cloudflare Pages

Import this Git repository in Cloudflare Workers & Pages.

- Framework preset: Vite
- Build command: `npm run build`
- Build output directory: `dist`

`public/_redirects` is included for SPA fallback.
