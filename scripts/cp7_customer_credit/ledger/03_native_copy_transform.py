"""OW04 source-only transform proposal. NO DATABASE CALLS, NO INSTALLER.

Inputs must be exact pg_get_functiondef/prosrc + pg_proc metadata captured by the
complete accepted installer, compared with its APPROVED predecessor manifest.
Do not substitute a regex-extracted .sql file for that authoritative capture.
The command line only performs a static source-footprint check on repository
files. It never executes the emitted SQL, nor modifies the active repository.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re


POST_JOURNAL_IDENTITY = "erp.post_journal(text,uuid,date,text,jsonb)"
# 20ac accepted AFTER pg_get_functiondef digest, inventory line 68.
POST_JOURNAL_APPROVED_SHA256 = "1f4b630c00147f88d195b3b365114eaecc60fdf3141859c384056423ae39f824"
REVERSE_JOURNAL_IDENTITY = "erp.reverse_journal(uuid,text)"
# 20ap installed digest, confirmed by later 20as predecessor manifest.
REVERSE_JOURNAL_APPROVED_SHA256 = "9c3b04353530df3c22e601e59927321714a186cecb026f7b08ff76c0ebb7e396"
POST_RETURN_IDENTITY = "erp.post_sales_return(uuid)"

PROTECTED_SOURCES = (
    "CP7_CUSTOMER_CREDIT_RECOGNITION",
    "CP7_CUSTOMER_CREDIT_APPLY",
    "CP7_CUSTOMER_CREDIT_REFUND",
    "CP7_CUSTOMER_CREDIT_EVENT_REVERSE",
)


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def once(value: str, old: str, new: str, label: str) -> str:
    if value.count(old) != 1:
        raise ValueError(f"{label}: expected one exact anchor, got {value.count(old)}")
    return value.replace(old, new, 1)


@dataclass(frozen=True)
class Capture:
    identity: str
    definition: str
    body: str
    owner: str
    acl: tuple[str, ...]
    security_definer: bool
    volatility: str
    config: tuple[str, ...]


@dataclass(frozen=True)
class Approved:
    """Trusted build manifest, NOT computed from the candidate capture itself."""
    identity: str
    definition_sha256: str
    owner: str
    acl: tuple[str, ...]
    security_definer: bool
    volatility: str
    config: tuple[str, ...]


POST_APPROVED = Approved(
    POST_JOURNAL_IDENTITY, POST_JOURNAL_APPROVED_SHA256, "postgres",
    ("postgres=X/postgres", "service_role=X/postgres"), True, "v", ("search_path=erp, public",),
)
REVERSE_APPROVED = Approved(
    REVERSE_JOURNAL_IDENTITY, REVERSE_JOURNAL_APPROVED_SHA256, "postgres",
    ("postgres=X/postgres", "service_role=X/postgres"), True, "v", ("search_path=erp, public, pg_temp",),
)


def assert_capture(captured: Capture, approved: Approved) -> None:
    actual = (
        captured.identity, digest(captured.definition), captured.owner,
        tuple(sorted(captured.acl)), captured.security_definer,
        captured.volatility, captured.config,
    )
    expected = (
        approved.identity, approved.definition_sha256, approved.owner,
        tuple(sorted(approved.acl)), approved.security_definer,
        approved.volatility, approved.config,
    )
    if actual != expected:
        raise ValueError("OW04_NATIVE_PREDECESSOR_OR_METADATA_CHANGED")
    if captured.definition.count(captured.body) != 1:
        raise ValueError("OW04_NATIVE_CAPTURE_BODY_NOT_UNIQUE")


def replace_body(captured: Capture, new_body: str) -> str:
    return once(captured.definition, captured.body, new_body, "captured body")


def post_body(body: str) -> str:
    """Only admission, exact book-date assignment and truthful shift audit change."""
    changed = once(
        body,
        "  perform erp.require_internal();",
        "  perform cp7_credit.assert_bound_post(p_source_type,p_source_id,p_transaction_date,p_lines);\n"
        "  perform erp.require_internal();",
        "post admission",
    )
    changed = once(
        changed,
        "  v_gl_date:=erp.resolve_accounting_transaction_date(p_transaction_date);",
        "  v_gl_date:=cp7_credit.bound_book_date(p_source_type,p_source_id,p_transaction_date,p_lines);",
        "book assignment",
    )
    changed = once(
        changed,
        "jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id)",
        "(jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id)||cp7_credit.bound_audit_context())",
        "source-bound audit context",
    )
    changed = once(
        changed,
        "'Late/backdated posting moved to open accounting period'",
        "'OW04 derived book date: lawful open period and source-bound dated profile'",
        "shift audit reason",
    )
    # Four replacements preserve every balancing, source-unique, period-SHARE,
    # account mapping, actual INSERT, AP admission and daily-balance statement.
    for preserved in (
        "  perform 1 from erp.accounting_period_control where singleton_id=1 for share;",
        "    v_cent_lines:=v_cent_lines||jsonb_build_array(r||jsonb_build_object(",
        "  if v_debit<>v_credit or v_debit<=0 then",
        "  insert into erp.journal_entries(",
        "    insert into erp.journal_lines(",
        "  insert into erp.account_daily_balances(",
        "  v_ap_vendor_account:=erp.account_id('AP_VENDOR');",
    ):
        if body.count(preserved) != changed.count(preserved) or not body.count(preserved):
            raise ValueError("OW04_PRESERVED_NATIVE_STATEMENT_CHANGED: " + preserved)
    return changed


def derive_post_journal(captured: Capture, approved: Approved) -> tuple[str, dict]:
    if approved != POST_APPROVED:
        raise ValueError("OW04_UNAPPROVED_NATIVE_POST_JOURNAL_BASE")
    assert_capture(captured, approved)
    derived = replace_body(captured, post_body(captured.body))
    derived = once(
        derived, "FUNCTION erp.post_journal(",
        "FUNCTION cp7_credit._post_journal_bound(", "private header",
    )
    return derived, manifest(captured, derived, "cp7_credit._post_journal_bound(text,uuid,date,text,jsonb)")


def return_body(body: str) -> str:
    # Paid admission/effective-paid changes are separate, mandatory transforms.
    # This hook changes only the ONE actual return journal call. It never rewrites
    # original SALE/PAYMENT/RETURN journal dates or Native HPP/stock construction.
    return once(
        body, "erp.post_journal('SALES_RETURN',h.id,",
        "cp7_credit.post_return_journal('SALES_RETURN',h.id,", "return journal hook",
    )


def hook_post_return(captured: Capture, approved: Approved) -> tuple[str, dict]:
    if approved.identity != POST_RETURN_IDENTITY or approved.owner != "postgres":
        raise ValueError("OW04_UNAPPROVED_POST_RETURN_BASE")
    # approved.definition_sha256 MUST be the exact current accepted composed
    # Native definition (including late F03 changes) in the trusted build manifest.
    # Do NOT replace it with a broad list of historic hashes or the current digest.
    assert_capture(captured, approved)
    changed = replace_body(captured, return_body(captured.body))
    return changed, manifest(captured, changed, captured.identity)


def reverse_body(body: str) -> str:
    sources = ",".join("'" + s + "'" for s in PROTECTED_SOURCES)
    anchor = "  if v_source_type is null then raise exception 'Journal entry not found'; end if;"
    guard = (
        anchor + "\n  if v_source_type in(" + sources + ")or cp7_credit.is_protected_journal(p_journal_entry_id)then\n"
        "    raise exception 'CP7_CREDIT_JOURNAL_USE_OWNING_SOURCE_WORKFLOW';\n"
        "  end if;"
    )
    return once(body, anchor, guard, "generic reverse source protection")


def protect_reverse(captured: Capture, approved: Approved) -> tuple[str, dict]:
    if approved != REVERSE_APPROVED:
        raise ValueError("OW04_UNAPPROVED_NATIVE_REVERSE_BASE")
    assert_capture(captured, approved)
    changed = replace_body(captured, reverse_body(captured.body))
    return changed, manifest(captured, changed, captured.identity)


def manifest(captured: Capture, derived: str, target: str) -> dict:
    return {
        "source_identity": captured.identity,
        "source_definition_sha256": digest(captured.definition),
        "source_owner": captured.owner,
        "source_acl": sorted(captured.acl),
        "source_security_definer": captured.security_definer,
        "source_volatility": captured.volatility,
        "source_config": list(captured.config),
        "target_identity": target,
        "expected_target_definition_sha256": digest(derived),
        "target_owner": "postgres",
        "target_acl": ["postgres=X/postgres"] if target.startswith("cp7_credit.") else sorted(captured.acl),
        "target_security_definer": captured.security_definer,
        "target_volatility": captured.volatility,
        "target_config": list(captured.config),
        "native_execution_proven": False,
    }


CAPTURE_QUERY = """\
select p.oid::regprocedure::text as identity,pg_get_functiondef(p.oid)as definition,
 p.prosrc as body,pg_get_userbyid(p.proowner)as owner,
 coalesce((select array_agg(a::text order by a::text)from unnest(p.proacl)a),'{}'::text[])as acl,
 p.prosecdef as security_definer,p.provolatile::text as volatility,
 coalesce(p.proconfig,'{}'::text[])as config
from pg_proc p where p.oid=%s::regprocedure
"""


def extract_release_definition(source: str, name: str) -> tuple[str, str]:
    """STATIC FOOTPRINT ONLY; not pg_get_functiondef and not an install capture."""
    # 20ah embeds its definition in EXECUTE $definition$: its $function$ is
    # followed by the outer dollar quote rather than a function semicolon.
    pattern = rf"CREATE OR REPLACE FUNCTION erp\.{re.escape(name)}\([^\n]*\).*?\$function\$(.*?)\$function\$(?:;)?"
    matches = list(re.finditer(pattern, source, re.S))
    if len(matches) != 1:
        raise ValueError(f"static release {name}: expected exactly one definition")
    return matches[0].group(0), matches[0].group(1)


def static_check(repo: Path) -> dict:
    release = repo / "supabase/release/cp6-t3"
    specs = (
        ("20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql", "post_journal", post_body),
        ("20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.sql", "post_sales_return", return_body),
        ("20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql", "reverse_journal", reverse_body),
    )
    results = []
    for file, name, transform in specs:
        definition, body = extract_release_definition((release / file).read_text(), name)
        changed = transform(body)
        # Exact anchor mutation must fail, including a duplicated anchor.
        failed = False
        try:
            transform(body + body)
        except ValueError:
            failed = True
        assert failed, "duplicated source anchors were accepted"
        results.append({"file": str(release / file), "function": name,
            "raw_release_definition_sha256": digest(definition),
            "raw_release_body_sha256": digest(body),
            "transformed_body_sha256": digest(changed),
            "duplicate_anchor_rejected": failed})
    return {"scope": "STATIC_RELEASE_TRANSFORM_ONLY", "native_execution_proven": False,
        "not_an_installer": True, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-check", type=Path, required=True, metavar="REPO")
    args = parser.parse_args()
    print(json.dumps(static_check(args.static_check.resolve()), indent=2))
