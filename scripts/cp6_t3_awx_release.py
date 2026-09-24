#!/usr/bin/env python3
"""T3: AW and AX as release candidates of the combined package (same guard pattern as AO..AV).

AW (close readiness engine) and AX (finished goods without a production source) passed T1 as development files
(supabase/dev/cp6_aw_t1_family.sql, cp6_ax_t1_family.sql). A release file needs what AO..AV have: closed and drained
admission, an exact predecessor in both ledgers (the statements sha256 of the previous file), the whole erp/public
catalog pinned before and after the install, and the platform ledger row. This builder wraps each T1 body unchanged
(only the ledger description stops saying "development install") and writes the sources to
supabase/release/cp6-t3-src/. Their catalog pins are placeholders that refuse until scripts/cp6_t3_release_package.py
capture derives the live values on the hosted-faithful chain; the ledger pins cascade like the rest of the package.
No rollback file yet (NOT_TESTED, as for the whole package). Label: T3_PREP.

Usage: python scripts/cp6_t3_awx_release.py
"""
from pathlib import Path
import hashlib,re,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp6_t3_release_package as package

SRC=ROOT/'supabase/release/cp6-t3-src'
AV=next((ROOT/'supabase/migrations').glob('*_erp_v2_6_20av_*.sql'))
FILES=[
    dict(key='AW',stamp='20260924010000',name='erp_v2_6_20aw_cp6_close_readiness_engine',version='v2.6.20aw',
         body=ROOT/'supabase/dev/cp6_aw_t1_family.sql',title='close readiness engine (one engine for preflight, close and the owner report)',
         description='Close readiness engine: preflight, close and report share one per-date engine'),
    dict(key='AX',stamp='20260924010100',name='erp_v2_6_20ax_cp6_fg_unsourced_receipts',version='v2.6.20ax',
         body=ROOT/'supabase/dev/cp6_ax_t1_family.sql',title='finished goods without a production source',
         description='Finished goods without a production source: owner receipt with average HPP and reversal'),
]
PLACEHOLDER='0'*64


def block(text,name):
    m=re.search(r"do \$%s\$.*?end \$%s\$;\n"%(name,name),text,re.S)
    assert m,name
    return m.group(0)


def body(path,version,description):
    lines=path.read_text().splitlines(keepends=True)
    assert lines[2]=='begin;\n' and lines[-1]=='commit;\n'
    inner=''.join(lines[3:-1])
    marker=re.compile(r"insert into erp\.schema_migrations\(version,description\) values\('%s','[^']*'\);\n"%re.escape(version))
    assert len(marker.findall(inner))==1
    return marker.sub("insert into erp.schema_migrations(version,description) values('%s','%s');\n"%(version,description),inner)


def catalog_guard(inner,agg,code):
    return ("do $catalog_guard$\ndeclare actual jsonb;fingerprint text;object_count bigint;\nbegin\n select * into actual from (\n%s\n) catalog;\n"
            " select count(*),%s into object_count,fingerprint from jsonb_each_text(actual);\n if object_count<>0 or fingerprint is distinct from '%s' then\n"
            "  raise exception '%s';\n end if;\nend $catalog_guard$;\n")%(inner,agg,PLACEHOLDER,code)


def build():
    av=AV.read_text()
    admission=block(av,'closed_admission');business=block(av,'lock_business')
    guard=package.catalog_blocks(av)[1]
    SRC.mkdir(parents=True,exist_ok=True)
    previous=dict(stamp=AV.name[:14],name=AV.name[15:-4],version='v2.6.20av',sha=package.sha(av))
    out=[]
    for f in FILES:
        code=f['key']
        predecessor=("do $predecessor$\nbegin\n if not exists(select 1 from erp.schema_migrations where version='%(pv)s')\n"
            "  or exists(select 1 from erp.schema_migrations where version='%(v)s')\n"
            "  or (select count(*) from supabase_migrations.schema_migrations where name='%(pn)s')<>1\n"
            "  or not exists(select 1 from supabase_migrations.schema_migrations where version='%(ps)s' and name='%(pn)s'\n"
            "   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='%(psha)s')\n"
            "  or exists(select 1 from supabase_migrations.schema_migrations where version>'%(ps)s') then raise exception '%(c)s_EXACT_PREDECESSOR_REQUIRED';end if;\n"
            "end $predecessor$;\n")%dict(pv=previous['version'],v=f['version'],pn=previous['name'],ps=previous['stamp'],psha=previous['sha'],c=code)
        text=("-- CP6 %s: %s. Release candidate of the T3 combined package; closed, drained maintenance required.\n"
              "begin;\n"
              "-- Built by scripts/cp6_t3_awx_release.py from %s (sha256 %s): the T1 body below is unchanged apart from the\n"
              "-- ledger description; guards follow AO..AV. Catalog pins are placeholders until the T3 capture (refuse as is).\n"
              "set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';\n"
              "set local role postgres;\n")%(code,f['title'],f['body'].relative_to(ROOT),package.sha(f['body'].read_text()))
        text+=admission
        text+="lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;\n"
        text+=business+predecessor
        text+=catalog_guard(guard['inner'],guard['agg'],code+'_PREDECESSOR_CATALOG_DRIFT')
        text+=body(f['body'],f['version'],f['description'])
        text+=catalog_guard(guard['inner'],guard['agg'],code+'_INSTALLED_CATALOG_DRIFT')
        text+="commit;\n"
        path=SRC/('%s_%s.sql'%(f['stamp'],f['name']))
        path.write_text(text)
        out.append((path.relative_to(ROOT),package.sha(text)))
        previous=dict(stamp=f['stamp'],name=f['name'],version=f['version'],sha=package.sha(text))
    for p,s in out:print(p,s)


if __name__=='__main__':build()
