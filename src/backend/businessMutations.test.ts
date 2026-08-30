import { describe, expect, it } from 'vitest'
import { BUSINESS_RPC_ALLOWLIST, invokeBusinessRpc, isBusinessRpcAllowed } from './businessMutations'

describe('business RPC phase-0 guard', () => {
  it('ships with a deliberately empty hardcoded allowlist', () => {
    expect(BUSINESS_RPC_ALLOWLIST).toEqual([])
    expect(isBusinessRpcAllowed('post_sale_v2')).toBe(false)
  })

  it('cannot invoke any business RPC', async () => {
    await expect(invokeBusinessRpc('post_sale_v2', {}))
      .rejects.toMatchObject({ code: 'BUSINESS_RPC_DISABLED' })
  })
})
