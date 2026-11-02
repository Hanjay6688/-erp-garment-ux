"""Record the actual pre-refinement route and stylesheet inventory once."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'docs/cp7/d17-14/ui-reference-20261103/UI_INVENTORY.json'


def main():
    text=(ROOT/'src/auth/accessCatalog.ts').read_text()
    catalogs={}
    for key in('NAV_PERMISSION_BY_LABEL','PAGE_PERMISSION_BY_ID'):
        start=text.index('Object.freeze({',text.index('export const '+key))+len('Object.freeze({')
        end=text.index('\n})',start)
        catalogs[key]={a or b:c for a,b,c in re.findall(r"(?:'([^']+)'|([\w-]+)):\s*'([^']+)'",text[start:end])}
    stylesheets=[]
    for path in sorted((ROOT/'src').rglob('*.css')):
        raw=path.read_bytes();css=raw.decode()
        row={
            'path':str(path.relative_to(ROOT)),
            'bytes':len(raw),
            'sha256':sha256(raw).hexdigest(),
            'literal_colors':dict(Counter(re.findall(r'#[0-9a-fA-F]{3,8}\b',css))),
            'css_variable_uses':len(re.findall(r'var\(--',css)),
            'important_count':css.count('!important'),
            'status':'PENDING_REFINEMENT_AND_VISUAL_VERIFICATION',
        }
        stylesheets.append(row)
    value={
        'contract':'cp7.owner-ui-refinement-inventory.v1',
        'integrator':'WRITER_A',
        'base_head':'2c7a5a05516548667ec71faedcffb3591828100f',
        'base_tree':'349b0ed64c2fa1b719976ff286bfe2a98030a4c4',
        'owner_handoff':{'library_file_id':'libfile_2c81e41399488191967a3c7751b24997','sha256':'213f1bb0ffb376f51245b90bbef451b81b83a35710f076cf78d2bc457da11a53'},
        'primary_reference':{'library_file_id':'libfile_bd803f2016088191932a8e42a16b9d26','sha256':'7650b1d8bb940f26ddb7fe5807e3e1c3b218ffab60b57b882a80a17d7cd5996d'},
        'secondary_reference':{'library_file_id':'libfile_3fae5120bf808191be0848d80d8c723b','sha256':'d6e1d6d07c799236c3aee0a5ab705bcd3e687b090054a42e79e1db65cba5b363'},
        'images_visually_read':True,
        'scope_is_owner_requested_UI_refinement_not_CP7_denominator_change':True,
        'routes':catalogs['PAGE_PERMISSION_BY_ID'],
        'navigation_labels':catalogs['NAV_PERMISSION_BY_LABEL'],
        'stylesheets':stylesheets,
        'representative_families':['Shell/shared controls','Dashboard','Penjualan/list/form','Payroll/Mandor popup','Kartu stok','Produksi/Laundry/BS','Keuangan','Master/Pengaturan','CP7 panels'],
        'planned_viewports':[320,390,768,1440],
        'actual_visual_acceptance':False,
        'actual_changed_financial_sources':0,
        'CP7_complete':False,
        'production_go':False,
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    with OUTPUT.open('x')as output:output.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'status':'ACTUAL_SOURCE_UI_INVENTORY_WRITTEN_NOT_IMPLEMENTATION',
        'routes':len(value['routes']),'navigation_labels':len(value['navigation_labels']),
        'stylesheets':len(stylesheets),'baseline':value['base_head']}))


if __name__=='__main__':main()
