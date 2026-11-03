"""Test early sourced-cost ordering in exact Native bodies, with explicit providers.

This generates a focused model input, not an ERP or Auth qualification.
The complete previous91 result remains separately retained and is not recounted.
"""
from pathlib import Path
from hashlib import sha256
import json
import os
import sys

HERE=Path(__file__).resolve().parent
COMPONENT=HERE.parent/'cp7_sku_cost_components'
sys.path.insert(0,str(COMPONENT))
import prepare_legacy_model
from valuation_delta import Derivation

def prepare(destination):
    if any(os.environ.get(k)=='1'for k in('CP7_COST_LEGACY_FULL','CP7_COST_LEGACY_COUNTER','CP7_COST_LEGACY_MORE_ONLY')):
        raise ValueError('COST_ORDER_REQUIRES_FOCUSED_CURRENT_LEGACY_PRODUCT')
    prepare_legacy_model.prepare(destination)
    path=Path(destination)/'test_cost_successor.mjs';original=path.read_text()
    start=original.index(' if(!legacyMoreOnly)for(const lot of[x.root50,x.converted]){')
    end=original.index(' const report={baseCentFindings,',start)
    d=Derivation(original)
    d.once(original[start:end],(HERE/'cost_order_cases.mjs.inc').read_text()+'\n','seven independent early-cost Native ordering controls')
    d.once('MODELED_NATIVE_LEGACY_BODIES_REPAIR_NOT_ERP','MODELED_NATIVE_EARLY_COST_ORDER_NOT_ERP','explicit model scope')
    if d.inverse()!=original:raise ValueError('COST_ORDER_MODEL_NOT_REVERSIBLE')
    path.write_text(d.source)
    print(json.dumps(dict(status='FOCUSED_EXACT_NATIVE_COST_ORDER_PREPARED',business_controls=7,
        harness_sha256=sha256(path.read_bytes()).hexdigest(),actual_ERP_cases=0)))

if __name__=='__main__':prepare(sys.argv[1])
