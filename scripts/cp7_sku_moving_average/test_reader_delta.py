from pathlib import Path
import importlib.util,json,zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('moving_average_reader_delta',HERE/'reader_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
archive=HERE.parents[2]/'evidence'/'DE_6E615_SUCCESS_FULL_CANONICAL.zip'
with zipfile.ZipFile(archive)as z:
    raw=json.loads(z.read('DE_GLOBAL_BEFORE_NATIVE30/CALLER_RAW_BOUNDARY_OBSERVATION.json'))
originals={sig:raw['before']['actual_all22']['functions'][sig][0]for sig in delta.SIGNATURES}
patched=delta.patched(originals)
assert 'position_value_v2(x.product_id,x.location_id,x.quality_grade,x.physical_qty)'in patched[delta.SIGNATURES[0]]
assert 'position_value_v2(pid,location,grade,1)'in patched[delta.SIGNATURES[1]]
assert patched[delta.SIGNATURES[0]].count('cp7_fg.positions(q,zero)')==originals[delta.SIGNATURES[0]].count('cp7_fg.positions(q,zero)')
assert 'CURRENT_RESTATED_MOVEMENT_SNAPSHOT'in patched[delta.SIGNATURES[1]]
print({'status':'SKU_MOVAVG_FG_READER_TWO_EXACT_SUBSTITUTIONS','actual_sql':0,'production_go':False})
