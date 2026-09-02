/**
 * Narrow, hand-written pre-connect read contract.
 *
 * This is deliberately NOT presented as generated database coverage. Phase 0
 * types only the approved public facades. The private `erp` schema remains
 * unexposed and there are no browser-writable tables in this contract.
 */
export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

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
    Functions: {
      erp_get_my_access_v1: { Args: Record<PropertyKey, never>; Returns: Json }
      erp_get_access_admin_v1: { Args: Record<PropertyKey, never>; Returns: Json }
      erp_save_role_v1: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version?: number | null }
        Returns: Json
      }
      erp_deactivate_role_v1: {
        Args: { p_role_id: string; p_reason: string; p_client_request_id: string; p_expected_version: number }
        Returns: Json
      }
      erp_save_app_user_v3: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version?: number | null }
        Returns: Json
      }
      erp_list_patterns_v1: {
        Args: { p_status?: string; p_query?: string | null; p_limit?: number; p_offset?: number }
        Returns: Json
      }
      erp_save_pattern_v1: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version?: number | null }
        Returns: Json
      }
      erp_deactivate_pattern_v1: {
        Args: { p_pattern_id: string; p_reason: string; p_client_request_id: string; p_expected_version: number }
        Returns: Json
      }
      erp_assign_pattern_v1: {
        Args: {
          p_cutting_group_id: string; p_pattern_id: string; p_reason: string
          p_client_request_id: string; p_expected_version: number
        }
        Returns: Json
      }
      erp_get_wip_control_v1: {
        Args: { p_filter?: string; p_pattern_id?: string | null; p_sort?: string; p_query?: string | null }
        Returns: Json
      }
      erp_set_wip_control_flag_v1: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version?: number | null }
        Returns: Json
      }
      erp_post_final_sku_allocation_v1: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version: number }
        Returns: Json
      }
    }
    Enums: Record<string, never>
    CompositeTypes: Record<string, never>
  }
}
