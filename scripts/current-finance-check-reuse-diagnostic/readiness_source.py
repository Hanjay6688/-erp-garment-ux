"""Exact post-BA, post-CP7 readers matched to the f038 live snapshot hash."""
from pathlib import Path
from hashlib import sha256
import json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp7_note_report_bundle as notes
import cp7_report_accounts_bundle as accounts

def extract(text,name,delimiter,replace=True):
    head='CREATE OR REPLACE FUNCTION 'if replace else'create function '
    pattern=re.escape(head+name+'(')+r'[\s\S]*?'+re.escape('AS '+delimiter if replace else'as '+delimiter)+r'([\s\S]*?)'+re.escape(delimiter+';')
    matches=list(re.finditer(pattern,text))
    if len(matches)!=1:raise ValueError('INSTALLED_REPORT_FUNCTION_SHAPE_CHANGED:'+name)
    return matches[0].group(0),matches[0].group(1)

def derive():
    ba=(ROOT/'supabase/dev/cp6_ba_t1_family.sql').read_text()
    aw=(ROOT/'supabase/dev/cp6_aw_t1_family.sql').read_text()
    read=(ROOT/'scripts/cp7-src/finance/read.sql').read_text()
    definition,base=extract(ba,'erp.get_owner_financial_snapshot_v2','$function$')
    installed=accounts.wrap(notes.SIGNATURE,notes.patched_report(definition))
    snapshot=installed.split('$function$')[1]
    _,preflight=extract(aw,'erp.accounting_close_preflight_v1','$function$')
    _,workspace=extract(read,'cp7_finance.workspace','$$',False)
    return dict(snapshot=snapshot,preflight=preflight,workspace=workspace),dict(
        native_BA_body_sha256=sha256(base.encode()).hexdigest(),installed_snapshot_sha256=sha256(snapshot.encode()).hexdigest(),
        installed_snapshot_bytes=len(snapshot.encode()),preflight_sha256=sha256(preflight.encode()).hexdigest(),
        workspace_sha256=sha256(workspace.encode()).hexdigest())

def expected():
    source=json.loads((HERE/'INSTALLED_REPORT_SOURCE.json').read_bytes())
    for rel,digest in source['sources'].items():
        if sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise ValueError('INSTALLED_REPORT_SOURCE_CHANGED:'+rel)
    bodies,derived=derive()
    if derived!=source['derived']:raise ValueError('INSTALLED_REPORT_DERIVATION_CHANGED')
    if derived['installed_snapshot_sha256']!=source['actual_f038_live_body_sha256']:
        raise ValueError('INSTALLED_REPORT_DOES_NOT_MATCH_OBSERVED_LIVE_BODY')
    return bodies,source
