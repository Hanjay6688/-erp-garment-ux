import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { rng } from './demand-history-fixture.mjs'
// history_build before (git) and after (working tree), with only the planning
// functions it reads: utc, history_events, history_availability.
export const buildBase = 'c1f91041035941edded57da13482176701b2bfb6'
const block = (text, name) => { const a = text.indexOf(`create function ${name}(`); if (a < 0) throw new Error(name); return text.slice(a, text.indexOf('$$;', a) + 3) }
export async function installBuildControls(db) {
  const now = readFileSync('scripts/cp7-src/planning/history.sql', 'utf8'), old = execFileSync('git', ['show', `${buildBase}:scripts/cp7-src/planning/history.sql`], { encoding: 'utf8' })
  await db.execute(`create schema if not exists extensions;create extension if not exists pgcrypto schema extensions;create schema cp7_planning;
   ${block(readFileSync('scripts/cp7-src/planning/bootstrap.sql', 'utf8'), 'cp7_planning.utc')}
   ${block(readFileSync('scripts/cp7-src/planning/history-source.sql', 'utf8'), 'cp7_planning.history_events')}
   ${block(now, 'cp7_planning.history_availability')}
   ${block(old, 'cp7_planning.history_build').replace('create function cp7_planning.history_build(', 'create function cp7_planning.history_build_0(')}
   ${block(now, 'cp7_planning.history_build')}
   create function public.hb_state(fn text,c jsonb,q jsonb) returns text language plpgsql as $s$
   begin execute format('select %s($1,$2)',fn) using c,q;return 'NO_ERROR';exception when others then return sqlstate||':'||sqlerrm;end $s$;`)
}
const iso = ms => new Date(ms).toISOString()
export function capture(seed, { products = 5, stock = 40, sales = 20, mismatch = false } = {}) {
  const r = rng(seed), now = Date.UTC(2026, 5, 1, 3), day = 86400000, ids = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
  const roots = Array.from({ length: products }, (_, i) => ids(1000 + i)), out = { products: [], stock: [], sales: [], sale_journals: [], returns: [], return_journals: [] }
  roots.forEach((root, i) => out.products.push({ id: ids(2000 + i), root_id: root, size_id: ['S', 'M', 'L'][i % 3], sku: `SKU-${i}`, product_name: `Produk ${i}`, is_active: r() < 0.9,
    commercial: r() < 0.7 ? [{ sku_id: ids(3000 + i) }] : [], established_at: iso(now - (40 + Math.floor(r() * 30)) * day) }))
  let n = 0
  roots.forEach((root, i) => {
    for (let k = 0; k < stock / products; k++) out.stock.push({ id: ids(10000 + n++), root_id: root, physical_at: iso(now - Math.floor(r() * 35) * day - Math.floor(r() * day)), book_order: String(n),
      qty_signed: String(r() < 0.75 ? 1 + Math.floor(r() * 20) : -Math.floor(r() * 5)), quality_grade: r() < 0.85 ? (r() < 0.5 ? 'GRADE_A' : 'GRADE_B') : 'GRADE_C', movement_type: 'RECEIPT', reversal_of_id: null })
    // An open draft is reserved by a SALE_RESERVE movement of the same quantity (and sometimes a released one).
    if (r() < 0.6) {
      const qty = 1 + Math.floor(r() * 3), sid = ids(50000 + n), reserve = ids(10000 + n++)
      out.sales.push({ id: sid, sale_id: ids(60000 + n), root_id: root, size_id: out.products[i].size_id, status: 'DRAFT', revision: '1', qty_pcs: String(qty), sale_date: iso(now - 2 * day), updated_at: iso(now - day), sold_commercial: [] })
      out.stock.push({ id: reserve, root_id: root, physical_at: iso(now - 2 * day), book_order: String(n), qty_signed: String(mismatch && r() < 0.5 ? -(qty + 1) : -qty), quality_grade: 'GRADE_A', movement_type: 'SALE_RESERVE', reversal_of_id: null })
      if (r() < 0.3) { const old = ids(10000 + n++); out.stock.push({ id: old, root_id: root, physical_at: iso(now - 9 * day), book_order: String(n), qty_signed: '-2', quality_grade: 'GRADE_A', movement_type: 'SALE_RESERVE', reversal_of_id: null }, { id: ids(10000 + n++), root_id: root, physical_at: iso(now - 8 * day), book_order: String(n), qty_signed: '2', quality_grade: 'GRADE_A', movement_type: 'RELEASE', reversal_of_id: old }) }
    }
  })
  return { status: 'COMPLETE', captured_at: iso(now), facts: out }
}
