"""Prepare complete S03 Native14 sources for the joined product; never run SQL.

The owning composite caller must supply the declared private bindings only
after admitting every current source and actual parent Original. No executable
runtime entrypoint, database, test actor or qualification gate is supplied here.
"""
from hashlib import sha256
from pathlib import Path
import argparse,ast,importlib.util,json

HERE=Path(__file__).resolve().parent
EXPECTED_REFERENCES={'cases.py','fixtures.py','business.py','lawful_fixture.py','CALLBACK_CHANGES.json',
    'reader_cases.py','native_runner.py','reader_group.py','native14_derive.py'}


def literal(raw,name):
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.Assign)
           and any(isinstance(t,ast.Name)and t.id==name for t in n.targets)]
    if len(nodes)!=1:raise ValueError('JOIN_NATIVE14_EXACT_LITERAL_REQUIRED: '+name)
    return ast.literal_eval(nodes[0].value)


def substitute(raw,pairs):
    value=raw.decode()
    for before,after in pairs:
        if before==after or value.count(before)!=1 or after in value:
            raise ValueError('JOIN_NATIVE14_EXACT_BINDING_ANCHOR_REQUIRED')
        value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(pairs):
        if reverse.count(after)!=1:raise ValueError('JOIN_NATIVE14_UNIQUE_REVERSE_REQUIRED')
        reverse=reverse.replace(after,before,1)
    if reverse.encode()!=raw:raise ValueError('JOIN_NATIVE14_EXACT_ORIGINAL_BYTES_REQUIRED')
    return value,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(value.encode()).hexdigest(),
        counted_change_groups=len(pairs),all_other_bytes_exact=True,original_bytes_recovered=True)


def callbacks(raw):
    factory=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='cases')
    return {n.name:ast.dump(n)for n in factory.body if isinstance(n,ast.FunctionDef)}


def prepare(here=HERE):
    here=Path(here)
    if any(path.is_symlink()for path in(here,here/'RETAINED.json',here/'retained-s03-f42e')):
        raise ValueError('JOIN_NATIVE14_SOURCE_SYMLINK_FORBIDDEN')
    manifest=json.loads((here/'RETAINED.json').read_bytes());raw={}
    if(manifest['source_commit']!='f42e76978852ba9efe34f75a4b622990c0331866'
       or manifest['actual_Native_cases']!=0 or manifest['production_go']is not False
       or manifest['independent_acceptance']is not False):raise ValueError('JOIN_NATIVE14_SOURCE_PREPARATION_ONLY_REQUIRED')
    if set(manifest['retained_sources'])!=EXPECTED_REFERENCES:
        raise ValueError('JOIN_NATIVE14_EXACT_NINE_REFERENCE_NAMES_REQUIRED')
    for name,pin in manifest['retained_sources'].items():
        path=here/'retained-s03-f42e'/name;value=path.read_bytes()
        if path.is_symlink()or len(value)!=pin['bytes']or sha256(value).hexdigest()!=pin['sha256']:
            raise ValueError('JOIN_NATIVE14_RETAINED_SOURCE_CHANGED: '+name)
        raw[name]=value
    if len(raw)!=9:raise ValueError('JOIN_NATIVE14_EXACT_NINE_REFERENCES_REQUIRED')
    spec=importlib.util.spec_from_file_location('join_native14_pure_lawful_deriver',here/'retained-s03-f42e/business.py')
    lawful=importlib.util.module_from_spec(spec);spec.loader.exec_module(lawful)
    financial,lawful_proof=lawful.derive(raw['cases.py'])
    core,core_proof=substitute(financial.encode(),(
        ('from cp7_attendance_period_choice import composition','from cp7_s03_sku_composition import composition'),
        ("f=load('S03_prepared_Native_fixture',HERE/'fixtures.py')",'f=JOIN_FIXTURE'),
        ("admission=load('S03_prepared_parent_admission',HERE/'admission.py')",'admission=JOIN_PARENT_ADMISSION'),
    ))
    fixture,fixture_proof=substitute(raw['fixtures.py'],(
        ('from cp7_attendance_period_choice import composition','from cp7_s03_sku_composition import composition'),
    ))
    lawful_reader,reader_lawful_proof=substitute(raw['reader_cases.py'],((lawful.READER_BEFORE,lawful.READER_AFTER),))
    reader,reader_proof=substitute(lawful_reader.encode(),(
        ("admission=load('S03_reader3_local_source_admission',HERE/'admission.py')",'admission=JOIN_READER_ADMISSION'),
        ("return load('S03_unchanged_financial11_for_reader3',ROOT/'scripts/current-attendance-period-choice-qualification/cases.py')",'return JOIN_CORE'),
    ))
    native14,native14_proof=substitute(raw['native_runner.py'],literal(raw['native14_derive.py'],'NATIVE_PAIRS'))
    business_before="""spec = importlib.util.spec_from_file_location('s03_native11_unchanged_prepared_business',
    ROOT / 'scripts/current-attendance-period-choice-qualification/cases.py')
business = importlib.util.module_from_spec(spec)
spec.loader.exec_module(business)"""
    native,native_proof=substitute(native14.encode(),(
        ('from cp7_attendance_period_choice import composition as product','from cp7_s03_sku_composition import composition as product'),
        ('from cp7_attendance_period_choice import native_delta','from cp7_s03_sku_composition import native_delta'),
        (business_before,'business = JOIN_BUSINESS'),
    ))
    reader_before="""    spec = importlib.util.spec_from_file_location('s03_native14_actual_authored_reader3', ROOT / FACTORY)
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)"""
    group,group_proof=substitute(raw['reader_group.py'],(
        ("cfg = json.loads((HERE / 'CONFIG.json').read_bytes())",'cfg = JOIN_CONFIG'),
        (reader_before,'    reader = JOIN_READER'),
    ))
    financial_ids=literal(raw['cases.py'],'IDS');reader_ids=literal(raw['reader_cases.py'],'IDS')
    if len(financial_ids)!=11 or len(reader_ids)!=3 or len(set(financial_ids+reader_ids))!=14:
        raise ValueError('JOIN_NATIVE14_EXACT_CASE_IDENTITIES_REQUIRED')
    if callbacks(core)!=callbacks(financial)or callbacks(reader)!=callbacks(lawful_reader):
        raise ValueError('JOIN_NATIVE14_ROUTING_CHANGED_FINANCIAL_OR_READER_CALLBACK')
    sources=dict(core=core,fixture=fixture,reader=reader,native_runner=native,reader_group=group,
        lawful_fixture=raw['lawful_fixture.py'].decode())
    for name,value in sources.items():compile(value,'joined-source-only/'+name+'.py','exec')
    bindings=dict(core=['JOIN_FIXTURE','JOIN_PARENT_ADMISSION','LAWFUL','CORE'],
        reader=['JOIN_READER_ADMISSION','JOIN_CORE','LAWFUL'],
        native_runner=['JOIN_BUSINESS','CURRENT_READER_IDS','run_actual_reader3'],
        reader_group=['JOIN_CONFIG','JOIN_READER'])
    proof=dict(status='S03_NATIVE14_SOURCE_BINDINGS_COMPILED_NOT_EXECUTED',retained_sources=9,
        complete_compiled_modules=len(sources),separate_strict_groups=[11,3],
        original11_ids=financial_ids,reader3_ids=reader_ids,
        original_lawful_derivation=lawful_proof,core_route=core_proof,fixture_route=fixture_proof,
        original_reader_lawful_derivation=reader_lawful_proof,reader_route=reader_proof,
        retained_complete_native14_derivation=native14_proof,native_route=native_proof,reader_group_route=group_proof,
        all_current_lawful_financial11_callback_ASTs_exact=True,all_current_lawful_reader3_callback_ASTs_exact=True,
        original_committed_ALLOCATE_used_witness_retained=True,
        complete_strict_group_public_catalog_and_restoration_checks_retained=True,
        required_private_runtime_bindings=bindings,
        runtime_admission_or_outer_caller_supplied=False,actual_Native_cases=0,actual_browser_cases=0,
        production_go=False,independent_acceptance=False)
    return sources,proof


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(prepare()[1],indent=2))
