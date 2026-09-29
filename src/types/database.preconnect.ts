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
      erp_cp7_save_payroll_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string }; Returns: Json }
      erp_cp7_get_payroll_workspace_v1: { Args: { p_section: string; p_query: Json }; Returns: Json }
      erp_cp7_save_roster_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string | null }; Returns: Json }
      erp_cp7_get_attendance_workspace_v1: { Args: { p_section: string; p_query: Json }; Returns: Json }
      erp_cp7_get_nota_workspace_v1: { Args: { p_section: string; p_query: Json }; Returns: Json }
      erp_cp7_save_nota_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string|null }; Returns: Json }
      erp_cp7_get_supplier_returns_v1: { Args: { p_purchase: string; p_location: string | null; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_save_supplier_return_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string | null }; Returns: Json }
      erp_cp7_get_purchase_invoices_v1: { Args: { p_purchase: string; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_get_invoice_sources_v1: { Args: { p_purchase: string; p_q: string; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_save_purchase_invoice_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string|null }; Returns: Json }
      erp_cp7_preview_material_count_v1: { Args: { p_scope: Json }; Returns: Json }
      erp_cp7_get_material_counts_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_save_material_count_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string | null }; Returns: Json }
      erp_cp7_get_fg_book_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_book_options_v1: { Args: { p_kind: string; p_q: string; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_save_fg_book_v1: { Args: { p_action: string; p_payload: Json; p_request: string }; Returns: Json }
      erp_cp7_get_fg_adjustments_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_save_fg_adjustment_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string | null }; Returns: Json }
      erp_cp7_get_fg_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_ledger_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_materials_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_material_ledger_v1: { Args: { p_material: string; p_roll: string | null; p_location: string; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_get_material_transfers_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_material_locations_v1: { Args: { p_q: string; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_save_materials_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string | null }; Returns: Json }
      erp_cp7_get_procurement_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_procurement_options_v1: { Args: { p_kind: string; p_q: string; p_offset: number; p_limit: number }; Returns: Json }
      erp_cp7_get_procurement_uom_v1: { Args: { p_material: string; p_at: string }; Returns: Json }
      erp_cp7_save_procurement_v1: { Args: { p_action: string; p_payload: Json; p_request: string; p_expected: string | null }; Returns: Json }
      erp_get_sku_workspace_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_get_sku_hpp_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_save_sku_action_v1: { Args: { p_action: string; p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_product_conversion_workspace_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_save_product_conversion_action_v1: { Args: { p_action: string; p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_accessory_issue_workspace_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_save_accessory_issue_action_v1: { Args: { p_action: string; p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_accessory_service_workspace_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_save_accessory_service_action_v1: { Args: { p_action: string; p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_laundry_bd_workspace_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_get_supplier_credit_v1: { Args: { p_filters: Json }; Returns: Json }
      erp_save_supplier_credit_v1: { Args: { p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_laundry_history_v1: { Args: { p_filters: Json }; Returns: Json }
      erp_save_laundry_bd_action_v1: { Args: { p_action: string; p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_pocket_fabric_workspace_v1: { Args: { p_query?: string }; Returns: Json }
      erp_get_pocket_periods_v1: { Args: { p_query?: string; p_offset?: number }; Returns: Json }
      erp_preview_pocket_fabric_period_v1: { Args: { p_period_start: string; p_period_end: string }; Returns: Json }
      erp_save_pocket_fabric_action_v1: { Args: { p_action: string; p_payload: Json; p_client_request_id: string }; Returns: Json }
      erp_get_initial_import_workspace_v1: { Args: { p_batch_id?: string | null }; Returns: Json }
      erp_save_initial_import_action_v1: {
        Args: { p_action: string; p_payload: Json; p_client_request_id: string }
        Returns: Json
      }
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
      erp_get_cutting_workspace_v1: {
        Args: {
          p_roll_query?: string | null; p_location_id?: string | null
          p_limit?: number; p_offset?: number
        }
        Returns: Json
      }
      erp_get_cutting_workspace_v2: {
        Args: {
          p_roll_query?: string | null; p_location_id?: string | null
          p_limit?: number; p_offset?: number
          p_order_query?: string | null; p_order_limit?: number; p_order_offset?: number
          p_draft_query?: string | null; p_draft_limit?: number; p_draft_offset?: number
          p_selected_order_id?: string | null; p_selected_draft_id?: string | null
        }
        Returns: Json
      }
      erp_save_cutting_group_before_sewing_v2: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version?: number | null }
        Returns: Json
      }
      erp_get_cutting_pickup_queue_v1: {
        Args: {
          p_filter?: string; p_pattern_id?: string | null; p_query?: string | null
          p_limit?: number; p_offset?: number
        }
        Returns: Json
      }
      erp_save_cutting_pickup_v1: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version?: number | null }
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
      erp_get_bs_resolution_workspace_v1: {
        Args: {
          p_filter?: string; p_kind?: string; p_pattern_id?: string | null
          p_query?: string | null; p_limit?: number; p_offset?: number
        }
        Returns: Json
      }
      erp_save_bs_resolution_action_v1: {
        Args: {
          p_action: string; p_payload: Json; p_client_request_id: string
          p_expected_version?: number | null
        }
        Returns: Json
      }
      erp_post_final_sku_allocation_v1: {
        Args: { p_payload: Json; p_client_request_id: string; p_expected_version: number }
        Returns: Json
      }
      erp_get_laundry_qc_workspace_v1: {
        Args: { p_scope?: string; p_query?: string | null }
        Returns: Json
      }
      erp_search_final_sku_products_v1: {
        Args: {
          p_source_laundry_receipt_batch_size_line_id: string
          p_physical_at: string
          p_query?: string | null
          p_after_sort_key?: string | null
          p_limit?: number
        }
        Returns: Json
      }
      erp_search_laundry_bs_products_v1: {
        Args: {
          p_delivery_batch_size_line_id: string
          p_physical_at: string
          p_query?: string | null
          p_after_sort_key?: string | null
          p_limit?: number
        }
        Returns: Json
      }
      erp_save_laundry_qc_action_v1: {
        Args: {
          p_action: string; p_payload: Json; p_client_request_id: string
          p_expected_version?: number | null
        }
        Returns: Json
      }
    }
    Enums: Record<string, never>
    CompositeTypes: Record<string, never>
  }
}
