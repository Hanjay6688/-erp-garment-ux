"""Exact predecessor admission and retained guard checks; no Native credit."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('moving_credit_delta',HERE/'credit_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
raw=(Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json').read_bytes()
assert sha256(raw).hexdigest()=='5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f'
functions=json.loads(raw)['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4']['Native_to_copy_handoff']['raw_current_catalog']['functions']
originals={s:functions[s][0]for s in delta.SIGNATURES}
changed=delta.patched(originals)
for sig in delta.SIGNATURES:
    bad=dict(originals);bad[sig]+='\n'
    try:delta.patched(bad)
    except ValueError as e:assert str(e)=='SKU_MOVAVG_CREDIT_PREDECESSOR_CHANGED:'+sig
    else:raise AssertionError('ALTERED_PREDECESSOR_ADMITTED')
    assert changed[sig]!=originals[sig] and changed[sig].endswith('$function$\n')
projection=changed['cp7_credit.initial_hpp_projection_v1(jsonb)']
# Every old semantic refusal survives, rather than asserting a lower count.
import re
assert re.findall("raise exception '([^']+)'",projection)==re.findall("raise exception '([^']+)'",originals['cp7_credit.initial_hpp_projection_v1(jsonb)'])
assert "before_target is distinct from to_jsonb(t)"in projection
assert 'component_plan is distinct from fresh_component_plan'in projection
assert projection.index('into component_plan')<projection.index('order by id for update')
assert projection.index('into fresh_component_plan')>projection.index('order by id for update')
target=changed['cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)']
assert 'erp.compute_'not in target
assert 'return_components_v2'in target and 'net_sold_entries'in target
assert "'lots',(select coalesce(jsonb_agg(to_jsonb(f)order by f.lot_id),'[]')from facts f)"in target
assert 'hpp_scope_lot_ids_v2'in changed['cp7_credit.initial_hpp_support_v1(uuid,uuid)']
assert 'hpp_scope_lot_ids_v2'in changed['cp7_credit.initial_opening_hpp_source_v1(uuid,uuid)']
print(json.dumps(dict(status='SKU_CREDIT_FOUR_EXACT_PREDECESSORS_AND_ALL_OLD_REFUSALS_RETAINED',
    changed_functions=4,altered_predecessor_refusals=4,actual_Native_cases=0,production_go=False)))
