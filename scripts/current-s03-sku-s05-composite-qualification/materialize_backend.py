"""Create one exact detached backend checkout, with no source substitution."""
from pathlib import Path
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
if __name__=='__main__':
    path=ROOT/'scripts/current-finance-combined-composition/materialize_sources.py'
    spec=importlib.util.spec_from_file_location('joined_exact_backend_materializer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    proof=module.materialize(ROOT,{'qualified-sku090b':'090b85d3fcb738d3e694d4329d306f199a686eb8'})
    (ROOT/'cp6-proof/t3/JOIN_QUALIFIED_BACKEND_CHECKOUT.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof))
