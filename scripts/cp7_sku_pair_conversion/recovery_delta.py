"""Two exact Native captures; managed-only preflight, no costing rewrite."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIGNATURES = ('erp.bc_value_custody_v1(jsonb,uuid)',
              'erp.save_accessory_service_action_v1(text,jsonb,uuid)')
GUARD = "  perform cp7_sku_conversion.recovery_preflight_v1(l.id,v_qty,v_unit,v_at);\n"
AUTH = "  if v_action='VALUE_CUSTODY' then perform cp7_sku_conversion.recovery_auth_v1(p_payload);end if;\n"


def profile():
    value = json.loads((HERE / 'recovery_profile.json').read_bytes())
    if (value['contract'] != 'cp7.sku-managed-recovery-native-profile.v1'
            or set(value['captures']) != set(SIGNATURES)
            or value['new_Native_capture_count'] != 2):
        raise ValueError('SKU_RECOVERY_EXACT_TWO_CURRENT_NATIVE_CAPTURES_REQUIRED')
    return value


def validate(catalog):
    """Physical qualified catalogue only, before any new installation DDL."""
    value = profile()
    for sig, pin in value['captures'].items():
        raw = (HERE / pin['path']).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('SKU_RECOVERY_CURRENT_NATIVE_ORIGINAL_CHANGED:' + sig)
        actual = catalog['functions'].get(sig)
        if actual is None or actual[0].encode() != raw or actual[1:] != pin['metadata']:
            raise ValueError('SKU_RECOVERY_NATIVE_DEFINITION_OWNER_ACL_CHANGED:' + sig)
    for sig, digest in value['unchanged_native_function_abi'].items():
        if sha256(catalog['functions'][sig][0].encode()).hexdigest() != digest:
            raise ValueError('SKU_RECOVERY_NATIVE_COST_PROFILE_CHANGED:' + sig)
    for column, expected in value['hpp_columns'].items():
        if catalog['columns'].get(column) != expected:
            raise ValueError('SKU_RECOVERY_NATIVE_HPP_STORAGE_CHANGED:' + column)
    if catalog['relations']['erp.v_current_hpp'][9] != value['current_hpp_view_definition']:
        raise ValueError('SKU_RECOVERY_NATIVE_CURRENT_HPP_VIEW_CHANGED')


def once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError('SKU_RECOVERY_EXACT_NATIVE_ANCHOR_REQUIRED:' + label)
    return text.replace(old, new, 1)


def patched(originals):
    value = profile()
    if set(originals) != set(SIGNATURES):
        raise ValueError('SKU_RECOVERY_EXACT_TWO_CURRENT_NATIVE_CAPTURES_REQUIRED')
    for sig, text in originals.items():
        if sha256(text.encode()).hexdigest() != value['captures'][sig]['sha256']:
            raise ValueError('SKU_RECOVERY_CURRENT_NATIVE_BODY_CHANGED:' + sig)
    sig = SIGNATURES[0]
    anchor = "  perform erp.bc_new_document_v1(p_request,'VALUE_CUSTODY',v_at,p_payload,jsonb_build_object('ACC_DEC03',erp.bc_policy_version_v1('ACC_DEC03')));"
    guarded = once(originals[sig], anchor, GUARD + anchor, 'before first custody document')
    if guarded.replace(GUARD, '', 1) != originals[sig]:
        raise ValueError('SKU_RECOVERY_NATIVE_VALUATION_DERIVATION_NOT_REVERSIBLE')
    result = {sig: guarded}
    sig = SIGNATURES[1]
    before = "  v_cached:=erp._idempotency_begin('save_accessory_service_action_v1',p_client_request_id,"
    after = "    erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));"
    guarded = once(originals[sig], before, AUTH + before, 'managed authority before request wait')
    guarded = once(guarded, after, after + '\n' + AUTH.rstrip('\n'), 'managed authority after request wait before cache')
    if guarded.replace(AUTH, '', 1).replace('\n' + AUTH.rstrip('\n'), '', 1) != originals[sig]:
        raise ValueError('SKU_RECOVERY_NATIVE_SERVICE_DERIVATION_NOT_REVERSIBLE')
    result[sig] = guarded
    return result
