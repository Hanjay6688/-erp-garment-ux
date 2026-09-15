"""Require complete AB native evidence before extending the final manifest."""
import json

from cp6_v2620ab_audit_wave import GROUPS, validate_wave


def extend_manifest(proof, manifest, head):
    def read(name):
        result = json.loads((proof / name).read_text())
        assert result['head'] == head, name
        return result
    waves = {}
    for phase, folder in (('AA_AUDIT', 'independent-aa'), ('AB_REGRESSION', 'independent-ab')):
        reports = {name: read(folder + '/' + spec[1]) for name, spec in GROUPS.items()}
        counts = validate_wave(phase, reports, head)
        wave = read(folder + '/AB_AUDIT_WAVE.json')
        expected = 'EXPECTED_PREDECESSOR_COUNTEREXAMPLES_REPRODUCED' if phase == 'AA_AUDIT' else 'PASS_BOUNDED_REGRESSION'
        assert wave['status'] == expected and wave['phase'] == phase
        assert all(wave[key] == value for key, value in counts.items())
        assert all(wave['groups'][name]['exit_code'] == (1 if report['counterexamples'] else 0)
                   for name, report in reports.items())
        waves[phase] = dict(report=folder + '/AB_AUDIT_WAVE.json', **counts)
    material = read('independent-ab/AB_MATERIAL_DAY_REGRESSION.json')
    close = read('independent-ab/AB_CLOSE_REGRESSION.json')
    for report, count, incomplete in ((material, 8, 'incomplete_attempted_cases'), (close, 20, 'incomplete_cases')):
        assert report['status'] == 'PASS_BOUNDED_AUDIT' and report['runtime_generation'] == 'AB'
        assert report['controls_passed'] == len(report['cases']) == count
        assert report['qualified_counterexamples'] == report[incomplete] == 0
        assert report['entire_unseeded_runtime_restored'] and report['schema_usage_restored']
        assert len(report['verified_ab_functions']) == 5
        assert all(c['status'] == 'CONTROL_PASS' and c['full_boundary_restored'] for c in report['cases'].values())
    install = read('CP6_V2620AB_INSTALL_QUALIFICATION.json')
    runtime = read('V2620AB_INSTALLED_RUNTIME.json')
    guards = read('CP6_V2620AB_ROLLBACK_GUARDS.json')
    restore = read('V2620AB_COMPLETE_AA_RESTORE.json')
    for report in (install, runtime, guards, restore):
        assert report['status'] == 'PASS' and report['production_go'] is False
    assert install['expected_cases'] == len(install['cases']) == 26
    assert install['entire_unseeded_runtime_restored'] and install['schema_usage_restored']
    assert all(c['status'] == 'CONTROL_PASS' and c['attempt_boundary_exact']
               and c['full_boundary_restored'] and c['ab_capsule_absent'] for c in install['cases'].values())
    assert sum(c['refused'] for c in install['cases'].values()) == 25
    assert install['cases']['LAWFUL_CHECKPOINT_HISTORY_ACCEPTED']['installed_five_functions_owner_acl_exact']
    assert len(runtime['functions']) == 5 and runtime['boundary_count'] == 213
    assert guards['rollback_sha256'] == '5602fefc1b29935ccfb485635ec14e6fdea7468bd726ed440d6c5d93d12b1262'
    assert len(guards['guards']) == 8 and all(c['status'] == 'PASS' and c['expected_rejection_observed'] for c in guards['guards'])
    assert len(guards['extra_object_preflight_guards']) == 22
    assert all(c['status'] == 'PASS' and not c['admission_closed'] and not c['rollback_started']
               for c in guards['extra_object_preflight_guards'])
    assert guards['trusted_capsule_guard']['status'] == 'PASS'
    assert not guards['trusted_capsule_guard']['admission_closed'] and not guards['trusted_capsule_guard']['rollback_started']
    assert guards['exact_pre_use_restore'] == dict(generation='AA', restored_function_count=5, owner_acl_exact=True, metadata_schema_residue=0)
    assert guards['maintenance']['rollback_committed'] and guards['maintenance']['admission_reopened_after_success']
    assert restore['complete_function_count'] == 533 and restore['definitions_owners_acls_exact']
    assert restore['full_table_boundary_exact'] and restore['restored_table_count'] == 215
    carry_path = proof / 'CP6_AB189_MATRIX_CARRY_FORWARD.json'
    matrix_carry = None
    if carry_path.exists():
        matrix_carry = read('CP6_AB189_MATRIX_CARRY_FORWARD.json')
        assert matrix_carry['status'] == 'QUALIFIED_PREDECESSOR_EVIDENCE_CARRIED_FORWARD'
        assert matrix_carry['predecessor_head'] == 'e2aa399cfc787d848c1f136e8e563c5304d09a87'
        assert matrix_carry['predecessor_tree'] == '5bddd7add3296f27087ed30062c998bf20e53ac1'
        schedules = json.loads(
            (proof / 'H_MAINTENANCE_ROLLBACK/manifest.json').read_text()
        )
        assert schedules['head'] == matrix_carry['predecessor_head']
        assert matrix_carry['manifest_sha256'] == matrix_carry['observed_manifest_sha256']
    else:
        schedules = read('H_MAINTENANCE_ROLLBACK/manifest.json')
    assert schedules['status'] == 'PASS' and len(schedules['cases']) == 460
    assert schedules['writer_first_body_entry'] == dict(expected=115, observed=115, compilation_only_contexts=0)
    assert len([c for c in schedules['cases'] if c['target'] == 'AB' and c['status'] == 'PASS']) == 20
    manifest['audited_predecessor'] = dict(
        head='7d824f780fa06fc16385c347759a9b96d0138e9d', tree='0bfda3d552a3a3c37b4563d895a9eb387f64acb4',
        independent_run=34883270346, audit_checkout='86351dbc11e5525e35c645178776c2f7dae955f6',
        competition_verdict='FAIL_P2_RECOST_AND_LONG_TRANSACTION_BUSINESS_DAY',
        historical_qualified_counterexamples=6, historical_controls=17, historical_incomplete=0,
        current_before_regression=waves['AA_AUDIT'], previous_audit_chain=manifest['audited_predecessor'])
    manifest['ab_operational_clock_closure'] = dict(
        before=waves['AA_AUDIT'], after=waves['AB_REGRESSION'], functions=5,
        inherited_material_cases_under_ab=8, inherited_close_cases_under_ab=20,
        atomic_install_cases=26, refusal_cases=25, lawful_checkpoint_history_control=1,
        boundary_tables=213, complete_aa_restore=533, restored_tables=215,
        direct_rollback_guards=8, extra_rollback_guards=22, maintenance_schedules=460,
        maintenance_matrix_evidence=(
            'AB_NATIVE_189_CARRY_FORWARD' if matrix_carry else 'CURRENT_RUN'
        ),
        writer_first_body_entries=115, command_clock='statement_timestamp',
        single_statement_midnight_crossing_proven=False, overnight_soak_proven=False,
        new_wave_http_ui_reachability_proven=False,
        remaining_coverage=['other linked payment, return and opening-balance paths',
                            'other authorization and search_path paths', 'orphan codes and complete HTTP/UI lifecycles'])
    manifest['proof_contract']['final_runtime'] += '+v2.6.20ab'
    manifest['competition_verdict'] = 'WRITER_PASS_PENDING_EXPANDED_INDEPENDENT_AUDIT'
    manifest['independent_acceptance_complete'] = False
    manifest['production_go'] = False
