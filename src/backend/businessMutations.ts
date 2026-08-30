import { ClientAppError } from '../lib/clientError'

// Connection phase 0: there is intentionally no business RPC that the browser may call.
// Every future entry needs an audited contract for request_uuid, expected row_version,
// role/RLS behavior, replay semantics, and read-after-write verification before it is added.
export const BUSINESS_RPC_ALLOWLIST = Object.freeze([] as const)

export type AllowedBusinessRpc = (typeof BUSINESS_RPC_ALLOWLIST)[number]

export function isBusinessRpcAllowed(name: string): name is AllowedBusinessRpc {
  return (BUSINESS_RPC_ALLOWLIST as readonly string[]).includes(name)
}

export async function invokeBusinessRpc(
  name: string,
  _payload: Readonly<Record<string, unknown>>,
): Promise<never> {
  throw new ClientAppError(
    'BUSINESS_RPC_DISABLED',
    `RPC bisnis ${name || '(kosong)'} belum diizinkan pada fase Auth + data simulasi.`,
  )
}
