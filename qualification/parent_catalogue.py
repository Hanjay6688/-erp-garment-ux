"""Compare a reviewed SKU catalogue with the actual disposable Global parent."""
from hashlib import sha256
import json
import re


CENSUS = "cp7_credit.assert_source_native_trigger_census_v1()"
CONTRACT = "cp7.global-parent-trigger-census-equivalence.v1"
LITERAL = re.compile(
    r"(?<=\n if actual_sha256 is distinct from ')[0-9a-f]{64}"
    r"(?='then\n  raise exception 'CP7_CREDIT_SOURCE_NATIVE_TRIGGER_CENSUS_CHANGED';end if;)"
)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def group_pin(value):
    return pin(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def comparable(value):
    if len(value) != 25:
        raise ValueError("GLOBAL_COMPLETE_ACTUAL_PARENT_CATALOGUE_REQUIRED")
    rows = [row for name, row in value["functions"] if name == CENSUS]
    if len(rows) != 1:
        raise ValueError("GLOBAL_EXACT_PARENT_CENSUS_ROUTINE_REQUIRED")
    row, = rows
    if (len(row) != 19 or row[1:3] != ["postgres", "plpgsql"] or row[4] is not True
            or row[8] != "v" or row[12] != ['search_path=""', "TimeZone=UTC"]
            or row[18] != [["postgres", "postgres", "EXECUTE", False]]):
        raise ValueError("GLOBAL_EXACT_PARENT_CENSUS_AUTHORITY_REQUIRED")
    literals = LITERAL.findall(row[0])
    if len(literals) != 1 or literals[0] == "0" * 64:
        raise ValueError("GLOBAL_EXACT_PARENT_CENSUS_LITERAL_REQUIRED")
    comparable_row = [LITERAL.sub("0" * 64, row[0]), *row[1:]]
    normalized = dict(value, functions=[
        [name, comparable_row if name == CENSUS else entry] for name, entry in value["functions"]
    ])
    return dict(groups={name: group_pin(entries) for name, entries in normalized.items()},
                guard=group_pin(comparable_row)), literals[0], row[0]


def reviewed_fields(raw, original):
    """Derive comparison fields from the byte-verified archived catalogue."""
    if pin(raw) != {name: original[name] for name in ("bytes", "sha256")}:
        raise ValueError("GLOBAL_EXACT_SKU_CATALOGUE_ORIGINAL_REQUIRED")
    profile, literal, _ = comparable(json.loads(raw))
    return dict(contract=CONTRACT, original=pin(raw), archived_census_sha256=literal, **profile)


def verify(cur, value, inputs, fingerprint):
    """Bind the raw catalogue and verify the installed guard inside the owning transaction."""
    live = fingerprint(cur, value)
    archived = inputs.get("parent_catalogue_fingerprint")
    reviewed = inputs.get("parent_catalogue_equivalence")
    if reviewed is None:
        if live != archived:
            raise ValueError("GLOBAL_EXACT_CURRENT_PARENT_AND_REVIEWED_MODULE_REQUIRED")
        return dict(status="GLOBAL_EXACT_RAW_PARENT_CATALOGUE", live_fingerprint=live)
    if (not isinstance(archived, dict) or reviewed["contract"] != CONTRACT
            or live["contract"] != archived["contract"] or live["counts"] != archived["counts"]
            or live["groups"] != 25 or archived["groups"] != 25):
        raise ValueError("GLOBAL_EXACT_REVIEWED_PARENT_PROFILE_REQUIRED")
    profile, literal, definition = comparable(value)
    if profile != {name: reviewed[name] for name in ("groups", "guard")}:
        raise ValueError("GLOBAL_CURRENT_PARENT_CATALOGUE_OUTSIDE_REVIEWED_SCOPE")
    if cur.execute("select pg_get_functiondef(%s::regprocedure)", (CENSUS,)).fetchone() != (definition,):
        raise ValueError("GLOBAL_CAPTURED_PARENT_CENSUS_DEFINITION_CHANGED")
    cur.execute("select cp7_credit.assert_source_native_trigger_census_v1()").fetchone()
    return dict(status="GLOBAL_ACTUAL_PARENT_CATALOGUE_AND_CENSUS_VERIFIED", live_fingerprint=live,
                sku_catalogue=reviewed["original"], installed_census_sha256=literal,
                archived_census_sha256=reviewed["archived_census_sha256"], normalized=profile)
