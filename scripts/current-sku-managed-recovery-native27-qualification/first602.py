"""The complete original602 first-red reports remain negative prerequisites."""
from hashlib import sha256
from pathlib import Path
import gzip
import json

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'scripts/current-sku-managed-recovery-preflight/evidence'

def verified():
    manifest=json.loads((FOLDER.parent/'SOURCE.json').read_bytes());values={}
    for name in('CP7_SKU_ALL_MEMBER_NATIVE23.json','CP7_SKU_PAIR_CONVERSION_NATIVE7.json','CP7_SKU_GROUP_COST_NATIVE3.json',
                 'T3_PACKAGE_INSTALL.json','T3_PACKAGE_FILES_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json'):
        path=FOLDER/('FIRST_602_'+name+'.gz');pin=manifest['files'][str(path.relative_to(ROOT))]
        packed=path.read_bytes();assert len(packed)==pin['bytes']and sha256(packed).hexdigest()==pin['sha256']
        values[name]=json.loads(gzip.decompress(packed))
    main=values['CP7_SKU_ALL_MEMBER_NATIVE23.json'];core=values['CP7_SKU_PAIR_CONVERSION_NATIVE7.json'];cost=values['CP7_SKU_GROUP_COST_NATIVE3.json']
    assert main['status']=='INCOMPLETE'and core['counts']=={'PASS':7}and cost['counts']=={'PASS':2,'INCOMPLETE':1}
    failure=cost['cases']['SKU29_COST_GROUP_RETURN_OVER_FIRST_PART_SAFETY_REFUSAL_ONLY']
    assert failure['status']=='INCOMPLETE'and'SKU_COST_CURRENT_CENSUS_CHANGED'in failure['error']
    assert"'data_or_sequences': ['sequence:erp.audit_logs_id_seq']"in failure['error']
    assert main.get('used_guard_refused_before_DDL')is None
    package=values['T3_PACKAGE_INSTALL.json'];assert package['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    assert package['auth_users_before']==package['auth_users_after']==0
    for key in('baseline_full22_all_rows_all_sequences_equal','restore_raw_public_equal','cp6_restored','baseline_advisors_equal','advisor_gate'):assert main[key]is True
    assert values['T3_BACKUP_RESTORE_DRILL.json']['status']=='RESTORED_IDENTICAL'
    return dict(status='ORIGINAL602_9PASS_1INCOMPLETE_RETAINED_NO_FRESH_CREDIT',run=40961419818,artifact=12937998996,
      archive_sha256='698b90b0bc3dfa52a8339d0b30464c2d98721594e56abdd53b07c959223f2bcc',
      failed_native_guard_sequence_values=dict(before=['1317',True],after=['1322',True]),
      exact_Native_message_not_retained_only_code_asserted=True,outer_used_guard='ABSENT_NOT_QUALIFIED',
      core7_pass_cost2_pass_cost1_incomplete=True,downstream13_not_reached=True,usable_runtime_prerequisite=False,
      all22_data_sequences_roles_CP6_advisors_Auth_restored=True,writer_runtime=False)
