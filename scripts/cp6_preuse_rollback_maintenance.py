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
}


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
        'trusted_predecessor_identity_count': len(TRUSTED_FUNCTIONS[target_name]),
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
        if (marker_count, predecessor_count, platform_count, capsule_present) != (0, 1, 0, False):
            raise MaintenanceRollbackError('Exact predecessor marker/capsule postcondition failed')
        report['restored_functions'] = _function_snapshot(rollback_conn, capsule)
        report['postconditions'] = {
            'target_marker_count': marker_count,
            'predecessor_marker_count': predecessor_count,
            'target_platform_count': platform_count,
            'target_capsule_present': capsule_present,
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
