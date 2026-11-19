"""Read exactly the two released predecessor sources. Never runs database installation."""
import hashlib,importlib.util,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
here=Path(__file__).resolve().parent

def digest(v):return hashlib.sha256(v).hexdigest()

def inspect_source(helper):
    spec=importlib.util.spec_from_file_location('released_s06',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    try:status='COMPATIBLE';bodies=module.expected_bodies()
    except ValueError as exc:status=str(exc);bodies={}
    return status,sorted(bodies)

with tempfile.TemporaryDirectory()as temp:
    test=Path(temp);sql=test/'scripts/cp7-src/alerts/alerts.sql';sql.parent.mkdir(parents=True)
    helper=test/'scripts/cp7_s06_reminder_forward.py';shutil.copyfile(here/helper.name,helper)
    assert digest(helper.read_bytes())=='db11b19996734b3f33bd40db78d41389aa1ca9427a120b4f7bb7a4a3031f32a4'
    shutil.copyfile(sys.argv[1],sql);old=sql.read_bytes();assert digest(old)=='219adb738c65aa56301b4befd266e76da29f0c46db3dba2cc9b97ee4fb214410'
    accepted,signatures=inspect_source(helper);assert accepted=='COMPATIBLE' and len(signatures)==3
    subprocess.run(['git','apply','--whitespace=nowarn',str(here/'candidate-alerts.patch')],cwd=test,check=True)
    new=sql.read_bytes();assert digest(new)=='27efb12850111dccce92916e867ea4268384ed29ea6b07bd0cdbc7aef264a88b';refusal,_=inspect_source(helper);assert refusal=='CP7_S06_PREDECESSOR_SOURCE_CHANGED'
    # Compare named SQL bodies without invoking or modifying the installer's admission check.
    rx=re.compile(rb'^create(?: or replace)? function ([\w.]+)\([^\n]*\n[^\n]*as \$\$(.*?)\$\$;',re.M|re.S)
    pre=dict(rx.findall(old));post=dict(rx.findall(new));assert pre.keys()==post.keys()
    signed=all(pre[sig.split('(')[0].encode()]==post[sig.split('(')[0].encode()]for sig in signatures)
    print('ASTRA_INSTALLER_CHECK '+json.dumps(dict(baseline='7a17d348ea5831454c770586eff4270627003be0',candidate='ffda5cfceb7ebc196656baa650dffd18dd425047',baseline_sha256=digest(old),candidate_sha256=digest(new),qualified_baseline_result=accepted,candidate_result=refusal,compared_alert_definitions=len(pre),changed=[s.decode()for s in pre if pre[s]!=post[s]],three_S06_bodies_unchanged=signed,database_calls=0)))
