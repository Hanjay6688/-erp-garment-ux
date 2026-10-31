"""Use the natural joined product; never overlay or mutate a frozen backend."""
from pathlib import Path
from contextlib import contextmanager
import importlib,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


@contextmanager
def actual_backend(proof):
    if(proof.get('status')!='EXACT_CURRENT_PARENTS_AND_NATURAL_S03_ON_SKU_PRODUCT_SOURCE_ADMITTED'
       or proof.get('product_sources_override')is not False):raise ValueError('JOIN_ACTUAL_ADMISSION_BEFORE_BACKEND_REQUIRED')
    before_path=list(sys.path);before_argv=sys.argv
    try:
        sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'scripts'))
        product=importlib.import_module('cp7_s03_sku_composition.composition')
        if Path(product.__file__).resolve()!=ROOT/'scripts/cp7_s03_sku_composition/composition.py':
            raise ValueError('JOIN_ACTUAL_CURRENT_BACKEND_PATH_REQUIRED')
        if product.sources()!=proof['current_installation']:raise ValueError('JOIN_ACTUAL_CURRENT_WHOLE_PRODUCT_SOURCE_CHANGED')
        yield product
    finally:sys.path[:]=before_path;sys.argv=before_argv
