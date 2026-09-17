#!/usr/bin/env python3
"""Admission-closed executor for reviewed CP6 pre-use rollbacks.

PostgreSQL can continue an already-entered PL/pgSQL body after CREATE OR
REPLACE/DROP changes its dependencies. Table locks therefore are necessary but
not sufficient for a live DDL rollback. This controller opens the one rollback
session first, persistently closes database admission, drains or terminates all
other client sessions, and only then executes the exact reviewed rollback.

On any ambiguous or pre-commit failure admission remains closed. An operator
must inspect the structured report and explicitly recover; the controller never
guesses whether a failed DDL command committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


TARGETS: dict[str, dict[str, Any]] = {
    'AK': {
        'rollback': Path(__file__).resolve().parents[1] / 'supabase/rollbacks/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.rollback.sql',
        'rollback_sha256': '12179dc19e6becb323400ffa8f180e71b456638837a38ebfc304ae8b523b8bcd',
        'marker': 'v2.6.20ak', 'platform': 'erp_v2_6_20ak_cp6_import_reference_preview',
        'predecessor': 'v2.6.20aj', 'capsule': 'erp.cp6_v2620ak_rollback_capsule',
        'capsule_count': 8,
    },
    'AJ': {
        'rollback': Path(__file__).resolve().parents[1] / 'supabase/rollbacks/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.rollback.sql',
        'rollback_sha256': '896baab52089adf56c60562cf3161391e01392aec972b48408752fc4e417aed9',
        'marker': 'v2.6.20aj', 'platform': 'erp_v2_6_20aj_cp6_rework_output_lineage',
        'predecessor': 'v2.6.20ai', 'capsule': 'erp.cp6_v2620aj_rollback_capsule',
        'capsule_count': 6,
    },
    'AI': {
        'rollback': Path('supabase/rollbacks/20260916090022_erp_v2_6_20ai_cp6_work_source_lineage.rollback.sql'),
        'rollback_sha256': 'ea7798456883773d53f747003017903305ee32b4d3b6f5851b17de443630ded7',
        'marker': 'v2.6.20ai', 'platform': 'erp_v2_6_20ai_cp6_work_source_lineage',
        'predecessor': 'v2.6.20ah', 'capsule': 'erp.cp6_v2620ai_rollback_capsule',
        'capsule_count': 3,
    },
    'AH': {
        'rollback': Path('supabase/rollbacks/20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.rollback.sql'),
        'rollback_sha256': 'aec93e99065e7197c7fcbab8b42f0b5b2ab50a2f9cc216436ae61ff854044a71',
        'marker': 'v2.6.20ah', 'platform': 'erp_v2_6_20ah_cp6_return_allocation_eligibility',
        'predecessor': 'v2.6.20ag', 'capsule': 'erp.cp6_v2620ah_rollback_capsule',
        'capsule_count': 5,
    },
    'AG': {
        'rollback': Path('supabase/rollbacks/20260916050822_erp_v2_6_20ag_cp6_sale_reservation_lineage.rollback.sql'),
        'rollback_sha256': 'c1265acfb790a8c7f2b6bc8d6b3691902658eb1f0b879ea2c1269d6e24a2f231',
        'marker': 'v2.6.20ag', 'platform': 'erp_v2_6_20ag_cp6_sale_reservation_lineage',
        'predecessor': 'v2.6.20af', 'capsule': 'erp.cp6_v2620ag_rollback_capsule',
        'capsule_count': 4,
    },
    'AF': {
        'rollback': Path('supabase/rollbacks/20260916014332_erp_v2_6_20af_cp6_posted_child_integrity.rollback.sql'),
        'rollback_sha256': 'd417b2ccb0e2cc5cd836e6a3d58ea9f50f2391cd386b31320d82fef7dc542575',
        'marker': 'v2.6.20af', 'platform': 'erp_v2_6_20af_cp6_posted_child_integrity',
        'predecessor': 'v2.6.20ae', 'capsule': 'erp.cp6_v2620af_rollback_capsule',
        'capsule_count': 2,
    },
    'AE': {
        'rollback': Path('supabase/rollbacks/20260915201500_erp_v2_6_20ae_cp6_opening_roll_integrity.rollback.sql'),
        'rollback_sha256': 'a869de31481cac1c8a26de17e3be9d47d2b42c18a6756df5cabfc016ebfa0341',
        'marker': 'v2.6.20ae', 'platform': 'erp_v2_6_20ae_cp6_opening_roll_integrity',
        'predecessor': 'v2.6.20ad', 'capsule': 'erp.cp6_v2620ae_rollback_capsule',
        'capsule_count': 2,
    },
    'AD': {
        'rollback': Path('supabase/rollbacks/20260915113627_erp_v2_6_20ad_cp6_opening_material_business_day.rollback.sql'),
        'rollback_sha256': '38eb8025f07fa9a49f221fa274e56242c5c525947c3d24dc98a735d02b75512c',
        'marker': 'v2.6.20ad', 'platform': 'erp_v2_6_20ad_cp6_opening_material_business_day',
        'predecessor': 'v2.6.20ac', 'capsule': 'erp.cp6_v2620ad_rollback_capsule',
        'capsule_count': 2,
    },
    'AC': {
        'rollback': Path('supabase/rollbacks/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.rollback.sql'),
        'rollback_sha256': 'ebf1d0f66fe0b50d41d872c19510adad9af993bd03ae5e513542004b7e5b1acb',
        'marker': 'v2.6.20ac',
        'platform': 'erp_v2_6_20ac_cp6_temporal_surface_closure',
        'predecessor': 'v2.6.20ab',
        'capsule': 'erp.cp6_v2620ac_rollback_capsule',
        'extra_capsules': ['erp.cp6_v2620ac_relation_rollback_capsule'],
        'capsule_count': 115,
    },
    'AB': {'rollback': Path('supabase/rollbacks/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.rollback.sql'), 'rollback_sha256': '5602fefc1b29935ccfb485635ec14e6fdea7468bd726ed440d6c5d93d12b1262', 'marker': 'v2.6.20ab', 'platform': 'erp_v2_6_20ab_cp6_operational_business_clock', 'predecessor': 'v2.6.20aa', 'capsule': 'erp.cp6_v2620ab_rollback_capsule', 'capsule_count': 5},
    'F': {
        'rollback': Path('supabase/rollbacks/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.rollback.sql'),
        'rollback_sha256': '83819e093d1489af70431704c59e2cb50a0149e1adc8520d5b9536510572a23d',
        'marker': 'v2.6.20f',
        'platform': 'erp_v2_6_20f_cp6_final_runtime_reliability',
        'predecessor': 'v2.6.20e',
        'capsule': 'erp.cp6_v2620f_rollback_capsule',
        'capsule_count': 8,
    },
    'G': {
        'rollback': Path('supabase/rollbacks/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.rollback.sql'),
        'rollback_sha256': '8946f4ca8b75850cb284cee669b609e7e938b6020f4e9fa7a270e9794b2becd8',
        'marker': 'v2.6.20g',
        'platform': 'erp_v2_6_20g_cp6_independent_audit_closure',
        'predecessor': 'v2.6.20f',
        'capsule': 'erp.cp6_v2620g_rollback_capsule',
        'capsule_count': 7,
    },
    'H': {
        'rollback': Path('supabase/rollbacks/20260910061516_erp_v2_6_20h_cp6_expanded_audit_closure.rollback.sql'),
        'rollback_sha256': '0d0318e3848344c3642f1796a205d25bcf1cc2d2091ce28d1fc9cf6d186ecbe5',
        'marker': 'v2.6.20h',
        'platform': 'erp_v2_6_20h_cp6_expanded_audit_closure',
        'predecessor': 'v2.6.20g',
        'capsule': 'erp.cp6_v2620h_rollback_capsule',
        'capsule_count': 6,
    },
    'I': {
        'rollback': Path('supabase/rollbacks/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.rollback.sql'),
        'rollback_sha256': '7719d329e7e0e4d4293466b9e425c9ef0b4a46a757545ad3d1bb6acbd2c535f2',
        'marker': 'v2.6.20i',
        'platform': 'erp_v2_6_20i_cp6_h2_audit_closure',
        'predecessor': 'v2.6.20h',
        'capsule': 'erp.cp6_v2620i_rollback_capsule',
        'capsule_count': 1,
    },
    'J': {
        'rollback': Path('supabase/rollbacks/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.rollback.sql'),
        'rollback_sha256': 'b0def9ada0670e9cdfd9c33ee4c507b8be628fed17027651d4df4b3038264f6d',
        'marker': 'v2.6.20j',
        'platform': 'erp_v2_6_20j_cp6_payment_fact_closure',
        'predecessor': 'v2.6.20i',
        'capsule': 'erp.cp6_v2620j_rollback_capsule',
        'capsule_count': 3,
    },
    'K': {
        'rollback': Path('supabase/rollbacks/20260911023222_erp_v2_6_20k_cp6_payment_date_conservation.rollback.sql'),
        'rollback_sha256': '9c08f543e4635d59f5e65857a0e3c13f76f52af019eccbe249acc313aac8f01d',
        'marker': 'v2.6.20k',
        'platform': 'erp_v2_6_20k_cp6_payment_date_conservation',
        'predecessor': 'v2.6.20j',
        'capsule': 'erp.cp6_v2620k_rollback_capsule',
        'capsule_count': 4,
    },
    'L': {
        'rollback': Path('supabase/rollbacks/20260911070622_erp_v2_6_20l_cp6_exact_ledger_conservation.rollback.sql'),
        'rollback_sha256': 'd6aa1e6bf6aa0dc4d2fffc7cf2432dd1f6e8eed89bfe0471cad0ebbfb7e58531',
        'marker': 'v2.6.20l',
        'platform': 'erp_v2_6_20l_cp6_exact_ledger_conservation',
        'predecessor': 'v2.6.20k',
        'capsule': 'erp.cp6_v2620l_rollback_capsule',
        'capsule_count': 3,
    },
    'M': {
        'rollback': Path('supabase/rollbacks/20260911092622_erp_v2_6_20m_cp6_subledger_exact_cent_closure.rollback.sql'),
        'rollback_sha256': '1bf669e82c46fe3fa7e8d007800657c6f30c13445f301960aec78154c970b5ac',
        'marker': 'v2.6.20m',
        'platform': 'erp_v2_6_20m_cp6_subledger_exact_cent_closure',
        'predecessor': 'v2.6.20l',
        'capsule': 'erp.cp6_v2620m_rollback_capsule',
        'capsule_count': 15,
    },

    'N': {
        'rollback': Path('supabase/rollbacks/20260911124328_erp_v2_6_20n_cp6_supplier_cent_lifecycle.rollback.sql'),
        'rollback_sha256': '29f52100d28779112638bd7bc95b0ffb7dd5ec17c83dc140e79b2f18e2fe3dda',
        'marker': 'v2.6.20n',
        'platform': 'erp_v2_6_20n_cp6_supplier_cent_lifecycle',
        'predecessor': 'v2.6.20m',
        'capsule': 'erp.cp6_v2620n_rollback_capsule',
        'capsule_count': 7,
    },

    'O': {
        'rollback': Path('supabase/rollbacks/20260911165255_erp_v2_6_20o_cp6_supplier_return_document_allocation.rollback.sql'),
        'rollback_sha256': 'a26c3d9869337d874daef0292081a150f543b6f754b899f214ba45cf57c46003',
        'marker': 'v2.6.20o',
        'platform': 'erp_v2_6_20o_cp6_supplier_return_document_allocation',
        'predecessor': 'v2.6.20n',
        'capsule': 'erp.cp6_v2620o_rollback_capsule',
        'capsule_count': 2,
    },

    'P': {
        'rollback': Path('supabase/rollbacks/20260912051922_erp_v2_6_20p_cp6_supplier_return_match_state.rollback.sql'),
        'rollback_sha256': '02f269e031dc6a930c29452742ae13caf81a6c537d999e13d972731b3597290f',
        'marker': 'v2.6.20p',
        'platform': 'erp_v2_6_20p_cp6_supplier_return_match_state',
        'predecessor': 'v2.6.20o',
        'capsule': 'erp.cp6_v2620p_rollback_capsule',
        'capsule_count': 3,
    },

    'Q': {
        'rollback': Path('supabase/rollbacks/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.rollback.sql'),
        'rollback_sha256': 'd3c2cc7a18281f357b2b47e23179a2e4c86d5a16b035b0fc1e05dc3bf8d8dcb4',
        'marker': 'v2.6.20q', 'platform': 'erp_v2_6_20q_cp6_supplier_invoice_exact_quantity',
        'predecessor': 'v2.6.20p', 'capsule': 'erp.cp6_v2620q_rollback_capsule',
        'capsule_count': 4,
    },


    'R': {
        'rollback': Path('supabase/rollbacks/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.rollback.sql'),
        'rollback_sha256': 'ec3663694758cffef6509a4bc560aad257dd30b46be236c38abd4bf7c0e7e33e',
        'marker': 'v2.6.20r', 'platform': 'erp_v2_6_20r_cp6_receipt_invoice_dependency',
        'predecessor': 'v2.6.20q', 'capsule': 'erp.cp6_v2620r_rollback_capsule',
        'capsule_count': 3,
    },


    'S': {
        'rollback': Path('supabase/rollbacks/20260912132445_erp_v2_6_20s_cp6_supplier_payment_business_date.rollback.sql'),
        'rollback_sha256': '0711ddf3bb3fff97b27e3f576c1875aa34d7d16a4a018155a5ea2f24cbb2f66e',
        'marker': 'v2.6.20s', 'platform': 'erp_v2_6_20s_cp6_supplier_payment_business_date',
        'predecessor': 'v2.6.20r', 'capsule': 'erp.cp6_v2620s_rollback_capsule',
        'capsule_count': 3,
    },

    'T': {
        'rollback': Path('supabase/rollbacks/20260912171034_erp_v2_6_20t_cp6_material_adjustment_revaluation.rollback.sql'),
        'rollback_sha256': 'ed8f45bfb46721a5a23381db8ec607b86b7fe2756863dea48f2c8f5fa8db7b56',
        'marker': 'v2.6.20t', 'platform': 'erp_v2_6_20t_cp6_material_adjustment_revaluation',
        'predecessor': 'v2.6.20s', 'capsule': 'erp.cp6_v2620t_rollback_capsule',
        'capsule_count': 6,
    },

    'U': {
        'rollback': Path('supabase/rollbacks/20260913070000_erp_v2_6_20u_cp6_canonical_business_date.rollback.sql'),
        'rollback_sha256': 'e69035e7402c1d04ee3771145ad19bf3e83d6f303076dabdb8e05b1b251dcd76',
        'marker': 'v2.6.20u', 'platform': 'erp_v2_6_20u_cp6_canonical_business_date',
        'predecessor': 'v2.6.20t', 'capsule': 'erp.cp6_v2620u_rollback_capsule',
        'capsule_count': 7,
    },

    'V': {
        'rollback': Path('supabase/rollbacks/20260913135850_erp_v2_6_20v_cp6_misc_finance_business_date.rollback.sql'),
        'rollback_sha256': '4fb8f0ded3e452dca1d44214711bd79ffcf0f3b68d956283da9bbce5e4444f7b',
        'marker': 'v2.6.20v', 'platform': 'erp_v2_6_20v_cp6_misc_finance_business_date',
        'predecessor': 'v2.6.20u', 'capsule': 'erp.cp6_v2620v_rollback_capsule',
        'capsule_count': 3,
    },

    'W': {
        'rollback': Path('supabase/rollbacks/20260913173840_erp_v2_6_20w_cp6_scrap_business_date.rollback.sql'),
        'rollback_sha256': '07fcf6c91efe03eea30fb4c1ed3635c6d63421f73407e4d2054ee92861b31153',
        'marker': 'v2.6.20w', 'platform': 'erp_v2_6_20w_cp6_scrap_business_date',
        'predecessor': 'v2.6.20v', 'capsule': 'erp.cp6_v2620w_rollback_capsule',
        'capsule_count': 3,
    },

    'AA': {'rollback': Path('supabase/rollbacks/20260914163608_erp_v2_6_20aa_cp6_material_cost_business_day.rollback.sql'), 'rollback_sha256': '95af278ecdb285423ce07160fb8697cd0854599a9c8d8c091cd2c33b075d2306', 'marker': 'v2.6.20aa', 'platform': 'erp_v2_6_20aa_cp6_material_cost_business_day', 'predecessor': 'v2.6.20z', 'capsule': 'erp.cp6_v2620aa_rollback_capsule', 'capsule_count': 2},
    'Z': {'rollback': Path('supabase/rollbacks/20260914085912_erp_v2_6_20z_cp6_accounting_close_business_date.rollback.sql'), 'rollback_sha256': 'c00029564f0092ebfb8afa9daeb566961af7fe2b6fe8eb800550d1b045896f2f', 'marker': 'v2.6.20z', 'platform': 'erp_v2_6_20z_cp6_accounting_close_business_date', 'predecessor': 'v2.6.20y', 'capsule': 'erp.cp6_v2620z_rollback_capsule', 'capsule_count': 1},
    'Y': {
        'rollback': Path('supabase/rollbacks/20260914043146_erp_v2_6_20y_cp6_cash_business_dates.rollback.sql'),
        'rollback_sha256': '63d636288dcd1f25a844721a3429ac0966769465eb2ffd9a9772b4fffb92d679',
        'marker': 'v2.6.20y', 'platform': 'erp_v2_6_20y_cp6_cash_business_dates',
        'predecessor': 'v2.6.20x', 'capsule': 'erp.cp6_v2620y_rollback_capsule',
        'capsule_count': 6,
    },
    'X': {
        'rollback': Path('supabase/rollbacks/20260913224854_erp_v2_6_20x_cp6_internal_role_fail_closed_rollback_r2.rollback.sql'),
        'rollback_sha256': '915fbba9398885e1ce4deef0650c38d6237729781c5985beb2acdec0c911e43a',
        'marker': 'v2.6.20x', 'platform': 'erp_v2_6_20x_cp6_internal_role_fail_closed',
        'predecessor': 'v2.6.20w', 'capsule': 'erp.cp6_v2620x_rollback_capsule',
        'capsule_count': 1,
    },
}


def _acl(*roles: str) -> list[str]:
    return [f'{role}=X/postgres' for role in sorted(roles)]


# Independent trust roots. A capsule's self-declared checksum is not authority:
# every predecessor definition, installed definition, owner, and ACL must match
# these reviewed source pins before database admission may be changed.
TRUSTED_FUNCTIONS: dict[str, list[dict[str, Any]]] = {
    'F': [
        {'identity': 'erp.compute_po_hpp_gl_targets_v2620d(uuid)', 'predecessor_sha256': '77b5b531d484bcb4c1532e529e8b5269f1afab438ca16d0b1dc7f0f143efc53e', 'installed_sha256': 'dcc180e84d21f3869674dcbb98514ad739bffa7f6205b45db7fd18c98473787a', 'owner': 'postgres', 'acl': _acl('postgres')},
        {'identity': 'erp.post_product_conversion(uuid)', 'predecessor_sha256': 'c80f9ff4a047c7232a3bb224cccdfd9e947d38ffe8ef46b9ef9457fa43fb0e4d', 'installed_sha256': '2f38beab669cb2dc3a1eb7a88dc6b04506234f85d79caff70331f97d09a93b90', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.post_sale(uuid)', 'predecessor_sha256': '96e5eec137b2eee4b16dd3df6aad69c084935521dfa851bf106ef0bab2239ca4', 'installed_sha256': '5b6372d1e0ac6e3ed841dd3d1e13506af4297974aa8c7847c093e85c2181a5e0', 'owner': 'postgres', 'acl': _acl('postgres', 'service_role')},
        {'identity': 'erp.post_sales_return(uuid)', 'predecessor_sha256': 'd83e9f58406528fd3777b348cf71fc7521de853c6c31c1ed668f7f3e46c2d755', 'installed_sha256': '217788d5f72bcfb87a387b82360c0f4a1ac191913beb0cf1a2ec5e31926a09a0', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.propagate_conversion_hpp_for_po(uuid)', 'predecessor_sha256': '15d8d2a4fceafe70105aa1a4f97dc08ce67571001c965dbc50f0c39310e37296', 'installed_sha256': 'bcef98540ac0e6f27618d6c13eca57d8451ff2fa3f0306f334f87881360fd418', 'owner': 'postgres', 'acl': _acl('postgres', 'service_role')},
        {'identity': 'erp.reverse_sale(uuid,text)', 'predecessor_sha256': 'ec522f0eeabac729590e45360752db6d0fa021e51716289a59be65856adb6cfd', 'installed_sha256': 'f9bade2d172a4abefe6973fb3dc333f6f70705b1b5ba1da52d464e3f45f64726', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.reverse_sales_return(uuid,text)', 'predecessor_sha256': '8678a986758185dd489379321f4e2525187252d0108cd7fc2930121da8324175', 'installed_sha256': '68e4ed3a1940e3853bcdadaf2d607ed60a78a350460efcaf4fa052a90c902bce', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': '5d06a5d87aecd59f6a069a2d2ad3663859787dfe5b9e4ecd4922e1f7b2e28c6e', 'installed_sha256': 'dc535f21e23d53af97a98a37da99f5109a8130833fd8bceb518196119cf993ed', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
    ],
    'G': [
        {'identity': 'erp.post_fg_adjustment(uuid)', 'predecessor_sha256': 'a8d3fcccacd5017e54e5f48f042bc8ec57224bce2623fbdbc1cbe1f70824316c', 'installed_sha256': '710778d554493ca1acb91f5878fcf8b12998020a62c67f87dcf8106bb08cdc19', 'owner': 'postgres', 'acl': _acl('postgres', 'service_role')},
        {'identity': 'erp.post_opening_balance(uuid)', 'predecessor_sha256': 'eee35b03c775861208d64873acfd010d51d28da4b377dced1d815ae5ec88c720', 'installed_sha256': 'd73391c79e725c14aab7370cf5f5dfc0bd2134a02480e5693c37dc9c25bf5829', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.post_opening_hpp_correction(uuid,numeric,text,date)', 'predecessor_sha256': 'c3bd668af920187afe2781cbe5b87cca7995bcbfff2cee684a38a9d0d0b4fcac', 'installed_sha256': '0fcce7b463ca220a1d565f5d6eac56d75531e1a071f42d4c11d9852642673399', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.reverse_fg_adjustment(uuid,text)', 'predecessor_sha256': '22d7a3ac32c06397b1e6f1659d4c4de0b49367c75a8872e7313ea850b1e185e9', 'installed_sha256': '2591b1f0b9cdf6a0a36629bb183386bf0e7433d585520687aec6e2be6853b8a4', 'owner': 'postgres', 'acl': _acl('postgres', 'service_role')},
        {'identity': 'erp.reverse_opening_hpp_correction(uuid,text)', 'predecessor_sha256': 'b5931900f8c23ec8b24663165859754f496c93d25caf95ab9fe1adb510628b0c', 'installed_sha256': '9ea3965ec90c5f070b81ab6384a95ad573984d3a56dd01a242d31077905ca230', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': 'dc535f21e23d53af97a98a37da99f5109a8130833fd8bceb518196119cf993ed', 'installed_sha256': 'fd48bcf94868dbcf7087af2c34b12c82333ae861d44c6bf79cbb41b1350a8962', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.sync_opening_lot_hpp_to_gl(uuid,date)', 'predecessor_sha256': '217b1b364852601e7dd05da766219290083574a9c64684abdd0a5a5a009a8040', 'installed_sha256': '2353bb967fec7d661877db745554b2b48e206ac8b3a36562af70fc60b6107998', 'owner': 'postgres', 'acl': _acl('postgres')},
    ],
    'H': [
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': '436a77b32c953e92fc8e43f953335392c4137b61bf632780d26b9b942d94e8b0', 'installed_sha256': '4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7', 'owner': 'postgres', 'acl': _acl('postgres', 'service_role')},
        {'identity': 'erp.post_sales_payment(uuid)', 'predecessor_sha256': '83214f0812d151b5d03cb8669f48fb5c72b4480d0c609df84d244559f3e4d988', 'installed_sha256': '010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.post_sales_return(uuid)', 'predecessor_sha256': '217788d5f72bcfb87a387b82360c0f4a1ac191913beb0cf1a2ec5e31926a09a0', 'installed_sha256': 'd959c5e095cce32540b9f2a4310857520b4eec70c5200465f16d74cccfb45a46', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.reverse_sales_payment(uuid,text)', 'predecessor_sha256': '33219c5509a43470f87d3b0fe4af472bec3f87b4808bbdba7d2eed69ea88354d', 'installed_sha256': '09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.reverse_sales_return(uuid,text)', 'predecessor_sha256': '68e4ed3a1940e3853bcdadaf2d607ed60a78a350460efcaf4fa052a90c902bce', 'installed_sha256': 'e7155962a8aa0f0e72f16644ffdf3563d3a11658b73c5185e94d6023090ec3cb', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': 'fd48bcf94868dbcf7087af2c34b12c82333ae861d44c6bf79cbb41b1350a8962', 'installed_sha256': '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
    ],
    'I': [
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f', 'installed_sha256': 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
    ],
    'J': [
        {'identity': 'erp.post_sales_payment(uuid)', 'predecessor_sha256': '010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df', 'installed_sha256': '5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
        {'identity': 'erp.reverse_sales_payment(uuid,text)', 'predecessor_sha256': '09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6', 'installed_sha256': '00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres')},
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1', 'installed_sha256': '3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f', 'owner': 'postgres', 'acl': _acl('authenticated', 'postgres', 'service_role')},
    ],
    'K': [
        {'identity': 'erp.post_sales_payment(uuid)', 'predecessor_sha256': '5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a', 'installed_sha256': '362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.reverse_sales_payment(uuid,text)', 'predecessor_sha256': '00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6', 'installed_sha256': 'e5f48784389148a40b2f71fbe9a3e133ff9a7bc95ec969da74e27163b0c5b069', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': '3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f', 'installed_sha256': '2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.guard_sales_payment_posted_identity_v2620j()', 'predecessor_sha256': '3849af0c4d17fa6fba90d87ff923dd82bf942f922d792ab5c2901f069b42a5d0', 'installed_sha256': 'bc2f8539173958e7c8c8dd8287e193131598ee71286146e7d76d258d700e1617', 'owner': 'postgres', 'acl': ['postgres=X/postgres']},
    ],
    'L': [
        {'identity': 'erp.post_journal(text,uuid,date,text,jsonb)', 'predecessor_sha256': 'c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76', 'installed_sha256': '1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': '4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7', 'installed_sha256': 'dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.resolve_laundry_claim(uuid,text,text)', 'predecessor_sha256': '51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b', 'installed_sha256': '20eba16640912f04220437c21df018a6799dc48b06d8147abfbd2454e2d60425', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
    ],
    'M': [
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': 'dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108', 'installed_sha256': '98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_material_purchase_cost_correction(uuid)', 'predecessor_sha256': 'd80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8', 'installed_sha256': '9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.post_material_supplier_invoice(uuid)', 'predecessor_sha256': 'ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5', 'installed_sha256': '65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_material_supplier_return(uuid)', 'predecessor_sha256': '562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714', 'installed_sha256': 'f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_opening_financial_correction(uuid,numeric,text,date)', 'predecessor_sha256': '41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7', 'installed_sha256': '95ad1f5db523bdc19d7b21d1f1b9e1baa49a499fb791f937fe43b0291d4bd7f1', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.post_opening_subledger_settlement(uuid)', 'predecessor_sha256': '95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2', 'installed_sha256': 'c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.post_supplier_payment(uuid)', 'predecessor_sha256': '3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60', 'installed_sha256': '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.reverse_material_purchase_cost_correction(uuid,text)', 'predecessor_sha256': '2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b', 'installed_sha256': 'dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.reverse_material_supplier_invoice(uuid,text)', 'predecessor_sha256': 'c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb', 'installed_sha256': '76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.reverse_material_supplier_return(uuid,text)', 'predecessor_sha256': '570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6', 'installed_sha256': 'ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.reverse_opening_financial_correction(uuid,text)', 'predecessor_sha256': '5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c', 'installed_sha256': '1ce99785ee8dc682b1b0f2aa9171f2110614baf4c9a99ecf4880b547496947fe', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.reverse_opening_subledger_settlement(uuid,text)', 'predecessor_sha256': 'd5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e', 'installed_sha256': 'c01292aebb98ea09d0fb440215f9c4cdbd9ece3b98caa641b9b308faec542e1a', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.reverse_supplier_payment(uuid,text)', 'predecessor_sha256': 'b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be', 'installed_sha256': '9733b0e39d82732fb4b2ec7be17c66bcff2a088a81cccd25892eb440d4923102', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': '368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea', 'installed_sha256': 'efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': '2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff', 'installed_sha256': '48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
    ],

    'N': [{'identity': 'erp.post_material_purchase_cost_correction(uuid)',
      'predecessor_sha256': '9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9',
      'installed_sha256': '5839dee0ab9db69ebabf5f08894b5c6603c851c1d55aa9eff30a12dd0331dff9',
      'owner': 'postgres',
      'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
     {'identity': 'erp.post_material_supplier_invoice(uuid)',
      'predecessor_sha256': '65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69',
      'installed_sha256': 'da4ce12c6f41625933511e6fd59246c2410b80ce02ddf865c489803070f7b8b0',
      'owner': 'postgres',
      'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
     {'identity': 'erp.post_material_supplier_return(uuid)',
      'predecessor_sha256': 'f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1',
      'installed_sha256': 'b4ac34b5df0e35f0cf1afe85d4a92e0b369922f91d0ce9eb4e2589a71367d607',
      'owner': 'postgres',
      'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
     {'identity': 'erp.reverse_material_purchase_cost_correction(uuid,text)',
      'predecessor_sha256': 'dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f',
      'installed_sha256': '9913ee82901495aa850712c29d21ab8a8b96a5d71c29fca20fb0844b1af1dddd',
      'owner': 'postgres',
      'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
     {'identity': 'erp.reverse_material_supplier_invoice(uuid,text)',
      'predecessor_sha256': '76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e',
      'installed_sha256': 'b4b10a9021e4360a25327656217fac0ed8a171748c215af2291ed00539684cb2',
      'owner': 'postgres',
      'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
     {'identity': 'erp.reverse_material_supplier_return(uuid,text)',
      'predecessor_sha256': 'ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b',
      'installed_sha256': '5659d9755c81ae4134a494d1ebd0aaaec29ed82b75a5a32bdfd6d048e6ebaca3',
      'owner': 'postgres',
      'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
     {'identity': 'erp.run_v267_financial_truth_checks()',
      'predecessor_sha256': 'efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa',
      'installed_sha256': 'f50decac0d38f9ddc2cfc5a28af53607fb8c1cf38cde5a65f13b38ec748a6fda',
      'owner': 'postgres',
      'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}],

    'O': [
      {'identity': 'erp.post_material_supplier_return(uuid)',
       'predecessor_sha256': 'b4ac34b5df0e35f0cf1afe85d4a92e0b369922f91d0ce9eb4e2589a71367d607',
       'installed_sha256': 'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace',
       'owner': 'postgres',
       'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
      {'identity': 'erp.run_v267_financial_truth_checks()',
       'predecessor_sha256': 'f50decac0d38f9ddc2cfc5a28af53607fb8c1cf38cde5a65f13b38ec748a6fda',
       'installed_sha256': 'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0',
       'owner': 'postgres',
       'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
    ],
    'P': [
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': '98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1', 'installed_sha256': '17a07e10665756088f2faa0570c055efae4513abf1c5985afacf86bf8467e056', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_material_supplier_return(uuid)', 'predecessor_sha256': 'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace', 'installed_sha256': '541ce87729dd47bffd536847e71271c1e0b968d199e2fe24fd671a025cee027a', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': 'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0', 'installed_sha256': '2c546026b1325e265c62828c13f2eea63aaff302c9a359d5f49c18d5fb7a492e', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
    ],

    'Q': [
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': '17a07e10665756088f2faa0570c055efae4513abf1c5985afacf86bf8467e056', 'installed_sha256': 'edefb0fa134200d5d541bfdb6ab1b4b81e28b8cd912eff0a7c1ef59106744917', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_material_supplier_invoice(uuid)', 'predecessor_sha256': 'da4ce12c6f41625933511e6fd59246c2410b80ce02ddf865c489803070f7b8b0', 'installed_sha256': '727382a2c3b8464526bb5a8a66c68813be439fb931ca94d993898fecc1e41faf', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.refresh_material_purchase_item_match_state(uuid)', 'predecessor_sha256': '7ff2434fb46099077d3891359a161cfcf5fac8f4f8ca80f549b4d2e7ef6f8658', 'installed_sha256': '351dc9ea86baa9cda11047468f58db5f69044c9860ce5ca7315dcc9ec6e1acd5', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': '2c546026b1325e265c62828c13f2eea63aaff302c9a359d5f49c18d5fb7a492e', 'installed_sha256': '04115f87a2dd4777a56ed3667b461f71fb972887eccd1c9b5281878660a3acc3', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
    ],

    'R': [
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': 'edefb0fa134200d5d541bfdb6ab1b4b81e28b8cd912eff0a7c1ef59106744917', 'installed_sha256': '8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.reverse_material_purchase(uuid,text)', 'predecessor_sha256': '9b637facd36bcf810e11350fc97a1e0da68cbb77b67aec54697b3ae52cd820b3', 'installed_sha256': '5ed3d75116f42f558829e1707f58c28fd1c81a2c66004ae54cf52069b147d4e1', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']},
        {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': '04115f87a2dd4777a56ed3667b461f71fb972887eccd1c9b5281878660a3acc3', 'installed_sha256': 'ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
    ],

    'S': [
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': '8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2', 'installed_sha256': '2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_supplier_payment(uuid)', 'predecessor_sha256': '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8', 'installed_sha256': 'ad780c4b00261b6ee1890391cac1c459c23d06b041859399e6ccc2f73d67f421', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': 'ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066', 'installed_sha256': 'e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
    ],
    'T': [{'acl': ['postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp._v268_financial_report_checks_pre_scope()',
  'installed_sha256': '8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196',
  'owner': 'postgres',
  'predecessor_sha256': '2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad'},
 {'acl': ['postgres=X/postgres'],
  'identity': 'erp.resolve_accounting_transaction_date(date)',
  'installed_sha256': '92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48',
  'owner': 'postgres',
  'predecessor_sha256': '13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769'},
 {'acl': ['postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp.reverse_journal(uuid,text)',
  'installed_sha256': 'a6f635cd2319a68a1afa522fa4682921a6f7b80afd0e31fbdc4271cf53fcfef4',
  'owner': 'postgres',
  'predecessor_sha256': '3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1'},
 {'acl': ['postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp.reverse_material_adjustment(uuid,text)',
  'installed_sha256': 'c90fd34d4045a060ae4d36413d6520068281066d0de52dc766583c5f6e7d7288',
  'owner': 'postgres',
  'predecessor_sha256': '38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043'},
 {'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp.run_v267_financial_truth_checks()',
  'installed_sha256': 'acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8',
  'owner': 'postgres',
  'predecessor_sha256': 'e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89'},
 {'acl': ['postgres=X/postgres'],
  'identity': 'erp.sync_material_cost_revaluation(uuid)',
  'installed_sha256': '3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0',
  'owner': 'postgres',
  'predecessor_sha256': '57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83'}],
    'U': [
        {'identity': 'erp._cp3_r4_reverse_journal_internal(uuid,text)', 'predecessor_sha256': '9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249', 'installed_sha256': '2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c', 'owner': 'postgres', 'acl': ['postgres=X/postgres']},
        {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': '8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196', 'installed_sha256': '3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.get_owner_financial_snapshot_v2(date,date,date)', 'predecessor_sha256': 'e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c', 'installed_sha256': '0afb94d932b1c7488c1a787de7f734133c1674e0a43100d366c6f3f129ffb9bb', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_material_adjustment(uuid)', 'predecessor_sha256': 'be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83', 'installed_sha256': 'b32962d12adde0ca4ae659f2dd83a02a0a3111c3a9060d845ed2e82025696201', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.post_material_purchase(uuid)', 'predecessor_sha256': '83f51a14eef3b2942b7158e81c2db1ee1e7ec401368fd8abb6bc013bf1be95de', 'installed_sha256': '17547ee019fca617bf67100d9b3b899b96781a2fa62cc47c57bb2dbafe358082', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': 'acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8', 'installed_sha256': 'f32dcd6d6be2ef1f2762bce1dac463aeeed8965f4ef94f8e7a31f8da4451e6ce', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']},
        {'identity': 'erp.sync_material_purchase_grni_on_status()', 'predecessor_sha256': '7537c077a003924fce425c9db9769824fc5ffdd0e761e7b292508b1e248ad870', 'installed_sha256': 'e39d7cc4b457a58b929894f4fd5a9c7f47aa0da678853a3ddbee65f9630d676c', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']},
    ],

    'V': [{'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp.post_misc_finance(uuid)',
  'installed_sha256': 'f2e403942beaeb68a31057f5a0439f87da89519a9ba02f105907aa415c488c00',
  'owner': 'postgres',
  'predecessor_sha256': '1f8973f9426efe3555a587e0df5e8a852e4431464db651ec6f630ef1893a098c'},
 {'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp.run_v267_financial_truth_checks()',
  'installed_sha256': '13e1c0b7e3a9262aecd18504cb70890eeaeb61190c12e2cc7bb16f2e2d9ddfb2',
  'owner': 'postgres',
  'predecessor_sha256': 'f32dcd6d6be2ef1f2762bce1dac463aeeed8965f4ef94f8e7a31f8da4451e6ce'},
 {'acl': ['postgres=X/postgres', 'service_role=X/postgres'],
  'identity': 'erp._v268_financial_report_checks_pre_scope()',
  'installed_sha256': 'bdce68bf47700519d663e63302b5d48a720959d1c9995fcb9d8599a9516c2eef',
  'owner': 'postgres',
  'predecessor_sha256': '3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775'}],

    'W': [
  {
    "acl": [
      "authenticated=X/postgres",
      "postgres=X/postgres",
      "service_role=X/postgres"
    ],
    "identity": "erp.post_scrap_sale(uuid)",
    "installed_sha256": "cb573efa942bbf65e770dd645cc0636ea4142633241af16842b532f36ce32131",
    "owner": "postgres",
    "predecessor_sha256": "53e2b8c582b342b2b4391a3fdcf91308c0e0e0f08e021c9f800b99212f64d39c"
  },
  {
    "acl": [
      "authenticated=X/postgres",
      "postgres=X/postgres",
      "service_role=X/postgres"
    ],
    "identity": "erp.run_v267_financial_truth_checks()",
    "installed_sha256": "845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a",
    "owner": "postgres",
    "predecessor_sha256": "13e1c0b7e3a9262aecd18504cb70890eeaeb61190c12e2cc7bb16f2e2d9ddfb2"
  },
  {
    "acl": [
      "postgres=X/postgres",
      "service_role=X/postgres"
    ],
    "identity": "erp._v268_financial_report_checks_pre_scope()",
    "installed_sha256": "c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507",
    "owner": "postgres",
    "predecessor_sha256": "bdce68bf47700519d663e63302b5d48a720959d1c9995fcb9d8599a9516c2eef"
  }
],
    'AB': [
        {"acl":["postgres=X/postgres"],"identity":"erp.sync_material_cost_revaluation(uuid)","installed_sha256":"af752a5cb068d71af90c646718b55ef2b6eabd9319021202a0d8f92042892f91","owner":"postgres","predecessor_sha256":"3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0"},
        {"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.process_cost_recalc_queue(integer)","installed_sha256":"7fe85b6739fa5684171cffd26d028eabd35efe3bb2691e2daa9e52cf40892a13","owner":"postgres","predecessor_sha256":"4b0b4841ad3a6b4d72b86f8e4fb1958ba2dda0dad4ddb65c9c085c7c2358cc3f"},
        {"acl":["postgres=X/postgres"],"identity":"erp.resolve_accounting_transaction_date(date)","installed_sha256":"656ac4cd3ae6a2df24bd11f4c1c044c3e9bf423cc6c7343ab863bad16eee6803","owner":"postgres","predecessor_sha256":"92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48"},
        {"acl":["postgres=X/postgres"],"identity":"erp._cp3_r4_reverse_journal_internal(uuid,text)","installed_sha256":"2996d1c16396768097306556b5916ba93996d2ff451f3c5e7cd35deea7a3ac6f","owner":"postgres","predecessor_sha256":"2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c"},
        {"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_journal(text,uuid,date,text,jsonb)","installed_sha256":"0a84003a5e6a27cc445e835673d4f5030cbc19cb6b130037eaed922340d34d77","owner":"postgres","predecessor_sha256":"1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf"},
    ],
    'AA': [
        dict(identity='erp.refresh_material_cost_checkpoint(uuid,date)', predecessor_sha256='cbb3d27608c720380b099a020a2f54b639ffc9626d3a09fd258402eb15511978', installed_sha256='7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a', owner='postgres', acl=_acl('postgres')),
        dict(identity='erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)', predecessor_sha256='e70bce5bc64114ac0dad5c0ccbc374a63590089d9f481007d6c609f82f323399', installed_sha256='c1f74ab9e855bf354d62f0e9053883c7cc0efdfeb329de8f2e081e46852f50b6', owner='postgres', acl=_acl('postgres')),
    ],
    'Z': [dict(identity='erp.close_accounting_through(date,text)', predecessor_sha256='c9517690638ac40bb8914e0613b7d5bdf92256274e9c5551747060d09a79536b', installed_sha256='7f20b0a381b049391fc3e33dce00b3b8c517b0b77ae8f2b2756cac5e0a021b42', owner='postgres', acl=_acl('authenticated', 'postgres'))],
    'Y': [{'identity': 'erp.post_opening_subledger_settlement(uuid)', 'predecessor_sha256': 'c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393', 'installed_sha256': 'b709ed64c78b09c113e6e0541eb757b5367dfbf7dd51752a26827207fc12e97e', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres']}, {'identity': 'erp.post_vendor_payment(uuid)', 'predecessor_sha256': '05b067af75c8691c4e012ff719f8793dbe597ee5f0e451db665d4baab1427316', 'installed_sha256': 'cf8c1105cb6426583464d7516eb70693c28d668702ae3eb23c22f4029f07f763', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}, {'identity': 'erp.post_sales_payment(uuid)', 'predecessor_sha256': '362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c', 'installed_sha256': '605db7b1ce7bea6b54e70625092f8e98365d3966dc09d220be7dff81014a1f1d', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}, {'identity': 'erp.run_v267_financial_truth_checks()', 'predecessor_sha256': '845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a', 'installed_sha256': '7ead45b0a09258adcf1b9a9dae44b5627c2ba6fec36767f513706d282f076a9c', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}, {'identity': 'erp._v268_financial_report_checks_pre_scope()', 'predecessor_sha256': 'c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507', 'installed_sha256': 'f95aeb7875cd2a7de603ad33c86cff7c7b0849b7d7f401e9280962b4733c7d45', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']}, {'identity': 'erp.run_v268_financial_report_checks()', 'predecessor_sha256': '48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1', 'installed_sha256': '416b8c53665c4c2b814d4621935a9291797fdbf49067deb0a910d16dc90685fd', 'owner': 'postgres', 'acl': ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres']}],
    'X': [{'identity': 'erp.require_internal()', 'predecessor_sha256': 'da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f', 'installed_sha256': '5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e', 'owner': 'postgres', 'acl': ['postgres=X/postgres', 'service_role=X/postgres']}],

}

# AC has a deliberately broad generated capsule. Keep its independent trust
# roots in the reviewed JSON pin set instead of duplicating 115 hashes here.
_ac_pin_payload = json.loads(
    Path('docs/evidence/cp6-ac-runtime-pins.json').read_text(encoding='utf-8')
)
TRUSTED_FUNCTIONS['AC'] = [
    {
        'identity': item['identity'],
        'predecessor_sha256': item['before_sha'],
        'installed_sha256': item['after_sha'],
        'owner': item['owner'],
        'acl': item['acl'],
    }
    for item in _ac_pin_payload['functions']
]


class MaintenanceRollbackError(RuntimeError):
    """A fail-closed maintenance boundary refused or could not finish."""


def _public_failure_code(exc: Exception) -> str:
    """Return a non-sensitive serialization code; never persist exception text."""
    if isinstance(exc, MaintenanceRollbackError):
        return 'MAINTENANCE_ROLLBACK_REJECTED'
    return 'MAINTENANCE_RUNTIME_FAILED'


def _scalar(conn: psycopg.Connection, query: Any, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return row[0] if row else None


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(report, indent=2, default=str) + '\n')
    temporary.replace(path)


def _phase(path: Path, report: dict[str, Any], name: str, **facts: Any) -> None:
    report['phase'] = name
    report.setdefault('phases', []).append({
        'phase': name,
        'observed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        **facts,
    })
    _write_report(path, report)


def _sessions(control: psycopg.Connection, database: str, keep_pid: int) -> list[dict[str, Any]]:
    with control.cursor() as cur:
        cur.execute(
            """select pid,application_name,state,backend_type,
                      xact_start::text,query_start::text,wait_event_type,wait_event,query
               from pg_stat_activity
               where datname=%s and pid<>%s and backend_type='client backend'
               order by case when state='active' then 0 else 1 end,pid""",
            (database, keep_pid),
        )
        columns = [column.name for column in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def _capsule_snapshot(
    target_conn: psycopg.Connection, target_name: str, target: dict[str, Any]
) -> list[dict[str, Any]]:
    if target_name == 'AK':
        from cp6_v2620ak_runtime import pins, verified_successor
        TRUSTED_FUNCTIONS['AK'] = pins()['functions']
        with target_conn.cursor() as ak_cur:
            verified_successor(ak_cur, pre_admission=True)
    if target_name == 'AJ':
        from cp6_v2620aj_runtime import pins, verified_successor
        TRUSTED_FUNCTIONS['AJ'] = pins()['functions']
        with target_conn.cursor() as aj_cur:
            verified_successor(aj_cur, pre_admission=True)
    if target_name == 'AI':
        from cp6_v2620ai_runtime import pins, verified_successor
        TRUSTED_FUNCTIONS['AI'] = pins()['functions']
        with target_conn.cursor() as ai_cur:
            verified_successor(ai_cur, pre_admission=True)
    if target_name == 'AH':
        from cp6_v2620ah_runtime import pins, verified_successor
        TRUSTED_FUNCTIONS['AH'] = pins()['functions']
        with target_conn.cursor() as ah_cur:
            verified_successor(ah_cur, pre_admission=True)
    if target_name == 'AG':
        from cp6_v2620ag_runtime import pins, verified_successor
        TRUSTED_FUNCTIONS['AG'] = pins()['functions']
        with target_conn.cursor() as ag_cur:
            verified_successor(ag_cur, pre_admission=True)
    if target_name == 'AF':
        from cp6_v2620af_runtime import pins, verify_inherited_ae
        TRUSTED_FUNCTIONS['AF'] = pins()['functions']
        with target_conn.cursor() as af_cur:
            verify_inherited_ae(af_cur, pre_admission=True)
    if target_name == 'AE':
        from cp6_v2620ae_runtime import pins, verify_inherited_ad
        # AE replaces AD's two live definitions, so bind AE's exact pins while
        # checking AD through its stored edge and the unchanged AC runtime.
        TRUSTED_FUNCTIONS['AE'] = pins()['functions']
        with target_conn.cursor() as ae_cur:
            verify_inherited_ad(ae_cur, pre_admission=True)
    if target_name == 'AD':
        from cp6_v2620ad_runtime import pins, verify_ac_pre_admission
        # Bind AD's two pins independently and avoid relation deparsing until
        # old sessions drain, preserving the AC report-lock repair.
        TRUSTED_FUNCTIONS['AD'] = pins()['functions']
        with target_conn.cursor() as ad_cur:
            verify_ac_pre_admission(ad_cur)
    if target_name == 'AC':
        from cp6_v2620ac_runtime import verified_pre_admission_successor
        with target_conn.cursor() as ac_cur:
            # View/default deparsing can wait behind the REPORT writer's
            # deliberate table gate.  Before admission closes, inspect only
            # the exact function capsule/live state needed for restoration.
            # The full relation proof is mandatory after the drain below.
            all_objects = verified_pre_admission_successor(ac_cur)
        functions = [
            item for item in all_objects.values() if item['kind'] == 'FUNCTION'
        ]
        if len(functions) != target['capsule_count']:
            raise MaintenanceRollbackError('AC_TRUSTED_RUNTIME_CARDINALITY_MISMATCH')
        return [
            {
                'identity': item['identity'],
                'predecessor_sha256': item['predecessor_sha256'],
                'predecessor_definition_sha256': item['predecessor_sha256'],
                'installed_sha256': item['installed_sha256'],
                'owner': item['owner'],
                'acl': item['acl'],
                'observed_installed_sha256': item['installed_sha256'],
                'observed_installed_owner': item['owner'],
                'observed_installed_acl': item['acl'],
            }
            for item in functions
        ]
    # N adds helper and fact objects inherited by O/P outside their predecessor capsules.
    # Verify them before any admission mutation; F through M follow their original path.
    if target_name in {'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'AA', 'AB'}:
        if target_name == 'AB':
            from cp6_v2620ab_runtime import verify_extra_objects
        elif target_name == 'AA':
            from cp6_v2620aa_runtime import verify_extra_objects
        elif target_name == 'Z':
            from cp6_v2620z_runtime import verify_extra_objects
        elif target_name == 'Y':
            from cp6_v2620y_runtime import verify_extra_objects
        elif target_name == 'X':
            from cp6_v2620x_runtime import verify_extra_objects
        elif target_name == 'W':
            from cp6_v2620w_runtime import verify_extra_objects
        elif target_name == 'V':
            from cp6_v2620v_runtime import verify_extra_objects
        elif target_name == 'U':
            from cp6_v2620u_runtime import verify_extra_objects
        elif target_name == 'T':
            from cp6_v2620t_runtime import verify_extra_objects
        elif target_name == 'S':
            from cp6_v2620s_runtime import verify_extra_objects
        elif target_name == 'R':
            from cp6_v2620r_runtime import verify_extra_objects
        elif target_name == 'Q':
            from cp6_v2620q_runtime import verify_extra_objects
        elif target_name == 'P':
            from cp6_v2620p_runtime import verify_extra_objects
        elif target_name == 'O':
            from cp6_v2620o_runtime import verify_extra_objects
        else:
            from cp6_v2620n_runtime import verify_extra_objects
        with target_conn.cursor() as extra_cur:
            verify_extra_objects(extra_cur)
    capsule = sql.Identifier(*target['capsule'].split('.'))
    query = sql.SQL(
        """select c.object_regidentity,c.definition_sha256,
                  encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex'),
                  c.installed_definition_sha256,c.owner_snapshot,c.acl_snapshot,
                  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
                  pg_get_userbyid(p.proowner),
                  case when p.proacl is null then null else
                    array(select a::text from unnest(p.proacl) a order by a::text) end
           from {} c left join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
           order by c.object_regidentity"""
    ).format(capsule)
    with target_conn.cursor() as cur:
        cur.execute(query)
        rows = [
            {
                'identity': row[0],
                'predecessor_sha256': row[1],
                'predecessor_definition_sha256': row[2],
                'installed_sha256': row[3],
                'owner': row[4],
                'acl': row[5],
                'observed_installed_sha256': row[6],
                'observed_installed_owner': row[7],
                'observed_installed_acl': row[8],
            }
            for row in cur.fetchall()
        ]
    if len(rows) != target['capsule_count']:
        raise MaintenanceRollbackError(
            f"Target capsule count {len(rows)} != {target['capsule_count']}"
        )
    expected = TRUSTED_FUNCTIONS[target_name]
    trusted_by_identity = {item['identity']: item for item in expected}
    if len(trusted_by_identity) != len(expected) or set(trusted_by_identity) != {
        item['identity'] for item in rows
    }:
        raise MaintenanceRollbackError('TRUSTED_PREDECESSOR_PIN_MISMATCH: capsule identities')
    for item in rows:
        trusted = trusted_by_identity[item['identity']]
        if (
            item['predecessor_sha256'] != trusted['predecessor_sha256']
            or item['predecessor_definition_sha256'] != trusted['predecessor_sha256']
            or item['installed_sha256'] != trusted['installed_sha256']
            or item['observed_installed_sha256'] != trusted['installed_sha256']
            or item['owner'] != trusted['owner']
            or item['observed_installed_owner'] != trusted['owner']
            or item['acl'] != trusted['acl']
            or item['observed_installed_acl'] != trusted['acl']
        ):
            raise MaintenanceRollbackError(
                'TRUSTED_PREDECESSOR_PIN_MISMATCH: ' + item['identity']
            )
    return rows


def _function_snapshot(
    target_conn: psycopg.Connection, expected: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    with target_conn.cursor() as cur:
        for item in expected:
            expected_hash = item.get('predecessor_sha256', item.get('sha256'))
            cur.execute(
                """select encode(extensions.digest(convert_to(
                         pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
                         pg_get_userbyid(p.proowner),
                         case when p.proacl is null then null else
                           array(select a::text from unnest(p.proacl) a order by a::text) end
                   from pg_proc p where p.oid=to_regprocedure(%s)""",
                (item['identity'],),
            )
            row = cur.fetchone()
            if row is None:
                raise MaintenanceRollbackError(
                    f"Restored function is missing: {item['identity']}"
                )
            actual = {
                'identity': item['identity'],
                'sha256': row[0],
                'owner': row[1],
                'acl': row[2],
            }
            wanted = {
                'identity': item['identity'],
                'sha256': expected_hash,
                'owner': item['owner'],
                'acl': item['acl'],
            }
            if actual != wanted:
                raise MaintenanceRollbackError(
                    f"Exact predecessor function/ACL mismatch: {item['identity']}"
                )
            observed.append(actual)
    return observed


def _reject_ambiguous_conninfo(value: str, label: str) -> None:
    """Accept one closed, authority-based URI shape before libpq normalization.

    ``conninfo_to_dict`` intentionally applies libpq's last-key-wins behavior.
    That is useful for ordinary clients but unsafe at this maintenance boundary:
    a duplicate host/user/database/password key must be rejected, not silently
    normalized.  The reviewed executor needs no keyword conninfo and no query
    parameters, so this deliberately narrow grammar removes both ambiguity
    classes before any connection attempt.
    """
    if not isinstance(value, str) or not value.startswith('postgresql://'):
        raise MaintenanceRollbackError(
            f'Refusing {label} conninfo outside canonical postgresql URI grammar'
        )
    if '?' in value or '#' in value:
        raise MaintenanceRollbackError(
            f'Refusing ambiguous {label} conninfo query/fragment parameters'
        )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise MaintenanceRollbackError(f'Refusing malformed {label} endpoint') from None
    if (
        parsed.scheme != 'postgresql'
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.hostname is None
        or parsed.username is None
        or parsed.password is None
        or port is None
        or not parsed.path.startswith('/')
        or parsed.path.count('/') != 1
        or not parsed.path[1:]
    ):
        raise MaintenanceRollbackError(f'Refusing malformed {label} endpoint')


def _validate_connections(target_pgurl: str, maintenance_pgurl: str) -> tuple[str, str]:
    _reject_ambiguous_conninfo(target_pgurl, 'rollback')
    _reject_ambiguous_conninfo(maintenance_pgurl, 'admission-control')
    try:
        target_info = conninfo_to_dict(target_pgurl)
        maintenance_info = conninfo_to_dict(maintenance_pgurl)
    except Exception:
        raise MaintenanceRollbackError('Refusing invalid maintenance conninfo') from None
    allowed_conninfo = {'dbname', 'host', 'password', 'port', 'user'}
    for label, info in (('rollback', target_info), ('admission-control', maintenance_info)):
        unexpected = sorted(set(info) - allowed_conninfo)
        if unexpected:
            raise MaintenanceRollbackError(
                f"Refusing {label} connection parameters outside allowlist: {unexpected}"
            )
        if not info.get('password'):
            raise MaintenanceRollbackError(f'Refusing {label} endpoint without password')
    database = target_info.get('dbname', '')
    maintenance_database = maintenance_info.get('dbname', '')
    if database not in {'cp6_rollback', 'postgres'}:
        raise MaintenanceRollbackError('Refusing non-allowlisted rollback database')
    if database == 'postgres' and os.environ.get(
        'CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE'
    ) != database:
        raise MaintenanceRollbackError(
            'Refusing postgres without CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE=postgres'
        )
    expected_target = {
        'host': '127.0.0.1', 'port': '54322', 'user': 'postgres', 'dbname': database,
    }
    expected_maintenance = {
        'host': '127.0.0.1', 'port': '54322',
        'user': 'cp6_maintenance_admission', 'dbname': 'template1',
    }
    if any(target_info.get(key) != value for key, value in expected_target.items()):
        raise MaintenanceRollbackError('Refusing non-allowlisted rollback endpoint')
    if any(
        maintenance_info.get(key) != value
        for key, value in expected_maintenance.items()
    ):
        raise MaintenanceRollbackError('Refusing non-allowlisted admission-control endpoint')
    confirmed = os.environ.get('CP6_MAINTENANCE_CONFIRM_DATABASE')
    if confirmed != database:
        raise MaintenanceRollbackError(
            'CP6_MAINTENANCE_CONFIRM_DATABASE must exactly name the target database'
        )
    return database, maintenance_database


def _endpoint_snapshot(conn: psycopg.Connection) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """select current_database(),current_user,inet_server_addr()::text,
                      inet_server_port(),(pg_control_system()).system_identifier::text"""
        )
        row = cur.fetchone()
    return {
        'database': row[0],
        'user': row[1],
        'server_address': row[2],
        'server_port': row[3],
        'system_identifier': row[4],
    }


def run_maintenance_rollback(
    *,
    target_name: str,
    target_pgurl: str,
    maintenance_pgurl: str,
    report_path: Path,
    drain_timeout: float,
    natural_grace: float,
    terminate_after_grace: bool,
    pause_after_close_file: Path | None = None,
    continue_file: Path | None = None,
) -> dict[str, Any]:
    if target_name not in TARGETS:
        raise MaintenanceRollbackError(f'Unsupported rollback target: {target_name}')
    target = TARGETS[target_name]
    database, maintenance_database = _validate_connections(target_pgurl, maintenance_pgurl)
    rollback_path = target['rollback'].resolve()
    repository = Path.cwd().resolve()
    if repository not in rollback_path.parents or not rollback_path.is_file():
        raise MaintenanceRollbackError('Reviewed rollback path is absent or outside the repository')
    rollback_bytes = rollback_path.read_bytes()
    rollback_sha256 = hashlib.sha256(rollback_bytes).hexdigest()
    if rollback_sha256 != target['rollback_sha256']:
        raise MaintenanceRollbackError(
            f"Reviewed rollback checksum mismatch: {rollback_sha256}"
        )
    report: dict[str, Any] = {
        'contract': 'CP6_PREUSE_ROLLBACK_MAINTENANCE_V2',
        'target': target_name,
        'database': database,
        'maintenance_database': maintenance_database,
        'rollback_path': str(target['rollback']),
        'rollback_sha256': rollback_sha256,
        'terminate_after_grace': terminate_after_grace,
        'drain_timeout_seconds': drain_timeout,
        'natural_grace_seconds': natural_grace,
        'admission_closed': False,
        'rollback_started': False,
        'rollback_committed': False,
        'admission_reopened': False,
        'status': 'RUNNING',
        'trusted_predecessor_identity_count': target['capsule_count'],
    }
    _phase(report_path, report, 'PREFLIGHT')

    rollback_conn: psycopg.Connection | None = None
    control: psycopg.Connection | None = None
    lock_held = False
    try:
        rollback_conn = psycopg.connect(
            target_pgurl,
            autocommit=True,
            application_name=f'cp6-maintenance-{target_name.lower()}-rollback',
        )
        control = psycopg.connect(
            maintenance_pgurl,
            autocommit=True,
            application_name='cp6-maintenance-admission-control',
        )
        rollback_pid = int(_scalar(rollback_conn, 'select pg_backend_pid()'))
        target_endpoint = _endpoint_snapshot(rollback_conn)
        control_endpoint = _endpoint_snapshot(control)
        report['target_endpoint'] = target_endpoint
        report['admission_control_endpoint'] = control_endpoint
        expected_target_identity = {'database': database, 'user': 'postgres'}
        expected_control_identity = {
            'database': maintenance_database,
            'user': 'cp6_maintenance_admission',
        }
        for key, value in expected_target_identity.items():
            if target_endpoint.get(key) != value:
                raise MaintenanceRollbackError(
                    f'Connected rollback endpoint identity mismatch: {key}'
                )
        for key, value in expected_control_identity.items():
            if control_endpoint.get(key) != value:
                raise MaintenanceRollbackError(
                    f'Connected admission-control endpoint identity mismatch: {key}'
                )
        for key in ('server_address', 'server_port', 'system_identifier'):
            if not target_endpoint.get(key) or target_endpoint.get(key) != control_endpoint.get(key):
                raise MaintenanceRollbackError(
                    f'Target/admission-control runtime cluster mismatch: {key}'
                )
        _phase(report_path, report, 'ENDPOINT_VERIFIED', rollback_pid=rollback_pid)
        if not _scalar(control, 'select rolsuper from pg_roles where rolname=current_user'):
            raise MaintenanceRollbackError('Admission control requires a database superuser')
        if not _scalar(
            control, 'select exists(select 1 from pg_database where datname=%s)', (database,)
        ):
            raise MaintenanceRollbackError('Target database no longer exists')
        _scalar(
            control,
            "select pg_advisory_lock(hashtextextended('CP6_PREUSE_ROLLBACK_MAINTENANCE',0))",
        )
        lock_held = True
        capsule = _capsule_snapshot(rollback_conn, target_name, target)
        report['capsule_observation'] = capsule
        _phase(report_path, report, 'CAPSULE_VERIFIED', rollback_pid=rollback_pid)

        with control.cursor() as cur:
            cur.execute(
                sql.SQL('alter database {} with allow_connections false').format(
                    sql.Identifier(database)
                )
            )
        if _scalar(control, 'select datallowconn from pg_database where datname=%s', (database,)):
            raise MaintenanceRollbackError('Database admission did not close')
        report['admission_closed'] = True
        _phase(report_path, report, 'ADMISSION_CLOSED', rollback_pid=rollback_pid)

        if pause_after_close_file is not None:
            pause_after_close_file.parent.mkdir(parents=True, exist_ok=True)
            pause_after_close_file.write_text('ADMISSION_CLOSED\n')
        if continue_file is not None:
            deadline = time.monotonic() + drain_timeout
            while not continue_file.exists() and time.monotonic() < deadline:
                time.sleep(.025)
            if not continue_file.exists():
                raise MaintenanceRollbackError('Admission-close test barrier timed out')

        natural_deadline = time.monotonic() + natural_grace
        active = _sessions(control, database, rollback_pid)
        report['sessions_at_close'] = active
        while active and time.monotonic() < natural_deadline:
            time.sleep(.025)
            active = _sessions(control, database, rollback_pid)
        report['sessions_after_natural_grace'] = active

        terminated: list[dict[str, Any]] = []
        if active and terminate_after_grace:
            with control.cursor() as cur:
                for session in active:
                    cur.execute('select pg_terminate_backend(%s)', (session['pid'],))
                    terminated.append({**session, 'terminate_requested': bool(cur.fetchone()[0])})
        report['terminated_sessions'] = terminated
        drain_deadline = time.monotonic() + drain_timeout
        active = _sessions(control, database, rollback_pid)
        while active and time.monotonic() < drain_deadline:
            time.sleep(.025)
            active = _sessions(control, database, rollback_pid)
        report['sessions_after_drain'] = active
        if active:
            raise MaintenanceRollbackError('DRAIN_TIMEOUT: old client invocations remain')
        if _scalar(control, 'select datallowconn from pg_database where datname=%s', (database,)):
            raise MaintenanceRollbackError('Admission reopened before rollback')

        # Only after every old invocation is gone can AC safely repeat the
        # parser-normalized source-to-live view proof.  Rollback remains
        # forbidden if this stronger second pass detects coordinated capsule
        # and live-definition drift; admission stays closed on failure.
        if target_name in {'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK'}:
            if target_name == 'AK':
                from cp6_v2620ak_runtime import verified_successor
            elif target_name == 'AJ':
                from cp6_v2620aj_runtime import verified_successor
            elif target_name == 'AI':
                from cp6_v2620ai_runtime import verified_successor
            elif target_name == 'AH':
                from cp6_v2620ah_runtime import verified_successor
            elif target_name == 'AG':
                from cp6_v2620ag_runtime import verified_successor
            elif target_name == 'AF':
                from cp6_v2620af_runtime import verified_successor
            elif target_name == 'AE':
                from cp6_v2620ae_runtime import verified_successor
            elif target_name == 'AD':
                from cp6_v2620ad_runtime import verified_successor
            else:
                from cp6_v2620ac_runtime import verified_successor
            with rollback_conn.cursor() as ac_cur:
                post_drain_objects = verified_successor(ac_cur)
            expected_count = {'AC': 272, 'AD': 274, 'AE': 276, 'AF': 278, 'AG': 690, 'AH': 690, 'AI': 690, 'AJ': 690, 'AK': 690}[target_name]
            if len(post_drain_objects) != expected_count:
                raise MaintenanceRollbackError(
                    target_name + '_POST_DRAIN_RUNTIME_CARDINALITY_MISMATCH'
                )
            report['post_drain_full_source_verification'] = {
                'object_count': len(post_drain_objects),
                'parser_normalized_views': True,
            }
        _phase(report_path, report, 'DRAINED', terminated_count=len(terminated))

        report['rollback_started'] = True
        _phase(report_path, report, 'ROLLBACK_STARTED')
        with rollback_conn.cursor() as cur:
            cur.execute(rollback_bytes.decode('utf-8'), prepare=False)
        report['rollback_committed'] = True
        _phase(report_path, report, 'ROLLBACK_COMMITTED')

        marker_count = int(_scalar(
            rollback_conn,
            'select count(*) from erp.schema_migrations where version=%s',
            (target['marker'],),
        ))
        predecessor_count = int(_scalar(
            rollback_conn,
            'select count(*) from erp.schema_migrations where version=%s',
            (target['predecessor'],),
        ))
        platform_count = int(_scalar(
            rollback_conn,
            'select count(*) from supabase_migrations.schema_migrations where name=%s',
            (target['platform'],),
        ))
        capsule_present = bool(_scalar(
            rollback_conn, 'select to_regclass(%s) is not null', (target['capsule'],)
        ))
        extra_capsules_present = {
            identity: bool(_scalar(
                rollback_conn, 'select to_regclass(%s) is not null', (identity,)
            ))
            for identity in target.get('extra_capsules', [])
        }
        if (
            (marker_count, predecessor_count, platform_count, capsule_present)
            != (0, 1, 0, False)
            or any(extra_capsules_present.values())
        ):
            raise MaintenanceRollbackError('Exact predecessor marker/capsule postcondition failed')
        report['restored_functions'] = _function_snapshot(rollback_conn, capsule)
        report['postconditions'] = {
            'target_marker_count': marker_count,
            'predecessor_marker_count': predecessor_count,
            'target_platform_count': platform_count,
            'target_capsule_present': capsule_present,
            'extra_capsules_present': extra_capsules_present,
            'functions_owner_acl_exact': True,
        }
        _phase(report_path, report, 'PREDECESSOR_VERIFIED')

        with control.cursor() as cur:
            cur.execute(
                sql.SQL('alter database {} with allow_connections true').format(
                    sql.Identifier(database)
                )
            )
        if not _scalar(control, 'select datallowconn from pg_database where datname=%s', (database,)):
            raise MaintenanceRollbackError('Database admission did not reopen after verified commit')
        report['admission_reopened'] = True
        report['status'] = 'PASS'
        _phase(report_path, report, 'ADMISSION_REOPENED')
        return report
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error_code'] = _public_failure_code(exc)
        report['error_type'] = type(exc).__name__
        # Fail closed: do not reopen admission here. The structured state and
        # exact database flag remain available for explicit recovery.
        if control is not None and report['admission_closed']:
            try:
                report['admission_still_closed'] = not bool(_scalar(
                    control,
                    'select datallowconn from pg_database where datname=%s',
                    (database,),
                ))
            except Exception:
                report['admission_observation_error_code'] = (
                    'ADMISSION_STATE_OBSERVATION_FAILED'
                )
        _phase(report_path, report, 'FAILED_CLOSED')
        raise
    finally:
        if control is not None and lock_held:
            try:
                _scalar(
                    control,
                    "select pg_advisory_unlock(hashtextextended('CP6_PREUSE_ROLLBACK_MAINTENANCE',0))",
                )
            except Exception:
                pass
        if rollback_conn is not None:
            rollback_conn.close()
        if control is not None:
            control.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=tuple(TARGETS), required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--drain-timeout', type=float, default=10.0)
    parser.add_argument('--natural-grace', type=float, default=1.0)
    parser.add_argument('--no-terminate', action='store_true')
    parser.add_argument('--pause-after-close-file', type=Path)
    parser.add_argument('--continue-file', type=Path)
    args = parser.parse_args()
    target_pgurl = (
        os.environ.get('CP6_ROLLBACK_TARGET_PGURL')
        or os.environ.get('CP6_ROLLBACK_RACE_PGURL', '')
    )
    maintenance_pgurl = os.environ.get('CP6_ADMISSION_CONTROL_PGURL', '')
    if not target_pgurl or not maintenance_pgurl:
        raise SystemExit(
            'CP6_ROLLBACK_TARGET_PGURL (or CP6_ROLLBACK_RACE_PGURL) '
            'and CP6_ADMISSION_CONTROL_PGURL are required'
        )
    try:
        run_maintenance_rollback(
            target_name=args.target,
            target_pgurl=target_pgurl,
            maintenance_pgurl=maintenance_pgurl,
            report_path=args.report,
            drain_timeout=args.drain_timeout,
            natural_grace=args.natural_grace,
            terminate_after_grace=not args.no_terminate,
            pause_after_close_file=args.pause_after_close_file,
            continue_file=args.continue_file,
        )
    except Exception as exc:
        print(json.dumps({
            'status': 'FAIL',
            'error_code': _public_failure_code(exc),
            'error_type': type(exc).__name__,
        }, sort_keys=True))
        raise SystemExit(1) from exc
    print(json.dumps({'status': 'PASS', 'target': args.target}, sort_keys=True))


if __name__ == '__main__':
    main()
