"""Keep the BF verifier and the SKU installer's source-frozen Python environments separate."""
import importlib.util
import sys
import os
import json
import tempfile
from pathlib import Path
from close11 import frozen,checkpoint

WORK=Path(os.environ["GITHUB_WORKSPACE"])
TEMP=Path(os.environ["RUNNER_TEMP"])
OUT=Path(os.environ["STAGE_PATH"])
def load_bf():
    spec = importlib.util.spec_from_file_location("bf_observer", WORK/"qualification-source/qualification/cp75-clean-bf/checkpoint.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m



def main():
    bf=load_bf()
    if sys.argv[1]=="before":
        original=bf.readback(frozen.SOURCE)
        assert original["cp6_rollback"]["catalogue_sha256"]=="b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
        (OUT/"bf-verified.json").write_text(json.dumps(original,indent=2)+"\n")
        return
    report=json.loads((OUT/"progress.json").read_text())
    assert report["phases"][-1]=="SKU_COMMITTED_AND_READ_BACK"
    image=frozen.docker("installed image",["inspect","-f","{{.Image}}",frozen.SOURCE])
    public=WORK/"capture/qualification/close11/auditor-public.pem"
    with tempfile.TemporaryDirectory(dir=TEMP) as root:
        raw=Path(root)/"sku.tar.gz"
        metadata=frozen.freeze(raw,image)
        before=bf.readback(frozen.SOURCE)
        after=bf.boot(raw,metadata,image)
        assert before==after
        report["recovery"]={"before":before,"after":after,"copy":metadata,"plaintext_sha256":checkpoint.digest(raw),
                            "archive":checkpoint.seal(raw,OUT/"sku.cp75",public)}
    report["phases"].append("SKU_PHYSICAL_RESTORE")
    (OUT/"progress.json").write_text(json.dumps(report,indent=2,default=str)+"\n")
    print("CP75_SKU_STAGE SKU_PHYSICAL_RESTORE",flush=True)

if __name__=="__main__":
    main()
