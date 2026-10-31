"""Read-only root intake of the qualified, unchanged S03 Native14 backend."""
from pathlib import Path
from hashlib import sha256
import argparse,json
from intake_common import GitBytes,exact,fields,pin,require,original_zip
from intake_sku27 import strict,literal,group,declared_files,full_census,PACKAGE,FILES,RESTORE

HEAD='3c0c5defe55e48cf6f221c868594dd6676d17170'
TREE='ca20c918201b455ad09df489829b83b9e6afea95'
MAIN='CP7_S03_ATTENDANCE_CHOICE_NATIVE14.json'
CASE='S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE'
NATIVE='CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json'
READER='CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json'
ARCHIVE=dict(bytes=8472775,sha256='567e64545493d4806fa613b1306b4fe8c2f70a2ebb327fc60b709737813e5a60')
PINS={
 MAIN:dict(bytes=78242045,sha256='15d08eb136c46e74ecf814b2256cc12b0a1df2b29fbc27a1296c3100fc2bafb5'),
 PACKAGE:dict(bytes=360433,sha256='0663c1140bd2877ef3859b4e34bb773aaaf15e2f3b4217e48a8df66c1c436c77'),
 FILES:dict(bytes=1806,sha256='14007d43dd9b8e1acfa2b91e35d59047f553b248e2fc06e8362e8ad813003ba7'),
 RESTORE:dict(bytes=1470,sha256='3883ec7b222e13badb22f5db7d9fabf563bf99b90dbf5d724a00c3ec40315091'),
 NATIVE:dict(bytes=19498,sha256='105e371726cdacd86900d7f086a4262450801c7606852a7711856b0ff06667dd'),
 READER:dict(bytes=13062,sha256='70b618aa40062eaa839a55f2edeb647ea1fe2c520840f5cca85c194df17668b7'),
}


def intake(root,archive):
    with GitBytes(root,HEAD,TREE)as g,original_zip(archive,ARCHIVE,119)as z:
        docs={}
        for name,expected in PINS.items():
            raw=z.read(name);exact(pin(raw),expected,'EXACT_QUALIFIED_RAW_ORIGINAL:'+name);docs[name]=strict(raw)
        source_raw=g.read('scripts/current-s03-lawful-fixture-successor-qualification/SOURCE.json')
        exact(pin(source_raw),dict(bytes=106705,sha256='ba59dee4ae71c62df2b2e35c558cb23a7c66254a974c554cc3d17d63b936c555'),'EXACT_SOURCE475_MANIFEST')
        source=strict(source_raw);exact(len(source['files']),475,'EXACT_475_SOURCE_PINS')
        for name,expected in source['files'].items():g.verify_pin(name,{key:expected[key]for key in('bytes','sha256')})
        main=docs[MAIN];part=main['committed'][CASE]
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
            actual_Native_cases=14,actual_business_cases=14,actual_browser_cases=0,actual_Auth_HTTP_cases=0,
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
            baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
            production_go=False,independent_acceptance=False),'EXACT_ACTUAL_NATIVE14_AND_RESTORE')
        exact(set(main['committed']),{CASE},'ONE_CURRENT_NATIVE14_COMPONENT')
        fields(part,dict(status='PASS',actual_Native_cases=14,used_guard_refused_before_DDL=True,
            original_accrual_and_source_binding_unchanged=True,both_groups_same_actual_installation=True,
            reader3_requires_actual_fresh_original11=True,combined_strict14_fabricated=False,
            source_derived_ABI_is_actual_runtime_capture=False),'ACTUAL_FRESH14_AND_REAL_USED_INVERSE')
        ids=list(literal(g,'scripts/current-attendance-period-choice-qualification/cases.py','IDS'))
        readers=list(literal(g,'scripts/current-attendance-period-choice-readers-qualification/cases.py','IDS'))
        exact([len(ids),len(readers)],[11,3],'EXACT_TWO_STRICT_GROUPS')
        exact(part['native'],docs[NATIVE],'RAW_NATIVE11_EQUALS_EMBEDDED');group(docs[NATIVE],ids)
        exact(part['reader_native3'],docs[READER],'RAW_READER3_EQUALS_EMBEDDED');group(docs[READER],readers)
        capture=part['actual_installed_capture'];delta={}
        exec(compile(g.read('scripts/cp7_attendance_period_choice/native_delta.py'),'qualified_native14_pure_deriver','exec'),delta)
        exact(set(capture['originals']),set(delta['SIGNATURES']),'ACTUAL_FIFTEEN_CAPTURE_IDENTITIES')
        exact(capture['definitions'],delta['patched'](capture['originals']),'EXACT_FIFTEEN_ACTUAL_SOURCE_DERIVATIONS')
        exact(capture['clones'],delta['clones'](capture['originals']),'EXACT_TWO_ACTUAL_NATIVE_CLONES')
        before=part['used_inverse_refusal_before'];after=part['used_inverse_refusal_after']
        exact(before,after,'USED_REFUSAL_FULL22_ALL_ROWS_ALL_SEQUENCES_ZERO_EFFECT')
        census=full_census(before['actual_all22'],before['full_data_and_sequences'])
        fields(part['strict_group_scope'],dict(all_current_business_rows_restored=True,actual_all22_restored=True,
            sequence_reseed_performed=False,complete_sequence_restore_proved=False),'STRICT_ROLLBACK_NO_SEQUENCE_RESTORE_INVENTED')
        package=docs[PACKAGE];exact(package['gate'],dict(installed=True,primary_unchanged=True,backup_restore_drill=True,
            security_advisors=True,writer_runtime=True),'ALL_FIVE_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id='40983410165',run_attempt='1'),'EXACT_NATIVE14_RUN')
        fields(docs[RESTORE],dict(status='RESTORED_IDENTICAL'),'COMPLETE_BACKUP_DRILL')
        require(all(type(v)is bool and v for v in docs[RESTORE]['checks'].values()),'EVERY_TYPED_RESTORE_CHECK')
        exact(docs[RESTORE]['data']['differ'],{},'NO_BACKUP_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'EXACT_OUTER_ROLE_RESTORE')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True),'EXACT_OUTER_RESTORE')
        source_maps=declared_files(g,main['source_declaration']['current_installation'])
        return dict(status='ROOT_VERIFIED_QUALIFIED_S03_NATIVE14_ALL5',head=HEAD,tree=TREE,run_id=40983410165,
            job_id=123828634300,artifact_id=12947563874,archive=dict(ARCHIVE,members=119),originals=PINS,
            exact_source_pins=475,source_manifest=pin(source_raw),actual_product_source_maps=source_maps,
            actual_case_ids=ids+readers,strict_group_counts=[11,3],actual_captures=15,actual_clones=2,
            used_refusal_raw_full_boundary=census,actual_used_refusal_full22_rows_ALL_sequences_equal=True,
            complete_native14_qualified=True,package_all_five=True,package_gates=package['gate'],
            prior_runs_aggregated=False,outer_raw_before_after_not_serialized=True,outer_restore_source_bound_receipts=True,
            original_data_reused_not_new_Native_execution=True,current_S03_browser4_result_required_for_separate_qualification=True,
            fresh_composite_case_credit=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('source','archive','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=intake(args.source,args.archive);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','strict_group_counts','complete_native14_qualified','package_all_five')}))
