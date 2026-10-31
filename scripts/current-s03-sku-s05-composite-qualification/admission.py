"""Full actual joined source graph after both exact current parent Originals."""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import importlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


@contextmanager
def import_scope():
    before_path=list(sys.path);before_argv=sys.argv
    try:
        backend=load('joined_physical_qualified_backend',HERE/'frozen_parent.py').admitted()
        backend_root=Path(backend['path'])
        sys.argv=sys.argv[:1];sys.path.insert(0,str(backend_root/'scripts'))
        # Load the real historical parent and its complete source graph while
        # its own physical checkout is first. Never rewrite a ROOT or source map.
        vendor,sku=load('joined_real_parent_module_selector',HERE/'parent_import.py').parent_modules(backend_root)
        sku.sources()
        sys.path.insert(0,str(ROOT/'scripts'));yield
    finally:sys.path[:]=before_path;sys.argv=before_argv


def admitted():
    source=load('joined_complete_current_source',HERE/'source.py').preflight()
    parents=load('joined_exact_current_parent_originals',HERE/'parents.py').admitted()
    backend=load('joined_exact_backend_before_current_product',HERE/'frozen_parent.py').admitted()
    with import_scope():
        # Preload the current vendor before inherited harness search paths.
        vendor=importlib.import_module('cp7_vendor_receivable.composition')
        sku=importlib.import_module('cp7_sku_pair_conversion.composition')
        product=importlib.import_module('cp7_s03_sku_composition.composition')
        for module,path in((vendor,'cp7_vendor_receivable'),(sku,'cp7_sku_pair_conversion'),(product,'cp7_s03_sku_composition')):
            expected_root=ROOT if module is product else Path(backend['path'])
            if Path(module.__file__).resolve()!=expected_root/'scripts'/path/'composition.py':
                raise ValueError('JOIN_NATURAL_CURRENT_PACKAGE_REQUIRED:'+path)
        if product.parent()is not sku or sku.parent()is not vendor:raise ValueError('JOIN_NATURAL_PARENT_CHAIN_CHANGED')
        current=product.sources()
        # sources() has just evaluated the real SKU parent through the
        # verified natural object chain. Compare that complete observation;
        # evaluating the same graph again adds no independent evidence.
        actual_sku=current['predecessor']
        if actual_sku!=parents['SKU']['current_installation']or current['predecessor']!=actual_sku:
            raise ValueError('JOIN_WHOLE_ACTUAL_SKU_SOURCE_MUST_EQUAL_QUALIFIED_CURRENT_ORIGINAL')
        s03=parents['S03']['current_installation']
        if s03['predecessor']!=actual_sku['predecessor']:
            raise ValueError('JOIN_TWO_QUALIFIED_PARENTS_MUST_HAVE_THE_SAME_REAL_VENDOR')
        for name,digest in s03['files'].items():
            if sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('JOIN_CANONICAL_QUALIFIED_S03_PRODUCT_CHANGED:'+name)
        declared=json.loads((ROOT/'scripts/current-s03-sku-integration-preparation/SOURCE_IMPORTS.json').read_bytes())
        original=(ROOT/'scripts/cp7_attendance_period_choice/composition.py').read_text()
        for change in declared['S03_composition_derivation']['changes']:
            if original.count(change['before'])!=change['count']:raise ValueError('JOIN_EXACT_S03_PARENT_DERIVATION_REQUIRED')
            original=original.replace(change['before'],change['after'],change['count'])
        if original!=(ROOT/'scripts/cp7_s03_sku_composition/composition.py').read_text():
            raise ValueError('JOIN_ONLY_DECLARED_S03_PARENT_IMPORT_AND_DOCUMENTATION_CHANGES_ALLOWED')
        for name,digest in current['files'].items():
            if sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('JOIN_NATURAL_CURRENT_STAGE_FILE_CHANGED:'+name)
    return dict(status='EXACT_CURRENT_PARENTS_AND_NATURAL_S03_ON_SKU_PRODUCT_SOURCE_ADMITTED',
        current_source=source,current_installation=current,qualified_SKU_parent=parents['SKU'],qualified_S03_parent=parents['S03'],
        physical_qualified_SKU_backend=backend,current_UI_is_separately_bound_by_exact_joined_base=True,
        qualified_SKU_current_installation=actual_sku,used_inverse_guard_before_DDL=True,
        product_sources_override=False,projected_source_graph=False,actual_composite_cases_credited=0,
        production_go=False,independent_acceptance=False)
