"""Original committed E witness; one raw-observation retention derivation."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import ast,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD="""            if catalog._catalog_rows(cur) != before_catalog or catalog._data(cur) != before_data:
                raise AssertionError('E1_USED_INVERSE_REFUSAL_CHANGED_CATALOG_DATA_OR_SEQUENCES')"""
NEW="""            after_catalog,after_data = catalog._catalog_rows(cur),catalog._data(cur)
            if after_catalog != before_catalog or after_data != before_data:
                raise AssertionError('E1_USED_INVERSE_REFUSAL_CHANGED_CATALOG_DATA_OR_SEQUENCES')
            result['before'] = dict(actual_all22=before_catalog,full_data_and_sequences=before_data)
            result['after'] = dict(actual_all22=after_catalog,full_data_and_sequences=after_data)"""


def prepared_sources():
    value=json.loads((HERE/'WITNESS_ORIGIN.json').read_bytes())
    if(value['source_head']!='928246e5f62637c7c6457e57d73d0699196e3408'
       or value['source_path']!='scripts/current-credit-e1-native-qualification/component.py'):
        raise ValueError('COMPLETE_DE_EXACT_COMMITTED_WITNESS_ORIGIN_REQUIRED')
    raw=(ROOT/value['retained_path']).read_bytes();pin=value['original']
    original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
        value['source_head']+':'+value['source_path']],env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0'))
    if raw!=original or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
        raise ValueError('COMPLETE_DE_UNCHANGED_E17_COMMITTED_WITNESS_REQUIRED')
    functions=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)
        and n.name in('require_local','committed_witness')]
    if [n.name for n in functions]!=['require_local','committed_witness']:
        raise ValueError('COMPLETE_DE_EXACT_TWO_WITNESS_FUNCTIONS_REQUIRED')
    source='\n\n'.join(ast.get_source_segment(raw.decode(),n)for n in functions)+'\n'
    if source.count(OLD)!=1 or NEW in source:raise ValueError('COMPLETE_DE_RAW_WITNESS_EXACT_ANCHOR_REQUIRED')
    derived=source.replace(OLD,NEW,1)
    if derived.replace(NEW,OLD,1)!=source:raise ValueError('COMPLETE_DE_ORIGINAL_WITNESS_NOT_RECOVERED')
    # Only retain the same already checked raw observations. All monetary,
    # stock/HPP/date/history/consumer and financial-truth statements survive.
    compile(derived,str(HERE/'actual_committed_E_witness.py'),'exec')
    return derived,dict(original_component=dict(pin),selected_function_count=2,counted_changes=1,
        original_function_sha256=sha256(source.encode()).hexdigest(),derived_sha256=sha256(derived.encode()).hexdigest(),
        complete_original_function_bytes_recovered=True,raw_observation_retention_only=True,
        Native_case_credit=0,actual_SQL_executed=0)


def business():
    text,proof=prepared_sources()
    module=ModuleType('complete_DE_original_committed_E_witness')
    module.__file__=str(HERE/'actual_committed_E_witness.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    return module,proof
