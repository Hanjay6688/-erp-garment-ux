"""Actual source/Original reader for Node, no database or response fixtures."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def read():
    prior=sys.argv;sys.argv=prior[:1];sys.path.insert(0,str(ROOT/'scripts'))
    try:
        spec=importlib.util.spec_from_file_location('sku27_node_static_closure',HERE/'closure.py')
        closure=importlib.util.module_from_spec(spec);spec.loader.exec_module(closure)
        committed=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:scripts/current-sku-managed-recovery-native27-qualification/SOURCE.json'])
        assert committed==(HERE/'SOURCE.json').read_bytes(),'SKU27_NODE_COMMITTED_SOURCE_MANIFEST_REQUIRED'
        static=closure.source_only(require_clean=False)
        spec=importlib.util.spec_from_file_location('sku27_node_DB_guard',HERE/'source_context.py')
        context=importlib.util.module_from_spec(spec);spec.loader.exec_module(context)
        # In CI there is one physical auditor checkout. Explicit preload also
        # preserves that identity in a multi-worktree local source review.
        with context.fenced_source_read()as guard:
            import cp7_vendor_receivable.composition as vendor
            assert Path(vendor.__file__).resolve()==ROOT/'scripts/cp7_vendor_receivable/composition.py'
            sys.path.insert(0,str(ROOT/'scripts'))
            from cp7_sku_pair_conversion import composition as product
            assert Path(product.__file__).resolve()==ROOT/'scripts/cp7_sku_pair_conversion/composition.py'
            spec=importlib.util.spec_from_file_location('sku27_node_actual_source_transition',HERE/'transition.py')
            transition=importlib.util.module_from_spec(spec);spec.loader.exec_module(transition)
            transition.historical_sources(product)
            spec=importlib.util.spec_from_file_location('sku27_node_original_reader',HERE/'admission.py')
            admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
            retained=admission.retained(product)
            actual=product.sources()
        raw=(json.dumps(actual,sort_keys=True,separators=(',',':'),default=str)+'\n').encode()
        return dict(actual_current_installation=actual,actual_current_sources_sha256=sha256(raw).hexdigest(),
          authentic_retained_Original=retained,product_public_head=transition.PRODUCT_HEAD,
          product_tree=transition.PRODUCT_TREE,static_current_source=static,DB_source_guard=guard,
          projected_sources=False,database_calls=0,actual_new_cases=0)
    finally:sys.argv=prior

if __name__=='__main__':
    assert len(sys.argv)==1,'SKU27_NODE_SOURCE_READER_EMPTY_ABI'
    print(json.dumps(read(),sort_keys=True,default=str))
