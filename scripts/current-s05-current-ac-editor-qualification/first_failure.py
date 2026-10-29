"""Exact cdbdea Original is negative evidence, never a successful prerequisite."""
from hashlib import sha256
from pathlib import Path
import io
import json
import zipfile

HERE = Path(__file__).resolve().parent
ZIP_BYTES = 2064935
ZIP_SHA = '8416f603ed401076293b1f91a9ff3db21f1bf0477147efb7cf012b45e244c0fc'


def checked(here=HERE):
    raw = (Path(here)/'retained-cdbdea/ORIGINAL.zip').read_bytes()
    if len(raw) != ZIP_BYTES or sha256(raw).hexdigest() != ZIP_SHA:
        raise ValueError('S05_CDBDEA_FIRST_ORIGINAL_ARCHIVE_CHANGED')
    with zipfile.ZipFile(io.BytesIO(raw)) as original:
        names = original.namelist()
        if len(names) != 114 or len(set(names)) != 114 or original.testzip() is not None:
            raise ValueError('S05_CDBDEA_EXACT_ORIGINAL_MEMBERS_OR_CRC_CHANGED')
        reports = {name: json.loads(original.read(name)) for name in (
            'CP7_S05_ACCESSORY_STANDARD_NATIVE10.json', 'CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES.json',
            'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json')}
    main = reports['CP7_S05_ACCESSORY_STANDARD_NATIVE10.json']
    cases = reports['CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES.json']
    package = reports['T3_PACKAGE_INSTALL.json']
    child = main['committed']['S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE']
    if (main['qualification_commit'] != 'cdbdea26ef8e4d15bfc16a362c6fad636d961ef2'
            or main['status'] != 'INCOMPLETE' or cases['counts'] != {'INCOMPLETE': 10}
            or len(cases['cases']) != 10 or cases['missing'] != []
            or any(row['status'] != 'INCOMPLETE' or row['error'] != 'S05_EXACT_NATIVE_LEGACY_EDITOR_BODY_REQUIRED'
                   or row['full_boundary_restored'] is not True for row in cases['cases'].values())
            or child['lawful_recipe_fixture']['actual_fixture_master_events'] != []
            or 'separate_committed_business_witness' in child or 'used_guard_refused_before_DDL' in main):
        raise ValueError('S05_CDBDEA_EXACT_FIRST_TEN_ABI_REFUSALS_REQUIRED')
    if (package['gate'] != dict(installed=True, primary_unchanged=True, backup_restore_drill=True,
                               security_advisors=True, writer_runtime=False)
            or package['auth_users_before'] != 0 or package['auth_users_after'] != 0
            or reports['T3_BACKUP_RESTORE_DRILL.json']['status'] != 'RESTORED_IDENTICAL'
            or cases['complete_boundary_restored'] is not True
            or any(main[key] is not True for key in ('baseline_full22_all_rows_all_sequences_equal',
                'restore_raw_public_equal', 'cp6_restored', 'baseline_advisors_equal', 'advisor_gate'))):
        raise ValueError('S05_CDBDEA_FULL_RESTORE_AND_NEGATIVE_PACKAGE_REQUIRED')
    return dict(status='EXACT_CDBDEA_TEN_ABI_INCOMPLETE_RETAINED_NOT_ACCEPTED',
        run_id=40959735086, job_id=123749056356, artifact_id=12936299484,
        archive_bytes=ZIP_BYTES, archive_sha256=ZIP_SHA, members=114, CRC_verified=True,
        counts={'INCOMPLETE': 10}, Native_PASS=0, actual_editor_observed_digest_retained=False,
        actual_fixture_master_events=0, used_witness_reached=False, full_outer_restore=True,
        package_gates=package['gate'], success_prerequisite=False, production_go=False, independent_acceptance=False)
