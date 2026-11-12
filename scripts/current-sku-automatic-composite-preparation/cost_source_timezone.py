"""Canonicalize the private non-PO cost capture beside its UTC recheck."""

from hashlib import sha256

SIGNATURE = "cp7_sku_conversion.capture_cost_source_v3(uuid)"
DONOR = {"bytes": 8954, "sha256": "7a9ab4a887fe92b82eeb003989418b5ab4da57607fccefc365b2f2445bade765"}
OLD_DEFINITION = {"bytes": 1556, "sha256": "d34b88ae943c49c5061d1c2116e9fc337dfbada17a81fcc5f5933fbe8627a02c"}
NEW_DEFINITION = {"bytes": 1581, "sha256": "44aba20d060d3a7eed11f7118c3cffa9289ec9306511e9ed3fb15ea8eaa28ae2"}
INITIAL_DDL = (
    "create function cp7_sku_conversion.capture_cost_source_v3(p_document uuid)returns jsonb\n"
    "language plpgsql volatile security definer set search_path=''as $$"
)
DDL_BEFORE = INITIAL_DDL.replace("create function", "create or replace function", 1)
DDL_AFTER = DDL_BEFORE.replace("set search_path=''as", "set search_path='' set timezone='UTC' as")
MONEY_STATE = "'cost_money_state',cp7_sku_conversion.cost_document_money_state_v3(p_document)"
DEFINITION_BEFORE = " SET search_path TO ''\nAS $function$"
DEFINITION_AFTER = " SET search_path TO ''\n SET \"TimeZone\" TO 'UTC'\nAS $function$"


def pin(text):
    raw = text.encode()
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def replace_exact(value, before, after):
    if value.count(before) != 1 or after in value:
        raise ValueError("SKU_SOURCE_COST_TIMEZONE_EXACT_PREIMAGE_REQUIRED")
    return value.replace(before, after, 1)


def adapt(product, profile):
    ddl = product["ddl"]
    if (product["source_files"].get("source_rebalance.sql") != DONOR
            or profile["source_files"] != product["source_files"]
            or profile["derived_ddl"] != pin(ddl)):
        raise ValueError("SKU_SOURCE_COST_TIMEZONE_EXACT_FROZEN_DDL_REQUIRED")
    functions = dict(profile["groups"]["functions"])
    original = functions[SIGNATURE]
    if (len(original) != 19 or pin(original[0]) != OLD_DEFINITION
            or original[1] != "postgres" or original[4] is not True
            or original[12] != ['search_path=""']
            or original[18] != [["postgres", "postgres", "EXECUTE", False]]):
        raise ValueError("SKU_SOURCE_COST_TIMEZONE_EXACT_PRIVATE_PROFILE_REQUIRED")
    changed = list(original)
    changed[0] = replace_exact(original[0], DEFINITION_BEFORE, DEFINITION_AFTER)
    if pin(changed[0]) != NEW_DEFINITION:
        raise ValueError("SKU_SOURCE_COST_TIMEZONE_EXACT_REPLAY_POSTIMAGE_REQUIRED")
    changed[12] = original[12] + ["TimeZone=UTC"]
    functions[SIGNATURE] = changed
    initial, separator, final = ddl.partition(DDL_BEFORE)
    if (not separator or initial.count(INITIAL_DDL) != 1 or INITIAL_DDL in final
            or MONEY_STATE not in final.split("$$;", 1)[0]):
        raise ValueError("SKU_SOURCE_COST_TIMEZONE_FINAL_MONEY_CAPTURE_REQUIRED")
    # Money installs a replacement after the initial capture and its ACL.
    revised = replace_exact(ddl, DDL_BEFORE, DDL_AFTER)
    groups = dict(profile["groups"], functions=functions)
    return dict(product, ddl=revised), dict(profile, derived_ddl=pin(revised), groups=groups)


def bind(prepare):
    def prepared(before, prior):
        product, profile, tables = prepare(before, prior)
        product, profile = adapt(product, profile)
        return product, profile, tables
    return prepared
