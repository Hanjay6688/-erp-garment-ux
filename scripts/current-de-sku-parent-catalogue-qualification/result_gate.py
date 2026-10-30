"""Require exact catalogue-only scope and complete outer restoration/all5."""
from pathlib import Path
from hashlib import sha256
import argparse
import json
import subprocess
import context_catalog

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CASE='D1_E_SKU_ACTUAL_PARENT_CATALOGUE_RAW_ACL_SOURCE_ONLY'
GATES={'installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime'}


def require(ok,message):
    if not ok:raise ValueError(message)


def checked(report,package,head):
    require(report.get('status')=='PASS'and report.get('label')=='CP7_D1_E_SKU_PARENT_CATALOGUE'
        and report.get('qualification_commit')==head,'DE_SKU_EXACT_ACTUAL_REPORT_REQUIRED')
    require(report.get('actual_catalogue_qualification_groups')==1 and set(report.get('committed',{}))=={CASE},
            'DE_SKU_EXACT_ONE_CATALOGUE_GROUP_REQUIRED')
    for key in('actual_business_cases','actual_Native_cases','actual_two_session_races','actual_Auth_HTTP_cases','actual_browser_cases'):
        require(type(report.get(key))is int and report[key]==0,'DE_SKU_NO_BUSINESS_CREDIT:'+key)
    require(report.get('used_guard_business_witness_executed')is False and report.get('full_final_composite_qualified')is False,
            'DE_SKU_CATALOGUE_CANNOT_BECOME_BUSINESS_QUALIFICATION')
    for key in('cp6_restored','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','advisor_gate','preuse_catalogue_qualified'):
        require(report.get(key)is True,'DE_SKU_COMPLETE_OUTER_REQUIRED:'+key)
    require(not report.get('error')and not report.get('restore_error'),'DE_SKU_ORIGINAL_FAILURE_CANNOT_BE_HIDDEN')
    case=report['committed'][CASE]
    require(case.get('status')=='PASS'and case.get('read_complete_noeffect')is True,'DE_SKU_ACTUAL_READ_NOEFFECT_REQUIRED')
    require(json.dumps(case['read_before'],sort_keys=True)==json.dumps(case['read_after'],sort_keys=True),
            'DE_SKU_ACTUAL_CATALOGUE_ROWS_SEQUENCES_CHANGED')
    require(case['actual_composite_catalogue']==case['read_before']['catalog'],'DE_SKU_ACTUAL_CATALOGUE_NOT_EMBEDDED_EXACTLY')
    for value in [case['actual_composite_catalogue'],*case['actual_layer_catalogues'].values()]:
        require(set(value)==set(context_catalog.ALL22)and all(type(v)is dict for v in value.values()),'DE_SKU_COMPLETE22_CATALOGUE_GROUPS_REQUIRED')
    require(len(case['actual_context55']['names'])==55 and len(set(case['actual_context55']['names']))==55
        and case['actual_context55']['schema_exclusions']==[],'DE_SKU_EXACT55_CONTEXT_CENSUS_REQUIRED')
    require(set(case['actual_layer_catalogues'])=={'D1','E','SKU'}and case['actual_layer_catalogues']['SKU']==case['actual_composite_catalogue'],
            'DE_SKU_EXACT_LAYER_CATALOGUES_REQUIRED')
    context_catalog.validate(case['actual_composite_catalogue'],case['actual_context55'])
    require(len(case['current_eight_hook_rows'])==8 and all(len(row)==19 for row in case['current_eight_hook_rows'].values()),
            'DE_SKU_EXACT8_CURRENT_HOOK_ROWS_REQUIRED')
    require(len(case['actual_raw_context_authority']['relations'])==55,'DE_SKU_FULL_RAW_RELATION_ACL_REQUIRED')
    privileges=case['actual_raw_context_authority']['effective_role_table_privileges']
    expected={(role,table,p)for role in case['actual_composite_catalogue']['roles']
        for table in case['actual_context55']['names']for p in('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')}
    require(len(privileges)==len(expected)and{tuple(row[:3])for row in privileges}==expected
        and all(type(row[3])is bool for row in privileges),'DE_SKU_COMPLETE_EFFECTIVE_ROLE_PRIVILEGE_MATRIX_REQUIRED')
    require(package.get('run_identity',{}).get('tool_head')==head and package['run_identity']['github_sha']==head,
            'DE_SKU_ACTUAL_PACKAGE_HEAD_CHANGED')
    require(set(package.get('gate',{}))==GATES and all(v is True for v in package['gate'].values()),'DE_SKU_COMPLETE_ALL5_REQUIRED')
    require(package.get('auth_users_before')==package.get('auth_users_after')==0,'DE_SKU_AUTH_RESIDUE')
    return dict(status='ACTUAL_D1_E_SKU_PARENT_CATALOGUE_PREUSE_AND_ALL5_QUALIFIED',
        head=head,actual_context_tables=55,actual_hook_rows=8,actual_Native_cases=0,
        actual_business_cases=0,global_bridge_qualified=False,full_final_composite_qualified=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=ROOT/'cp6-proof/t3');args=parser.parse_args()
    names=('CP7_D1_E_SKU_PARENT_CATALOGUE.json','T3_PACKAGE_INSTALL.json')
    raws=[(args.directory/name).read_bytes()for name in names]
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    result=checked(*(json.loads(raw)for raw in raws),head)
    result['originals']={name:dict(bytes=len(raw),sha256=sha256(raw).hexdigest())for name,raw in zip(names,raws)}
    (args.directory/'DE_SKU_PARENT_CATALOGUE_GATE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))
