"""Canonical timestamp proofs for the exact private rework/redye context."""

from hashlib import sha256

PRIOR_CONTEXT = {"bytes":13857,"sha256":"67141e2dcbf2c57082a2b6b415100a5583facdd81a43baab031bbe29a6355d5a"}
CURRENT_CONTEXT = {"bytes":13907,"sha256":"7627c3a71d6e546a9174dde9de6dd2babd4bae3a071661f6184bb633f80f9501"}
PRIOR_DDL = {"bytes":18268,"sha256":"80e1ec6ec0b7f0b19111d229c64413f70be7bd4fed157b3c5cbef67d96bcdd56"}
SEARCH_PATH = "set search_path=''as"
UTC_SEARCH_PATH = "set search_path='' set \"TimeZone\" to 'UTC' as"
NORMALIZED_BEFORE = " SET search_path TO ''\nAS $function$"
NORMALIZED_AFTER = " SET search_path TO ''\n SET \"TimeZone\" TO 'UTC'\nAS $function$"
REPAIRS = (
    ("cp7_sku_conversion.automatic_valid_v5()",
     "create function cp7_sku_conversion.automatic_valid_v5()returns boolean\nlanguage sql stable security definer set search_path=''as $$",
     "fe1afe2958c0582d3d858f7d567af3f1dc619cc97af92137527fe41665cab502",
     "c7366933a6bcf9b70859e28fd625fbe5988b28cb49f4c5febdeef4c8e3080db8"),
    ("cp7_sku_conversion.automatic_enter_v5(uuid,text,uuid)",
     "create function cp7_sku_conversion.automatic_enter_v5(p_rework uuid,p_phase text,p_conversion uuid)returns void\nlanguage plpgsql volatile security definer set search_path=''as $$",
     "114ea066e9db7ff770b733f65f8087fafe3703a18aa39089b84df564eebe8cdc",
     "37c945673bcb5fc3643d6bdaf0f7f9bae58c354bcc7f077ed78bff6fc29921a9"),
)


def pin(text):
    raw = text.encode()
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def replace_one(text, before, after, source):
    if text.count(before) != 1 or after in text:
        raise ValueError("SKU_AUTOMATIC_TIMEZONE_EXACT_PREIMAGE_REQUIRED:" + source)
    return text.replace(before, after, 1)


def repair_context(context):
    if pin(context) != PRIOR_CONTEXT:
        raise ValueError("SKU_AUTOMATIC_TIMEZONE_EXACT_CONTEXT_SOURCE_REQUIRED")
    for signature, before, _, _ in REPAIRS:
        # Edit the function settings inside the original header, including its
        # untouched dollar-quote delimiter in the result.
        after = replace_one(before, SEARCH_PATH, UTC_SEARCH_PATH, signature)
        context = replace_one(context, before, after, signature)
    if pin(context) != CURRENT_CONTEXT:
        raise ValueError("SKU_AUTOMATIC_TIMEZONE_EXACT_CONTEXT_POSTIMAGE_REQUIRED")
    return context


def adapt(product, profile):
    ddl = product["ddl"]
    if pin(ddl) != PRIOR_DDL or profile["derived_ddl"] != PRIOR_DDL:
        raise ValueError("SKU_AUTOMATIC_TIMEZONE_EXACT_FROZEN_DDL_REQUIRED")
    # The donor DDL ends with the full frozen context file.
    raw = ddl.encode()
    cut = len(raw) - PRIOR_CONTEXT["bytes"]
    amended = raw[:cut].decode() + repair_context(raw[cut:].decode())
    functions = dict(profile["groups"]["functions"])
    for signature, _, prior, current in REPAIRS:
        original = functions[signature]
        if (len(original) != 19 or pin(original[0])["sha256"] != prior
                or original[1] != "postgres" or original[4] is not True
                or original[12] != ['search_path=""']
                or original[18] != [["postgres", "postgres", "EXECUTE", False]]):
            raise ValueError("SKU_AUTOMATIC_TIMEZONE_EXACT_FUNCTION_PROFILE_REQUIRED:" + signature)
        changed = list(original)
        changed[0] = replace_one(original[0], NORMALIZED_BEFORE, NORMALIZED_AFTER, signature)
        if pin(changed[0])["sha256"] != current:
            raise ValueError("SKU_AUTOMATIC_TIMEZONE_EXACT_REPLAY_POSTIMAGE_REQUIRED:" + signature)
        changed[12] = original[12] + ["TimeZone=UTC"]
        functions[signature] = changed
    groups = dict(profile["groups"], functions=functions)
    return dict(product, ddl=amended), dict(profile, derived_ddl=pin(amended), groups=groups)


def bind(prepare):
    def prepared(before, prior):
        product, profile, tables = prepare(before, prior)
        product, profile = adapt(product, profile)
        return product, profile, tables
    return prepared
