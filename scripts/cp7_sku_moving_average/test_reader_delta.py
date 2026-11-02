from pathlib import Path
import importlib.util,json,os

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('moving_average_reader_delta',HERE/'reader_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
parent=Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
raw=json.loads(parent.read_bytes())
functions=raw['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'][
    'Native_to_copy_handoff']['raw_current_catalog']['functions']
originals={sig:functions[sig][0]for sig in delta.SIGNATURES}
patched=delta.patched(originals)
assert 'position_value_v2(x.product_id,x.location_id,x.quality_grade,x.physical_qty)'in patched[delta.SIGNATURES[0]]
assert 'position_value_v2(pid,location,grade,1)'in patched[delta.SIGNATURES[1]]
assert patched[delta.SIGNATURES[0]].count('cp7_fg.positions(q,zero)')==originals[delta.SIGNATURES[0]].count('cp7_fg.positions(q,zero)')
assert 'CURRENT_RESTATED_MOVEMENT_SNAPSHOT'in patched[delta.SIGNATURES[1]]
print({'status':'SKU_MOVAVG_FG_READER_TWO_EXACT_SUBSTITUTIONS','actual_sql':0,'production_go':False})
