// Integrator-owned routing for the exact vendored B caller. No calculation,
// persistence, retry, actor or result rewriting belongs in this boundary.
export const OPERATIONAL_RPC = 'erp_cp7_request_bounded_staged_analysis_v2'
export const FINANCE_RPC = 'erp_cp7_request_bounded_frozen_finance_analysis_v2'
const clients = new WeakMap<object, object>()
const invalid = (): never => { throw Error('Pilihan laporan pada permintaan tersimpan tidak sesuai. Pulihkan permintaan asal.') }
const record = (v: unknown): Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v) ? v as Record<string, unknown> : invalid()

function route(args: unknown): { name: string; args: unknown } {
  const a = record(args), q = record(a.p_query)
  if (Object.keys(a).sort().join('|') !== 'p_query|p_request') return invalid()
  const hasMode = Object.hasOwn(q, 'finance_mode')
  if (Object.keys(q).sort().join('|') !== (hasMode ? 'finance_mode|from_date|group_mode|through_date' : 'from_date|group_mode|through_date')) return invalid()
  if (!hasMode) return { name: OPERATIONAL_RPC, args }
  if (q.finance_mode === 'STAGED') return { name: FINANCE_RPC, args }
  if (q.finance_mode !== 'DEFERRED') return invalid()
  // A's operational contract represents DEFERRED by absence of the mode.
  // Convert transport syntax only; the durable B request remains byte exact.
  const { finance_mode: _mode, ...query } = q
  return { name: OPERATIONAL_RPC, args: { ...a, p_query: query } }
}

export function bindFrozenFinanceTransport<T extends object>(client: T): T {
  const prior = clients.get(client)
  if (prior) return prior as T
  const rpc: unknown = Reflect.get(client, 'rpc', client)
  if (typeof rpc !== 'function') return invalid()
  const adapted = new Proxy(client, {
    get(target, key) {
      if (key === 'rpc') return (name: string, args: unknown, ...options: unknown[]) => {
        const next = name === OPERATIONAL_RPC ? route(args) : { name, args }
        return Reflect.apply(rpc, target, [next.name, next.args, ...options])
      }
      const value: unknown = Reflect.get(target, key, target)
      return typeof value === 'function' ? value.bind(target) : value
    },
  })
  clients.set(client, adapted)
  return adapted
}
