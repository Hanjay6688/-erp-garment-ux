"""Install the precise read projection beside the retained booked quote."""

from hashlib import sha256
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
FUNCTION = 'cp7_sku_conversion.pool_values_v6(uuid,uuid,text)'
PREVIEW = 'cp7_sku_conversion.preview_v1(jsonb)'
POSITION = 'cp7_sku_conversion.position_value_v2(uuid,uuid,text,numeric)'
BASELINE_ROWS = {
    PREVIEW: 'a8a8dcffe5342ea77d8dbe1144f19c337d26fe0873fd850f0f5dc5ee67672d76',
    POSITION: 'faa5abd52dbb87cab1b9d3c5f4e4c938a7cc7e480bab7db2e310162d45e2e1f7',
}
ROUTES = {
    PREVIEW: (
        ('source_pool jsonb;target_pool jsonb;', 'source_pool jsonb;target_pool jsonb;source_values jsonb;source_booked jsonb;'),
        ("source_pool:=cp7_sku_conversion.pool_quote_v2(src.id,loc.id,'GRADE_A');"
         "target_pool:=cp7_sku_conversion.pool_quote_v2(dst.id,loc.id,'GRADE_A');",
         "money:=erp.has_permission('finance.hpp.view');\n"
         " if money then\n"
         "  source_values:=cp7_sku_conversion.pool_values_v6(src.id,loc.id,'GRADE_A');\n"
         "  source_booked:=source_values->'booked';source_pool:=source_values->'economic';\n"
         "  target_pool:=cp7_sku_conversion.pool_values_v6(dst.id,loc.id,'GRADE_A')->'economic';\n"
         " else\n"
         "  source_booked:=cp7_sku_conversion.pool_quote_v2(src.id,loc.id,'GRADE_A');source_pool:=source_booked;\n"
         "  target_pool:=cp7_sku_conversion.pool_quote_v2(dst.id,loc.id,'GRADE_A');\n"
         " end if;"),
        ("need:=qty;money:=erp.has_permission('finance.hpp.view');", "need:=qty;"),
        ("round(qty*(source_pool->>'average')::numeric,2)::text",
         "round(qty*(source_booked->>'average')::numeric,2)::text"),
    ),
    POSITION: (("q:=cp7_sku_conversion.pool_quote_v2(p_product,p_location,p_grade);",
                "q:=cp7_sku_conversion.pool_values_v6(p_product,p_location,p_grade)->'economic';"),),
}


def pin(value):
    return dict(bytes=len(value.encode()), sha256=sha256(value.encode()).hexdigest())


def require_original(signature, row):
    encoded = json.dumps(row, ensure_ascii=False, separators=(',', ':'))
    if len(row) != 19 or pin(encoded)['sha256'] != BASELINE_ROWS[signature]:
        raise ValueError('SKU_ECONOMIC_POOL_EXACT_FUNCTION_REQUIRED:' + signature)


def restore(signature, postimage):
    if len(postimage) != 19:
        raise ValueError('SKU_ECONOMIC_POOL_COMPLETE_FUNCTION_REQUIRED:' + signature)
    inverse = postimage[0]
    for before, after in reversed(ROUTES[signature]):
        if inverse.count(after) != 1:
            raise ValueError('SKU_ECONOMIC_POOL_EXACT_INVERSE_ROUTE_REQUIRED:' + signature)
        inverse = inverse.replace(after, before, 1)
    original = [inverse, *postimage[1:]]
    require_original(signature, original)
    return original


def project(signature, original):
    require_original(signature, original)
    postimage = original[0]
    for before, after in ROUTES[signature]:
        if postimage.count(before) != 1:
            raise ValueError('SKU_ECONOMIC_POOL_EXACT_READ_ROUTE_REQUIRED:' + signature)
        postimage = postimage.replace(before, after, 1)
    changed = [postimage, *original[1:]]
    if restore(signature, changed) != original:
        raise ValueError('SKU_ECONOMIC_POOL_COMPLETE_PREIMAGE_REQUIRED:' + signature)
    return changed


def helper_source():
    return (HERE / 'economic_pool.sql').read_text(encoding='utf-8')


def helper_row():
    definition, delimiter, _ = helper_source().partition('\n$function$;\n')
    if not delimiter or not definition.startswith('CREATE FUNCTION '):
        raise ValueError('SKU_ECONOMIC_POOL_NORMALIZED_HELPER_REQUIRED')
    definition = 'CREATE OR REPLACE FUNCTION ' + definition.removeprefix('CREATE FUNCTION ') + '\n$function$\n'
    return [definition, 'postgres', 'plpgsql', 'f', False, False, False, False,
            's', 'u', '100', '0', ['search_path=""'], ['p_product', 'p_location', 'p_grade'],
            None, 'p_product uuid, p_location uuid, p_grade text', 'jsonb', '-',
            [['postgres', 'postgres', 'EXECUTE', False]]]


def adapt(before, product, profile):
    if profile['derived_ddl'] != pin(product['ddl']) or profile['source_files'] != product['source_files']:
        raise ValueError('SKU_ECONOMIC_POOL_EXACT_INSTALL_PROFILE_REQUIRED')
    additions = dict(profile['groups']['functions'])
    predecessor = before['functions']
    if FUNCTION in additions or FUNCTION in predecessor:
        raise ValueError('SKU_ECONOMIC_POOL_NEW_PRIVATE_FUNCTION_REQUIRED')
    additions[FUNCTION] = helper_row()
    definitions = dict(product['definitions'])
    originals = dict(profile['replacement_before'])
    replacements = dict(profile['replacement_functions'])
    for signature in ROUTES:
        original = predecessor[signature]
        if signature in replacements:
            if originals[signature] != original:
                raise ValueError('SKU_ECONOMIC_POOL_EXACT_PREDECESSOR_REQUIRED:' + signature)
            current = replacements[signature]
        else:
            current = original
        replacement = project(signature, current)
        definitions[signature] = replacement[0]
        originals[signature] = original
        replacements[signature] = replacement
    ddl = product['ddl'] + '\n' + helper_source()
    product = dict(product, ddl=ddl, definitions=definitions)
    profile = dict(profile, derived_ddl=pin(ddl), replacement_before=originals,
                   derived_replacements={sig: pin(body) for sig, body in definitions.items()},
                   replacement_functions=replacements, groups=dict(profile['groups'], functions=additions))
    return product, profile


def bind(prepare):
    def prepared(before, prior):
        product, profile, tables = prepare(before, prior)
        product, profile = adapt(before, product, profile)
        return product, profile, tables
    return prepared
