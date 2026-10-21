"""Exact additive overlays of frozen OW04 helpers; no Native body/DB calls.

Run outside the product. The generated SQL guards installed prosrc+metadata
against these frozen predecessors before changing any helper. Root must still
verify the accepted Native captures/private copy and compose atomically.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import json
import re

HERE = Path(__file__).resolve().parent
BASE = Path(os.environ.get('ERP_REPO', Path(__file__).resolve().parents[3])) / 'scripts/cp7_customer_credit'
PINS = {
    "coordinator/01_coordinator_facts.sql": "4741483e2a61056a6e2365cfcc43e65d83c4ab9d1c8fd6fa77d33eda26b7af99",
    "coordinator/03_native_initial_callbacks.sql": "b462af8229a8d1cdfc0bda414a555e69108be5961f72af23b214a58ff58a0843",
    "coordinator/04_register_and_materialize.sql": "abf523b1ba7a9e2d9f1aa8825b1e2c74cec160d2be726db71e2f2f8176ad7ff0",
    "coordinator/05_factual_profile.sql": "a11a072b8e0fffbea380063787e752814893089ef9066bcc541b5984221bb16d",
    "coordinator/06_finish_and_closed_routes.sql": "0dc8fb0f81e5a1787fe29e5a0585b8ca8138915dbb79f536d76051eb9c3ae27e",
    "source/member-proof.sql": "565e4e8643323442eadad2d6d1e65fdf1750da1675a2c68cc28187add17c1205",
    "ledger/02_uuid_poster.proposal.sql": "7ab2fc6f5cb700c2284e58921bd6e59fbe731a0064457f5031116d61aa30baf8"
}

def digest(s: str) -> str:
    return sha256(s.encode()).hexdigest()

def extract(source: str, name: str) -> tuple[str, str]:
    matches = list(re.finditer(r"create (?:or replace )?function " + re.escape(name) + r"\([^$]*?as \$\$([\s\S]*?)\$\$;", source))
    if len(matches) != 1:
        raise ValueError("NATIVE_EMPTY_FUNCTION_CAPTURE_NOT_UNIQUE: " + name)
    return matches[0].group(0), matches[0].group(1)

def prefix(body: str, text: str) -> str:
    # Exactly the outer block. A declaration may contain a CASE, never a BEGIN.
    match = re.search(r"\nbegin\n", body)
    if match is None:
        raise ValueError("NATIVE_EMPTY_OUTER_BEGIN_CHANGED")
    return body[:match.end()] + text + "\n" + body[match.end():]

def build() -> tuple[str, dict]:
    files = {}
    for path, pin in PINS.items():
        value = (BASE / path).read_text()
        if digest(value) != pin:
            raise ValueError("NATIVE_EMPTY_FROZEN_PREDECESSOR_CHANGED: " + path)
        files[path] = value
    targets = [
        ("coordinator/01_coordinator_facts.sql", "cp7_credit.is_unchanged_native_return_v1", "uuid", None),
        ("coordinator/03_native_initial_callbacks.sql", "cp7_credit.native_return_enter", "uuid",
         " if cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_enter_v1(p_return);return;end if;"),
        ("coordinator/03_native_initial_callbacks.sql", "cp7_credit.native_return_guard", "uuid,numeric,numeric,numeric",
         " if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_guard_v1(p_return,p_refund,p_net_after,p_raw_paid);end if;"),
        ("coordinator/03_native_initial_callbacks.sql", "cp7_credit.post_return_journal", "text,uuid,date,text,jsonb",
         " if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_post_return_journal_v1(p_type,p_return,p_economic,p_description,p_lines);end if;"),
        ("coordinator/04_register_and_materialize.sql", "cp7_credit.native_return_complete", "uuid,numeric,numeric",
         " if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_complete_v1(p_return,p_refund,p_net_after);end if;"),
        ("coordinator/06_finish_and_closed_routes.sql", "cp7_credit.native_return_leave", "uuid",
         " if cp7_credit.native_empty_owns_return_v1(p_return)then perform cp7_credit.native_empty_leave_v1(p_return);return;end if;"),
        ("ledger/02_uuid_poster.proposal.sql", "cp7_credit.assert_bound_post", "text,uuid,date,jsonb",
         " if cp7_credit.native_empty_post_scope_v1()then perform cp7_credit.assert_native_empty_bound_post_v1(p_type,p_source,p_economic,p_lines);return;end if;"),
        ("coordinator/03_native_initial_callbacks.sql", "cp7_credit.bound_book_date", "text,uuid,date,jsonb",
         " if cp7_credit.native_empty_post_scope_v1()then return cp7_credit.native_empty_bound_book_v1(p_type,p_source,p_economic,p_lines);end if;"),
        ("ledger/02_uuid_poster.proposal.sql", "cp7_credit.bound_audit_context", "",
         " if cp7_credit.native_empty_post_scope_v1()then return cp7_credit.native_empty_bound_audit_v1();end if;"),
        ("source/member-proof.sql", "ow04_source_proposal.verify_return_member_v1", "uuid",
         " if exists(select 1 from cp7_credit.native_empty_operations where source_return_id=p_return)then return cp7_credit.verify_native_empty_member_v1(p_return);end if;"),
        ("coordinator/05_factual_profile.sql", "cp7_credit.assert_financial_materialization_provenance", "jsonb",
         " perform cp7_credit.assert_native_empty_provenance_v1(p_actual);\n p_actual:=cp7_credit.without_native_empty_markers_v1(p_actual);"),
        ("coordinator/06_finish_and_closed_routes.sql", "cp7_credit.enforce_initial_return_closure_v1", "",
         " operation:=cp7_credit.native_empty_closure_id_v1(tg_table_name,to_jsonb(new));\n if operation is not null then perform cp7_credit.assert_native_empty_closed_v1(operation);return null;end if;"),
        ("coordinator/06_finish_and_closed_routes.sql", "cp7_credit.native_source_enter", "text,uuid",
         " if cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_source_enter_v1(p_action,p_source);return;end if;"),
        ("coordinator/06_finish_and_closed_routes.sql", "cp7_credit.native_source_complete", "text,uuid",
         " if exists(select 1 from cp7_credit.native_empty_source_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())\n  or cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_source_complete_v1(p_action,p_source);return;end if;")
    ]
    guards, definitions, manifest = [], [], []
    for source, name, args, add in targets:
        original, body = extract(files[source], name)
        if add is None:
            changed = "\nbegin\n -- No unregistered Native bypass remains after the technical operation is installed.\n return false;\nend "
        else:
            changed = prefix(body, add)
        derived = original.replace(body, changed, 1)
        derived = re.sub(r"^create (?:or replace )?function ", "create or replace function ", derived)
        identity = f"{name}({args})"
        volatility = "s" if re.search(r"\bstable\b", original.split("as $$")[0]) else "v"
        guards.append(f""" if not exists(select 1 from pg_proc p where p.oid='{identity}'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='{digest(body)}'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='{volatility}'
  and p.proconfig@>array['search_path=\"\"','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: {identity}';end if;""")
        definitions.append(derived)
        manifest.append({"identity": identity, "source": source, "source_sha256": PINS[source],
                         "before_body_sha256": digest(body), "after_body_sha256": digest(changed),
                         "overlay_definition_sha256": digest(derived), "owner": "postgres", "security_definer": True,
                         "volatility": volatility, "required_config": ['search_path=""', 'TimeZone=UTC'],
                         "acl": "unchanged by CREATE OR REPLACE; no outsider EXEC before or after"})
    sql = """-- Generated exact additive helper overlays. No Native body or role grant changes.
do $not_an_installer$begin raise exception 'OW04_NATIVE_EMPTY_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;
do $frozen_predecessors$begin
""" + "\n".join(guards) + "\nend $frozen_predecessors$;\n\n" + "\n\n".join(definitions) + "\n"
    return sql, {"classification": "EXACT_FROZEN_HELPER_OVERLAYS_NOT_NATIVE_CAPTURE_OR_EXECUTION",
                 "native_execution_proven": False, "frozen_sources": PINS, "overlays": manifest,
                 "generated_sql_sha256": digest(sql)}

if __name__ == "__main__":
    sql, manifest = build()
    (HERE / "04_exact_overlays.sql").write_text(sql)
    (HERE / "OVERLAY_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"overlays":len(manifest['overlays']),"sql_sha256":digest(sql)}))
