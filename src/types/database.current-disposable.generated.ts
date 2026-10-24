export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      v_erp_my_profile: {
        Row: {
          auth_user_id: string | null
          full_name: string | null
          id: string | null
          is_active: boolean | null
          role: string | null
          row_version: number | null
        }
        Insert: {
          auth_user_id?: string | null
          full_name?: string | null
          id?: string | null
          is_active?: boolean | null
          role?: string | null
          row_version?: number | null
        }
        Update: {
          auth_user_id?: string | null
          full_name?: string | null
          id?: string | null
          is_active?: boolean | null
          role?: string | null
          row_version?: number | null
        }
        Relationships: []
      }
    }
    Functions: {
      erp_accounting_close_preflight_v1: {
        Args: { p_through: string }
        Returns: Json
      }
      erp_activate_attendance_hpp_pool_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_pool_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_assign_pattern_v1: {
        Args: {
          p_client_request_id: string
          p_cutting_group_id: string
          p_expected_version: number
          p_pattern_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_cancel_attendance_hpp_pool_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_pool_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_cancel_my_reminder_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_reason: string
          p_reminder_id: string
        }
        Returns: Json
      }
      erp_close_accounting_through_v1: {
        Args: { p_closed_through: string; p_reason: string }
        Returns: Json
      }
      erp_cp7_apply_plan_action_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_apply_plan_action_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_analysis_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_baseline_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_cutting_model_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_cutting_observation_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_cutting_wip_v1: {
        Args: { p_groups: string[]; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_cutting_yield_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_demand_history_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_model_evaluation_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_netting_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_operational_analysis_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_planning_scenario_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_production_supply_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_capture_production_wip_v1: {
        Args: { p_request: string; p_scope: Json }
        Returns: Json
      }
      erp_cp7_capture_snapshot_v1: {
        Args: { p_request: string; p_root: string }
        Returns: Json
      }
      erp_cp7_check_staged_analysis_source_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_check_staged_snapshot_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_claim_local_preview_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_claim_reminder_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_compare_reports_v1: {
        Args: { p_after: string; p_before: string }
        Returns: Json
      }
      erp_cp7_compare_reports_v2: {
        Args: { p_after: string; p_before: string }
        Returns: Json
      }
      erp_cp7_correct_mandor_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_correct_misc_finance_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_correct_note_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_correct_receipt_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_correct_sales_payment_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_correct_sales_return_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_correct_supplier_payment_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_create_supplier_payment_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_customer_credit_command_v1: {
        Args: { p_expected_versions: Json; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_evaluate_obligation_episodes_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_evaluate_rule_episodes_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_finish_local_preview_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_finish_po_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_finish_reminder_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_alerts_v1: { Args: { p: Json }; Returns: Json }
      erp_cp7_get_analysis_attention_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_analysis_attention_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_get_analysis_job_v1: {
        Args: { p_request: string }
        Returns: Json
      }
      erp_cp7_get_analysis_payable_conditions_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_get_analysis_receivable_conditions_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_get_attendance_entry_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_attendance_workspace_v1: {
        Args: { p_query: Json; p_section: string }
        Returns: Json
      }
      erp_cp7_get_audit_trail_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_customer_credit_review_v1: {
        Args: { p_payload: Json }
        Returns: Json
      }
      erp_cp7_get_customer_credit_workspace_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_customer_history_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_cutover_v1: { Args: never; Returns: Json }
      erp_cp7_get_cutting_auto_po_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_cutting_correction_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_cutting_input_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_cutting_input_workspace_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_cutting_model_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_cutting_model_workspace_v1: {
        Args: { p_group: string; p_roll: string }
        Returns: Json
      }
      erp_cp7_get_cutting_observation_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_cutting_return_reversal_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_cutting_return_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_cutting_status_policy_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_cutting_status_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_erp_settings_v1: { Args: never; Returns: Json }
      erp_cp7_get_fabric_recipe_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_adjustments_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_book_options_v1: {
        Args: { p_kind: string; p_limit: number; p_offset: number; p_q: string }
        Returns: Json
      }
      erp_cp7_get_fg_book_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_book_v2: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_ledger_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_ledger_v2: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_reorder_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_fg_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_finance_analysis_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_finance_report_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_history_yield_policy_v1: { Args: never; Returns: Json }
      erp_cp7_get_hpp_pools_v1: {
        Args: {
          p_limit: number
          p_offset: number
          p_period_end: string
          p_period_start: string
        }
        Returns: Json
      }
      erp_cp7_get_invoice_sources_v1: {
        Args: {
          p_limit: number
          p_offset: number
          p_purchase: string
          p_q: string
        }
        Returns: Json
      }
      erp_cp7_get_journal_book_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_kasbon_v1: { Args: { p_contractor: string }; Returns: Json }
      erp_cp7_get_local_reminder_request_v1: {
        Args: { p_operation: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_local_reminders_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_get_mandor_correction_v1: {
        Args: { p_po: string }
        Returns: Json
      }
      erp_cp7_get_master_v1: {
        Args: { p_kind: string; p_query: Json }
        Returns: Json
      }
      erp_cp7_get_material_count_options_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_material_counts_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_material_ledger_v1: {
        Args: {
          p_limit: number
          p_location: string
          p_material: string
          p_offset: number
          p_roll: string
        }
        Returns: Json
      }
      erp_cp7_get_material_ledger_v2: {
        Args: {
          p_limit: number
          p_location: string
          p_material: string
          p_offset: number
          p_roll: string
        }
        Returns: Json
      }
      erp_cp7_get_material_locations_v1: {
        Args: { p_limit: number; p_offset: number; p_q: string }
        Returns: Json
      }
      erp_cp7_get_material_name_v1: {
        Args: { p_material: string }
        Returns: Json
      }
      erp_cp7_get_material_reorder_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_material_transfers_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_materials_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_misc_correction_history_v1: {
        Args: { p_transaction_id: string }
        Returns: Json
      }
      erp_cp7_get_misc_finance_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_nota_sources_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_nota_workspace_v1: {
        Args: { p_query: Json; p_section: string }
        Returns: Json
      }
      erp_cp7_get_note_correction_v1: {
        Args: { p_sale: string }
        Returns: Json
      }
      erp_cp7_get_note_correction_v2: {
        Args: { p_sale: string }
        Returns: Json
      }
      erp_cp7_get_obligation_episode_history_v1: {
        Args: { p_payload: Json }
        Returns: Json
      }
      erp_cp7_get_obligation_episode_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_obligation_report_preview_v1: {
        Args: { p_publication: string }
        Returns: Json
      }
      erp_cp7_get_obligation_report_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_payroll_installments_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_payroll_workspace_v1: {
        Args: { p_query: Json; p_section: string }
        Returns: Json
      }
      erp_cp7_get_period_control_v1: {
        Args: { p_through: string }
        Returns: Json
      }
      erp_cp7_get_pickup_reversal_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_plan_options_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_plan_options_v2: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_planning_profiles_v1: {
        Args: { p_roots: string[] }
        Returns: Json
      }
      erp_cp7_get_po_finish_v1: { Args: { p_po: string }; Returns: Json }
      erp_cp7_get_po_reopen_v1: { Args: { p_po: string }; Returns: Json }
      erp_cp7_get_procurement_options_v1: {
        Args: { p_kind: string; p_limit: number; p_offset: number; p_q: string }
        Returns: Json
      }
      erp_cp7_get_procurement_uom_v1: {
        Args: { p_at: string; p_material: string }
        Returns: Json
      }
      erp_cp7_get_procurement_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_production_policy_v1: {
        Args: { p_skus: string[] }
        Returns: Json
      }
      erp_cp7_get_production_schedule_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_get_purchase_invoices_v1: {
        Args: { p_limit: number; p_offset: number; p_purchase: string }
        Returns: Json
      }
      erp_cp7_get_receipt_correction_v1: {
        Args: { p_purchase: string }
        Returns: Json
      }
      erp_cp7_get_recost_queue_v1: {
        Args: { p_offset?: number }
        Returns: Json
      }
      erp_cp7_get_reminder_obligations_v2: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_get_reminder_policy_history_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_reminder_policy_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_reminder_policy_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_get_reminder_request_v2: {
        Args: { p_operation: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_reminder_workspace_v2: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_get_reminders_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_report_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_report_request_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_rule_conditions_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_get_rule_episode_request_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_get_sales_cash_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_sales_chain_v1: { Args: { p_sale: string }; Returns: Json }
      erp_cp7_get_sales_credit_dependencies_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_sales_form_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_sales_payment_correction_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_sales_return_correction_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_sales_return_settlement_quote_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_sales_returns_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_sales_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_get_sewing_completion_v1: {
        Args: { p_group: string }
        Returns: Json
      }
      erp_cp7_get_source_identity_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_get_staged_ai_brief_v1: {
        Args: { p_run: string; p_targets: Json }
        Returns: Json
      }
      erp_cp7_get_staged_analysis_v1: {
        Args: { p_request: string }
        Returns: Json
      }
      erp_cp7_get_staged_production_schedule_v1: {
        Args: { p_source_request: string }
        Returns: Json
      }
      erp_cp7_get_supplier_payment_correction_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_supplier_payment_create_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_supplier_payments_v1: {
        Args: {
          p_offset: number
          p_payment?: string
          p_purchase: string
          p_q: string
        }
        Returns: Json
      }
      erp_cp7_get_supplier_return_sources_v1: {
        Args: {
          p_limit: number
          p_offset: number
          p_purchase: string
          p_q: string
        }
        Returns: Json
      }
      erp_cp7_get_supplier_returns_v1: {
        Args: {
          p_limit: number
          p_location: string
          p_offset: number
          p_purchase: string
        }
        Returns: Json
      }
      erp_cp7_get_supplier_transfer_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_transaction_dependencies_v1: {
        Args: { p_offset?: number; p_source: Json }
        Returns: Json
      }
      erp_cp7_get_wa_settings_v1: { Args: never; Returns: Json }
      erp_cp7_get_warehouse_summary_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_get_work_rates_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_list_analysis_archives_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_list_obligation_reports_v1: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_list_po_finish_v1: {
        Args: { p_offset?: number; p_query?: string }
        Returns: Json
      }
      erp_cp7_list_reports_v1: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_list_reports_v2: { Args: { p_query: Json }; Returns: Json }
      erp_cp7_preview_attendance_v1: {
        Args: { p_expected: string; p_payload: Json }
        Returns: Json
      }
      erp_cp7_preview_material_count_v1: {
        Args: { p_scope: Json }
        Returns: Json
      }
      erp_cp7_preview_plan_action_v1: {
        Args: { p_draft: string }
        Returns: Json
      }
      erp_cp7_preview_plan_action_v2: {
        Args: { p_draft: string }
        Returns: Json
      }
      erp_cp7_process_recost_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_publish_obligation_report_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_publish_report_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_publish_report_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_read_analysis_manifest_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_read_analysis_segment_v1: {
        Args: { p_access: string; p_index: number; p_run: string }
        Returns: Json
      }
      erp_cp7_read_analysis_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_baseline_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_cutting_wip_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_cutting_yield_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_demand_history_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_model_evaluation_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_read_netting_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_obligation_report_v1: {
        Args: { p_id: string }
        Returns: Json
      }
      erp_cp7_read_plan_actual_v1: { Args: { p_draft: string }; Returns: Json }
      erp_cp7_read_plan_draft_v1: { Args: { p_draft: string }; Returns: Json }
      erp_cp7_read_plan_draft_v2: { Args: { p_draft: string }; Returns: Json }
      erp_cp7_read_planning_scenario_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_read_production_supply_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_read_production_wip_v1: { Args: { p_run: string }; Returns: Json }
      erp_cp7_read_reminder_conditions_v2: {
        Args: { p_query: Json }
        Returns: Json
      }
      erp_cp7_read_report_section_v2: {
        Args: { p_access: string; p_id: string; p_index: number }
        Returns: Json
      }
      erp_cp7_read_report_v1: { Args: { p_id: string }; Returns: Json }
      erp_cp7_read_report_v2: { Args: { p_id: string }; Returns: Json }
      erp_cp7_read_snapshot_v1: {
        Args: {
          p_cursor?: string
          p_domain?: string
          p_limit?: number
          p_run: string
        }
        Returns: Json
      }
      erp_cp7_read_staged_analysis_page_v1: {
        Args: { p_access: string; p_index: number; p_run: string }
        Returns: Json
      }
      erp_cp7_read_staged_analysis_pages_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_recheck_reminder_v2: {
        Args: { p_condition: string; p_run: string }
        Returns: Json
      }
      erp_cp7_record_cutting_inputs_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_refresh_fg_reorder_v1: { Args: never; Returns: Json }
      erp_cp7_refresh_material_reorder_v1: {
        Args: { p_material_type: string }
        Returns: Json
      }
      erp_cp7_rename_material_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_reopen_cutting_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_reopen_po_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_request_analysis_job_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_request_bounded_staged_analysis_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_request_operational_analysis_job_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_request_staged_analysis_v1: {
        Args: { p_query: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_resolve_local_preview_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_resolve_reminder_claim_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_resolve_transaction_source_v1: {
        Args: { p_source: Json }
        Returns: Json
      }
      erp_cp7_resolve_wa_dispatch_v1: {
        Args: { p: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_return_cutting_fabric_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_reverse_cutting_return_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_reverse_pickup_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_reverse_sales_chain_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_reverse_supplier_payment_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_run_analysis_job_v1: {
        Args: { p_request: string }
        Returns: Json
      }
      erp_cp7_save_analysis_attention_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_attendance_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_cutting_auto_po_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_cutting_status_policy_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_cutting_suggestion_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_fabric_recipe_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_fg_adjustment_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_fg_book_v1: {
        Args: { p_action: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_fg_reorder_manual_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_history_yield_policy_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_hpp_pool_v1: {
        Args: { p_action: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_kasbon_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_local_binding_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_master_v1: {
        Args: { p_kind: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_material_count_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_material_reorder_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_materials_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_misc_finance_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_nota_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_payroll_installment_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_payroll_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_period_control_v1: {
        Args: { p_action: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_plan_draft_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_plan_draft_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_planning_profile_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_procurement_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_production_schedule_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_purchase_invoice_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_reminder_binding_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_reminder_policy_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_reminder_policy_v2: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_reminder_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_roster_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_sale_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_sewing_completion_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_staged_production_schedule_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_stock_formula_settings_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_supplier_return_v1: {
        Args: {
          p_action: string
          p_expected: string
          p_payload: Json
          p_request: string
        }
        Returns: Json
      }
      erp_cp7_save_supplier_transfer_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_wa_settings_v1: {
        Args: { p: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_save_work_rate_v1: {
        Args: { p_action: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_send_wa_test_v1: { Args: { p_request: string }; Returns: Json }
      erp_cp7_set_cutover_v1: {
        Args: { p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_set_production_policy_v1: {
        Args: { p_changes: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_set_wa_key_v1: {
        Args: { p_key: string; p_request: string }
        Returns: Json
      }
      erp_cp7_settle_sales_return_v1: {
        Args: { p_expected: string; p_payload: Json; p_request: string }
        Returns: Json
      }
      erp_cp7_staged_snapshot_freshness_v1: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_step_reminder_conditions_v2: {
        Args: { p_run: string }
        Returns: Json
      }
      erp_cp7_step_report_v2: { Args: { p_request: string }; Returns: Json }
      erp_cp7_step_staged_analysis_v1: {
        Args: { p_request: string }
        Returns: Json
      }
      erp_create_attendance_hpp_pool_v1: {
        Args: { p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_deactivate_pattern_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_pattern_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_deactivate_role_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_reason: string
          p_role_id: string
        }
        Returns: Json
      }
      erp_get_access_admin_v1: { Args: never; Returns: Json }
      erp_get_accessory_issue_workspace_v1: {
        Args: { p_filters?: Json }
        Returns: Json
      }
      erp_get_accessory_service_workspace_v1: {
        Args: { p_filters?: Json }
        Returns: Json
      }
      erp_get_attendance_workspace_v1: {
        Args: {
          p_contractor_id: string
          p_include_inactive?: boolean
          p_period_end: string
          p_period_start: string
        }
        Returns: Json
      }
      erp_get_bs_resolution_workspace_v1: {
        Args: {
          p_filter?: string
          p_kind?: string
          p_limit?: number
          p_offset?: number
          p_pattern_id?: string
          p_query?: string
        }
        Returns: Json
      }
      erp_get_cutting_pickup_queue_v1: {
        Args: {
          p_filter?: string
          p_limit?: number
          p_offset?: number
          p_pattern_id?: string
          p_query?: string
        }
        Returns: Json
      }
      erp_get_cutting_workspace_v1: {
        Args: {
          p_limit?: number
          p_location_id?: string
          p_offset?: number
          p_roll_query?: string
        }
        Returns: Json
      }
      erp_get_cutting_workspace_v2: {
        Args: {
          p_draft_limit?: number
          p_draft_offset?: number
          p_draft_query?: string
          p_limit?: number
          p_location_id?: string
          p_offset?: number
          p_order_limit?: number
          p_order_offset?: number
          p_order_query?: string
          p_roll_query?: string
          p_selected_draft_id?: string
          p_selected_order_id?: string
        }
        Returns: Json
      }
      erp_get_fg_stock_explainability_v1: {
        Args: { p_location_id?: string; p_product_id?: string }
        Returns: Json
      }
      erp_get_initial_import_workspace_v1: {
        Args: { p_batch_id?: string }
        Returns: Json
      }
      erp_get_laundry_bd_workspace_v1: {
        Args: { p_filters?: Json }
        Returns: Json
      }
      erp_get_laundry_history_v1: { Args: { p_filters: Json }; Returns: Json }
      erp_get_laundry_qc_workspace_v1: {
        Args: { p_query?: string; p_scope?: string }
        Returns: Json
      }
      erp_get_my_access_v1: { Args: never; Returns: Json }
      erp_get_pocket_fabric_workspace_v1: {
        Args: { p_query?: string }
        Returns: Json
      }
      erp_get_pocket_periods_v1: {
        Args: { p_offset?: number; p_query?: string }
        Returns: Json
      }
      erp_get_product_conversion_workspace_v1: {
        Args: { p_filters?: Json }
        Returns: Json
      }
      erp_get_sku_hpp_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_get_sku_workspace_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_get_supplier_credit_v1: { Args: { p_filters?: Json }; Returns: Json }
      erp_get_wip_control_v1: {
        Args: {
          p_filter?: string
          p_pattern_id?: string
          p_query?: string
          p_sort?: string
        }
        Returns: Json
      }
      erp_list_my_reminders_v1: {
        Args: { p_filter?: string; p_limit?: number }
        Returns: Json
      }
      erp_list_patterns_v1: {
        Args: {
          p_limit?: number
          p_offset?: number
          p_query?: string
          p_status?: string
        }
        Returns: Json
      }
      erp_post_attendance_period_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_period_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_post_fg_unsourced_receipt_v1: {
        Args: { p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_post_final_sku_allocation_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_preview_attendance_hpp_pool_v1: {
        Args: { p_period_end: string; p_period_start: string }
        Returns: Json
      }
      erp_preview_fg_unsourced_value_v1: {
        Args: { p_physical_at: string; p_product_id: string }
        Returns: Json
      }
      erp_preview_pocket_fabric_period_v1: {
        Args: { p_period_end: string; p_period_start: string }
        Returns: Json
      }
      erp_record_sewing_terminal_v1: {
        Args: { p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_reverse_attendance_period_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version: number
          p_period_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_reverse_fg_unsourced_receipt_v1: {
        Args: {
          p_client_request_id: string
          p_reason: string
          p_receipt_id: string
        }
        Returns: Json
      }
      erp_reverse_sewing_terminal_v1:
        | {
            Args: {
              p_client_request_id: string
              p_event_id: string
              p_reason: string
            }
            Returns: Json
          }
        | {
            Args: {
              p_client_request_id: string
              p_event_id: string
              p_expected_version: number
              p_reason: string
            }
            Returns: Json
          }
      erp_save_accessory_issue_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_accessory_service_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_app_user_v3: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_attendance_period_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
          p_preview_only?: boolean
        }
        Returns: Json
      }
      erp_save_bs_resolution_action_v1: {
        Args: {
          p_action: string
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_cutting_group_before_sewing_v2: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_cutting_pickup_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_initial_import_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_laundry_bd_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_laundry_qc_action_v1: {
        Args: {
          p_action: string
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_my_reminder_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_pattern_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_pocket_fabric_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_product_conversion_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_role_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_save_sku_action_v1: {
        Args: { p_action: string; p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_supplier_credit_v1: {
        Args: { p_client_request_id: string; p_payload: Json }
        Returns: Json
      }
      erp_save_worker_roster_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_search_final_sku_products_v1: {
        Args: {
          p_after_sort_key?: string
          p_limit?: number
          p_physical_at: string
          p_query?: string
          p_source_laundry_receipt_batch_size_line_id: string
        }
        Returns: Json
      }
      erp_search_laundry_bs_products_v1: {
        Args: {
          p_after_sort_key?: string
          p_delivery_batch_size_line_id: string
          p_limit?: number
          p_physical_at: string
          p_query?: string
        }
        Returns: Json
      }
      erp_set_contractor_hpp_policy_v1: {
        Args: {
          p_client_request_id: string
          p_expected_current_policy_id?: string
          p_payload: Json
        }
        Returns: Json
      }
      erp_set_fg_stock_policy_v1: {
        Args: {
          p_basis_source: string
          p_client_request_id: string
          p_effective_from: string
          p_expected_policy_id: string
          p_location_id: string
          p_manual_reorder_point_qty: number
          p_manual_target_stock_qty: number
          p_minimum_sample_days: number
          p_product_id: string
          p_reason: string
        }
        Returns: Json
      }
      erp_set_laundry_rate_owner_estimate_v1: {
        Args: { p_delivery_line_id: string; p_rate: number; p_reason: string }
        Returns: Json
      }
      erp_set_my_reminder_done_v1: {
        Args: {
          p_client_request_id: string
          p_done: boolean
          p_expected_version: number
          p_reminder_id: string
        }
        Returns: Json
      }
      erp_set_wip_control_flag_v1: {
        Args: {
          p_client_request_id: string
          p_expected_version?: number
          p_payload: Json
        }
        Returns: Json
      }
      erp_set_worker_daily_rate_v1: {
        Args: {
          p_client_request_id: string
          p_daily_rate: number
          p_effective_from: string
          p_expected_version: number
          p_reason: string
          p_worker_id: string
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const

