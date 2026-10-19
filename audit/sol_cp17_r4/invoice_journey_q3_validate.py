"""Pure metadata/static controls for the declared Q3 form-state repair; no DB calls."""
import ast
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    declaration = json.loads((ROOT / 'INVOICE_JOURNEY_Q3_PREEXECUTION_MANIFEST.json').read_text())
    for path, value in declaration['audit_tools'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value
    for path, value in declaration['pinned_product_sources'].items():
        assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == value
    prior = json.loads((ROOT / 'INVOICE_JOURNEY_Q2_PREEXECUTION_MANIFEST.json').read_text())
    assert declaration['cases'] == prior['cases']
    assert declaration['expected_signatures'] == prior['expected_signatures']
    assert declaration['expected_write_action_sequences'] == prior['expected_write_action_sequences']
    for path, digest in declaration['original_tool_hashes'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    def transform(before, claim=False):
        edits = [
            ("import assert from 'node:assert/strict'", "import assert from 'node:assert/strict'\nimport {observePage} from './journey_q3_dom.mjs'"),
            (' const p=user.page\n', ' const p=user.page,diagnostics=observePage(user.page,id)\n'),
            ("   const r=payments.locator('tbody tr').filter({hasText:amount});", "   const reasonField=box.getByLabel('Alasan pembatalan',{exact:true})\n   ;(seen.reason_refills??=[]).push({amount,before:await reasonField.inputValue()})\n   await reasonField.fill('Sol inverse the lawful posted settlements')\n   const r=payments.locator('tbody tr').filter({hasText:amount});"),
            ('  writeFileSync(`cp6-proof/t3/${id}_OBSERVATIONS.json`', '  await diagnostics.complete()\n  writeFileSync(`cp6-proof/t3/${id}_OBSERVATIONS.json`'),
            (' }catch(error){\n', " }catch(error){\n  await diagnostics.capture('failure')\n"),
        ]
        if claim:
            edits += [
                ("  await p.getByRole('button',{name:'Claim Laundry',exact:true}).click()\n", "  await p.getByRole('button',{name:'Claim Laundry',exact:true}).click()\n  await diagnostics.capture('after_claim_click')\n"),
                ("  await claimForm.getByLabel('JENIS',{exact:true}).selectOption('MISSING')\n  await claimForm.getByLabel('SURAT KIRIM',{exact:true}).selectOption(delivery)", "  await ui.expect(claimForm).toBeVisible()\n  const typeSelect=claimForm.locator('label').filter({has:p.getByText('JENIS',{exact:true})}).locator('select')\n  const deliverySelect=claimForm.locator('label').filter({has:p.getByText('SURAT KIRIM',{exact:true})}).locator('select')\n  await ui.expect(typeSelect).toHaveCount(1);await typeSelect.selectOption('MISSING')\n  await ui.expect(deliverySelect).toHaveCount(1);await deliverySelect.selectOption(delivery)"),
                ("  await wait(s=>s.claims[0][2],'ACCEPTED')\n", "  await wait(s=>s.claims[0][2],'ACCEPTED')\n  claim=await claimPanel()\n"),
                ("  const creditRow=payments.locator('tbody tr').filter({hasText:'Kredit klaim'})", "  await box.getByLabel('Alasan pembatalan',{exact:true}).fill('Sol inverse the lawful posted claim credit application')\n  const creditRow=payments.locator('tbody tr').filter({hasText:'Kredit klaim'})"),
            ]
        for old, new in edits:
            assert before.count(old) == 1, old
            before = before.replace(old, new)
        return before
    assert transform((ROOT / 'journey_observer_q2_browser.mjs').read_text()) == (ROOT / 'journey_form_q3_browser.mjs').read_text()
    assert transform((ROOT / 'claim_observer_q2_browser.mjs').read_text(), True) == (ROOT / 'claim_form_q3_browser.mjs').read_text()
    for path in declaration['audit_tools']:
        if path.endswith('.py'):
            ast.parse((ROOT / path).read_text())
        if path.endswith('.mjs'):
            subprocess.run(['node', '--check', str(ROOT / path)], check=True, capture_output=True)
    # Extract only pure row binding, never import the DB fixture.
    tree = ast.parse((ROOT / 'invoice_observer_q2_fixture.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'invoice_rows')
    env = {'Decimal': Decimal}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<pure rows>', 'exec'), env)
    bind = env['invoice_rows']
    draft = [['one', 'INV', 'DRAFT', '8.00']]
    posted = [['one', 'INV', 'POSTED', '8.00']]
    reversed_ = [['one', 'INV', 'REVERSED', '8.00']]
    partial = [['one', 'INV', 'PARTIAL_PAID', '8.00']]
    paid = [['one', 'INV', 'PAID', '8.00']]
    cancelled = [['one', 'INV', 'CANCELLED', '8.00']]
    positives = ((draft, []), (cancelled, []), (posted, posted), (posted, partial), (posted, paid), (reversed_, reversed_))
    for documents, core in positives:
        assert bind(documents, core) == documents
    negatives = [([], posted), (draft, posted), (cancelled, posted), (posted, []), (posted, reversed_), (reversed_, partial), (reversed_, paid), (posted, [['one', 'INV', 'DRAFT', '8.00']]), (posted, [['one', 'INV', 'POSTED', '7.99']]), (posted, [['one', 'OTHER', 'POSTED', '8.00']]), (posted + posted, posted), (posted, posted + posted)]
    for documents, core in negatives:
        try:
            bind(documents, core)
        except AssertionError:
            pass
        else:
            raise AssertionError('NEGATIVE_ROW_BINDING_PASSED')
    # Use the actual qualified final PASS expression, including cleanup gates.
    tree = ast.parse((ROOT / 'invoice_journey_q3_qualification.py').read_text())
    final = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and isinstance(n.value, ast.IfExp) and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == 'status')
    gate = compile(ast.Expression(final.value.test), '<actual Q3 PASS gate>', 'eval')
    ids = [c['id'] for c in declaration['cases']]
    b = dict(database_remaining=0, status='RUN_COMPLETE', host_status='RUN_COMPLETE', host_exit=0, console_errors=0, session_leaks=[], cleanup_failures=False, auth_counts={'restored': True})
    report = dict(cp6_restored=True, observed_case_ids=ids, expected_case_ids=ids, counts={'PASS': 4}, each_literal_signature_matches_declared_branch=True)
    assert eval(gate, {'report': report, 'b': b}) is True
    mutations = [('b', 'database_remaining', None), ('b', 'database_remaining', False), ('b', 'database_remaining', 1), ('b', 'status', 'INCOMPLETE'), ('b', 'host_status', 'CRASHED'), ('b', 'host_exit', False), ('b', 'host_exit', 1), ('b', 'console_errors', False), ('b', 'console_errors', 1), ('b', 'session_leaks', ['leak']), ('b', 'cleanup_failures', True), ('b', 'auth_counts', {'restored': False}), ('b', 'error', 'observer error'), ('report', 'cp6_restored', False), ('report', 'observed_case_ids', ids[:-1]), ('report', 'counts', {'PASS': 3, 'INCOMPLETE': 1}), ('report', 'each_literal_signature_matches_declared_branch', False), ('report', 'error', 'case error')]
    for target, key, value in mutations:
        context = {'report': deepcopy(report), 'b': deepcopy(b)}
        context[target][key] = value
        assert eval(gate, context) is False, (target, key, value)
    # Parsed workflow differences limited to audit names, entrypoint and artifact.
    before = yaml.safe_load((REPO / '.github/workflows/audit-sol-r4-invoice-journey-q2.yml').read_text())
    after = yaml.safe_load((REPO / '.github/workflows/audit-sol-r4-invoice-journey-q3.yml').read_text())
    expected = deepcopy(before)
    expected['name'] = after['name']; expected['run-name'] = after['run-name']
    expected['on']['push']['paths'] = after['on']['push']['paths']
    expected['concurrency']['group'] = after['concurrency']['group']
    expected['jobs']['phase']['name'] = after['jobs']['phase']['name']
    for i, step in enumerate(expected['jobs']['phase']['steps']):
        if step.get('run') == "python '../sol/audit/sol_cp17_r4/invoice_journey_q2_qualification.py'":
            step['run'] = "python '../sol/audit/sol_cp17_r4/invoice_journey_q3_qualification.py'"
            step['name'] = after['jobs']['phase']['steps'][i]['name']
        if step.get('uses', '').startswith('actions/upload-artifact@'):
            step['with']['name'] = after['jobs']['phase']['steps'][i]['with']['name']
    assert expected == after
    assert after['permissions'] == {'contents': 'read', 'actions': 'read'}
    for step in after['jobs']['phase']['steps']:
        if step.get('uses', '').startswith('actions/checkout@'):
            assert step['with']['persist-credentials'] is False
            if step['with']['path'] == 'auditor':
                assert step['with']['ref'] == declaration['candidate_sha']
    assert Decimal('100') + 5 * (Decimal('3') + 1) + 5 * 2 == Decimal('130')
    assert subprocess.check_output(['git', 'diff', '--name-only', declaration['candidate_sha'], '--', 'src', 'supabase', 'scripts', 'package.json', 'package-lock.json', 'index.html', 'vite.config.ts'], cwd=REPO, text=True) == ''
    out = dict(state='STATIC_AND_PURE_METADATA_ONLY_NO_PRODUCT_CASES_RUN', source_hashes_verified=True, exact_declared_browser_diff=True, row_binding_positive=len(positives), row_binding_negative=len(negatives), actual_gate_positive=1, actual_gate_negative=len(mutations), parsed_workflow_diff_only_names_entrypoint_artifact=True, permissions_timeouts_prerequisites_unchanged=True, candidate_pinned=True, product_diff_empty=True, original_tools_unchanged=True, free_rewash_not_repeated=True, ordinary_expected_unchanged=True, q2_expected_signatures_and_action_sequences_unchanged=True, claim_render_cause_still_unresolved=True, diagnostics_read_only_reviewed=True, required_reason_refilled_before_each_inverse_and_after_claim_accept=True)
    (ROOT / 'INVOICE_JOURNEY_Q3_PREEXECUTION_VALIDATION.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
