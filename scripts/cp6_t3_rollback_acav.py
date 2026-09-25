#!/usr/bin/env python3
"""Release variants of the AC..AV rollbacks for the T3 release package (independent audit B3 / CP6-12).

The reviewed rollbacks in supabase/rollbacks pin the test chain: the statements digest the test applier recorded for
each file, and (AO..AV) the catalog fingerprints and history capsule hashes of the test chain. On the hosted-faithful
release chain those pins are different, so the original files refuse there (by design; they are not loosened). The
release package recorded, per file, exactly which test-chain pin became which release pin (docs/evidence/cp6-t3/
release_pins.json). A release variant is the original rollback with the same substitutions and nothing else:

  STATEMENTS  the statements digest of a file (own or predecessor): source sha256 -> package sha256. Where the original
              accepted two digests (AC..AN: the file and the test applier's form), the variant accepts only the digest
              the release applier records (the package file's sha256).
  CATALOG     object count and fingerprint of a catalog state (installed or predecessor), as re-pinned in the package.
  CAPSULE     hash of a history capsule, as re-pinned in the package.
  AC_VIEW     the pre-AC source of erp.v_payroll_nota_browser and its restore statement digest, as the package uses the
              hosted text (G-01 view finding).

Every other pin (function definition hashes, capsule shapes, data boundaries recorded at install) is left unchanged and
must hold on the release chain; the T3 rollback cycle (scripts/cp6_t3_rollback.py cycle) proves each variant restores
the state before its file exactly. The build stops on a catalog pin it cannot map. Label: T3_PREP.
"""
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1]
TEST=ROOT/'supabase/rollbacks'
OUTDIR=ROOT/'supabase/release/cp6-t3-rollbacks'
PINS=ROOT/'docs/evidence/cp6-t3/release_pins.json'
KEYS=['AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AP','AQ','AR','AS','AT','AU','AV']
H=re.compile(r'[0-9a-f]{64}')
IN_PAIR=re.compile(r"in\(\s*'(?P<a>[0-9a-f]{64})'\s*,\s*'(?P<b>[0-9a-f]{64})'\s*\)")
CATALOG_PIN=re.compile(r"object_count<>(?P<count>\d+) or fingerprint is distinct from '(?P<fp>[0-9a-f]{64})'")
CATALOG_SUB=re.compile(r"if object_count<>(?P<count>\d+) or fingerprint is distinct from '(?P<fp>[0-9a-f]{64})' then")


def sha(text):
    import hashlib
    return hashlib.sha256(text.encode() if isinstance(text,str) else text).hexdigest()


def maps(pins):
    statements={f['source_sha256']:f['package_sha256'] for f in pins['files']}
    catalog={};capsule={};strings=[]
    for f in pins['files']:
        for s in f['subs']:
            if s['kind']=='CATALOG':
                o=CATALOG_SUB.search(s['old']);n=CATALOG_SUB.search(s['new'])
                old=(int(o.group('count')),o.group('fp'));new=(int(n.group('count')),n.group('fp'))
                if old[1]=='0'*64:continue  # AW..BA placeholders, pinned at capture
                assert catalog.get(old,new)==new,('T3_ACAV_CATALOG_PIN_AMBIGUOUS',old)
                catalog[old]=new
            elif s['kind']=='CAPSULE':
                o=H.findall(s['old']);n=H.findall(s['new'])
                assert len(o)==len(n)==1
                # AW..BA sources carry zero placeholders for capsules pinned at capture; a test-chain rollback has none.
                if o[0]=='0'*64:continue
                assert capsule.get(o[0],n[0])==n[0],('T3_ACAV_CAPSULE_PIN_AMBIGUOUS',s['what'])
                capsule[o[0]]=n[0]
            elif s['kind']=='AC_VIEW':strings.append((s['what'],s['old'],s['new']))
    return statements,catalog,capsule,strings


def source_file(key):
    [path]=sorted(TEST.glob('*_erp_v2_6_20%s_*.rollback.sql'%key.lower()))
    return path


def variant(key,entry,pins):
    """The release variant of KEY's rollback and a record of every substitution."""
    statements,catalog,capsule,strings=maps(pins)
    path=source_file(key);text=path.read_text();out=text
    record=dict(key=key,source=str(path.relative_to(ROOT)),source_sha256=sha(text),subs=[])
    # AC..AN: the pair (file digest, test applier digest) becomes the one digest the release applier records.
    def pair(m):
        a,b=m.group('a'),m.group('b')
        assert a in statements and b not in statements and b not in statements.values(),('T3_ACAV_PAIR',key,a,b)
        record['subs'].append(dict(kind='STATEMENTS_PAIR',old=[a,b],new=statements[a]))
        return "in('%s')"%statements[a]
    out=IN_PAIR.sub(pair,out)
    def catalog_pin(m):
        old=(int(m.group('count')),m.group('fp'))
        assert old in catalog,('T3_ACAV_CATALOG_PIN_UNMAPPED',key,old)
        new=catalog[old];record['subs'].append(dict(kind='CATALOG',old=list(old),new=list(new)))
        return "object_count<>%d or fingerprint is distinct from '%s'"%new
    out=CATALOG_PIN.sub(catalog_pin,out)
    for what,old,new in strings:
        n=out.count(old)
        if n:
            assert n==1,('T3_ACAV_VIEW_TEXT',key,what,n)
            out=out.replace(old,new);record['subs'].append(dict(kind='AC_VIEW',what=what,count=n))
    # Remaining single digests: statements (own or predecessor) and capsule hashes, each replaced where it stands.
    def digest(m):
        h=m.group(0)
        if h in statements:
            record['subs'].append(dict(kind='STATEMENTS',old=h,new=statements[h]));return statements[h]
        if h in capsule:
            record['subs'].append(dict(kind='CAPSULE',old=h,new=capsule[h]));return capsule[h]
        return h
    out=H.sub(digest,out)
    own=[s for s in record['subs'] if s['kind'] in ('STATEMENTS','STATEMENTS_PAIR') and s['new']==entry['package_sha256']]
    assert own,('T3_ACAV_OWN_STATEMENTS_NOT_PINNED',key)
    # No test-chain statements digest may remain.
    left=[h for h in H.findall(out) if h in statements]
    assert not left,('T3_ACAV_TEST_DIGEST_LEFT',key,left)
    record['unchanged_pins']=len(set(H.findall(out))-{s['new'] for s in record['subs'] if isinstance(s.get('new'),str)})
    header='-- T3 release variant of %s (sha256 %s), built by scripts/cp6_t3_rollback_acav.py from docs/evidence/cp6-t3/release_pins.json.\n'%(
        record['source'],record['source_sha256'])
    out=header+out
    record['sha256']=sha(out)
    return out,record


def target(entry):return OUTDIR/('%s_%s.rollback.sql'%(entry['stamp'],entry['name']))


def build(files,write=True):
    pins=json.loads(PINS.read_text())
    assert [f['key'] for f in pins['files']][:len(KEYS)]==KEYS
    out={}
    for key in KEYS:
        text,record=variant(key,files[key],pins)
        out[key]=(target(files[key]),text,record)
    if write:
        OUTDIR.mkdir(parents=True,exist_ok=True)
        for p,t,_ in out.values():p.write_text(t)
    return out


def manifest():
    return {f['key']:f for f in json.loads((ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_text())['files']}


if __name__=='__main__':
    built=build(manifest())
    print(json.dumps({k:dict(file=str(p.relative_to(ROOT)),sha256=r['sha256'],subs=len(r['subs']),unchanged=r['unchanged_pins'])
                      for k,(p,t,r) in built.items()},indent=1))
