/**
 * Narrow, hand-written pre-connect read contract.
 *
 * This is deliberately NOT presented as generated database coverage. Phase 0
 * types only the exposed, security-invoker + security-barrier self-profile facade
 * `public.v_erp_my_profile`. The private `erp` schema must remain unexposed. Replace
 * this file with generated types after the complete approved public API surface is
 * available. There are no browser-writable tables in this contract.
 */
export type PreconnectDatabase = {
  public: {
    Tables: Record<string, never>
    Views: {
      v_erp_my_profile: {
        Row: {
          id: string
          auth_user_id: string | null
          full_name: string
          role: 'OWNER' | 'ADMIN' | 'STAFF' | 'CUSTOMER'
          is_active: boolean
          row_version: number
        }
        Relationships: []
      }
    }
    Functions: Record<string, never>
    Enums: Record<string, never>
    CompositeTypes: Record<string, never>
  }
}
