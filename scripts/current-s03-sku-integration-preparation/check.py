"""Current joined source and recorded parent ABI only; never execute SQL."""
from hashlib import sha256
from pathlib import Path
import argparse,ast,importlib,importlib.util,json,sys,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def check(archive):
    declaration=json.loads((HERE/'SOURCE_IMPORTS.json').read_bytes())
    if declaration['unresolved_conflicts'] or declaration['actual_composite_install_qualified']is not False:
        raise ValueError('JOIN_SOURCE_PREPARATION_ONLY_REQUIRED')
    for row in declaration['files']:
        path=ROOT/row['path'];raw=path.read_bytes()
        if len(raw)!=row['bytes'] or sha256(raw).hexdigest()!=row['sha256'] or path.is_symlink():
            raise ValueError('JOIN_DECLARED_SOURCE_CHANGED: '+row['path'])
    original=(ROOT/'scripts/cp7_attendance_period_choice/composition.py').read_bytes()
    actual=(ROOT/'scripts/cp7_s03_sku_composition/composition.py').read_bytes()
    derived=original.decode()
    for change in declaration['S03_composition_derivation']['changes']:
        if derived.count(change['before'])!=change['count']:raise ValueError('JOIN_EXACT_PARENT_ROUTE_ANCHOR_REQUIRED')
        derived=derived.replace(change['before'],change['after'],change['count'])
    if derived.encode()!=actual:raise ValueError('JOIN_ONLY_DECLARED_PARENT_ROUTE_ALLOWED')
    functions=lambda raw:{n.name:ast.dump(n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
    if functions(original)!=functions(actual):raise ValueError('JOIN_S03_FINANCIAL_FUNCTION_BODIES_CHANGED')
    raw=archive.read_bytes()
    if len(raw)!=94787144 or sha256(raw).hexdigest()!='06d8605b40b05c62b6a9cc7115444560f403d6c1844aa114e901e76a26ac9ac0':
        raise ValueError('JOIN_EXACT_RECORDED_E925_ORIGINAL_REQUIRED')
    del raw
    with zipfile.ZipFile(archive)as z:
        main=json.loads(z.read('CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'))
    # This failed run supplies actual source definitions only. It is never
    # admitted here as the qualified parent of a real installation.
    if main['status']!='INCOMPLETE' or main['qualification_commit']!='e9256772579f387df77dde949f8ea619cbd86856':
        raise ValueError('JOIN_RECORDED_FAILURE_MUST_REMAIN_FAILED')
    part=next(iter(main['committed'].values()))
    catalog=part['Native_to_copy_handoff']['raw_current_catalog']
    context=load('joined_source_no_DB_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    saved=sys.argv
    try:
        sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'scripts'))
        with context.fenced_source_read()as guard:
            product=importlib.import_module('cp7_s03_sku_composition.composition')
            sku=importlib.import_module('cp7_sku_pair_conversion.composition')
            if product.parent()is not sku or product.predecessor is not sku:
                raise ValueError('JOIN_NATURAL_ACTUAL_SKU_PARENT_IMPORT_REQUIRED')
            # This is an ABI derivation, not the full retained-runtime gate.
            # Never substitute a recorded graph for product.sources(). A real
            # installation must evaluate that function with every Original.
            recorded=main['source_declaration']['current_installation']
            leaves=recorded['files']
            if recorded['contract']!=sku.CONTRACT or len(leaves)!=10:
                raise ValueError('JOIN_EXACT_RECORDED_SKU_TEN_LEAVES_REQUIRED')
            for name,digest in leaves.items():
                path=ROOT/name
                if path.is_symlink()or not path.resolve().is_relative_to(ROOT)or sha256(path.read_bytes()).hexdigest()!=digest:
                    raise ValueError('JOIN_RECORDED_SKU_PRODUCT_LEAF_CHANGED: '+name)
            delta=product.native_delta
            overlap=set(delta.SIGNATURES)&set(sku.CAPTURE_SIGNATURES)
            if overlap:raise ValueError('JOIN_NATIVE_SIGNATURE_COLLISION: '+repr(sorted(overlap)))
            originals={name:catalog['functions'][name][0]for name in delta.SIGNATURES}
            definitions=delta.patched(originals);clones=delta.clones(originals)
            if set(definitions)!=set(originals) or len(definitions)!=15 or len(clones)!=2:
                raise ValueError('JOIN_EXACT_CURRENT15_AND_TWO_NATIVE_CLONES_REQUIRED')
    finally:sys.argv=saved
    return dict(status='SOURCE_JOIN_AND_RECORDED_PARENT_ABI_DERIVATION_PASS_NOT_RUNTIME',
        declared_imports=len(declaration['files']),UI_three_way_merges=declaration['ui'],
        natural_predecessor='cp7_sku_pair_conversion',actual_import_namespace='cp7_s03_sku_composition',
        recorded_parent_status='INCOMPLETE_NOT_QUALIFICATION_PREREQUISITE',
        exact_installed_parent_definitions=15,private_Native_clones_derived=2,
        source_signature_overlap=sorted(overlap),all_S03_function_AST_bodies_unchanged=True,
        exact_recorded_SKU_product_leaves=len(leaves),
        complete_product_sources_evaluated=False,recorded_sources_used_as_runtime_substitute=False,
        full_retained_runtime_source_and_Original_gate_still_required=True,
        original_source_sha256={name:sha256(value.encode()).hexdigest()for name,value in originals.items()},
        derived_source_sha256={name:sha256(value.encode()).hexdigest()for name,value in definitions.items()},
        source_DB_guard=guard,actual_Native_cases=0,actual_browser_cases=0,
        actual_composite_install_qualified=False,global_writer_or_permission_closure_proven=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sku-archive',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(check(args.sku_archive),indent=2))
