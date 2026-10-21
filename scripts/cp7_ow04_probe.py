"""OW04 first integrated Native qualification, on disposable CP6 copies only.

Predeclared: 12 explicit CREDIT/REFUND cases, all 11 unchanged P11 return
controls, all 8 unchanged P11 read/Native source controls, and E01 (32 Native).
An explicit --native-empty mode adds12 declared direct-Native cases atomically.
--fractional-hpp reruns those44 plus14 independently frozen HPP cases (58).
--signed-source reruns those58 plus five frozen source-inverse cases (63).
No mode claims browser, race, complete OW04, or production acceptance.
"""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import traceback

import psycopg
import cp7_f05_analysis_probe as predecessor
import cp7_restore_state as restore_state
import cp7_sales_return_cases as retained_returns
import cp7_sales_cases as retained_reads
import cp7_f03_e01_cases as retained_e01
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors, advisor_delta

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path[:0] = [str(HERE / 'cp7_customer_credit/initial-settlement'), str(HERE / 'cp7_customer_credit/native'),
               str(HERE / 'cp7_customer_credit/native-empty'),
               str(HERE / 'cp7_customer_credit/hpp-fractional'),
               str(HERE / 'cp7_customer_credit/reconciliation/native')]
import cp7_ow04_initial_settlement_cases as initial
from cp7_customer_credit.integration import owning_bundle as credit

p09 = predecessor.p09
package = predecessor.package
native = predecessor.native
SIGNED_SOURCE = '--signed-source' in sys.argv[1:]
FRACTIONAL_HPP = '--fractional-hpp' in sys.argv[1:] or SIGNED_SOURCE
NATIVE_EMPTY = '--native-empty' in sys.argv[1:] or FRACTIONAL_HPP
LABEL = 'CP7_OW04_SIGNED_SOURCE' if SIGNED_SOURCE else 'CP7_OW04_FRACTIONAL_HPP' if FRACTIONAL_HPP else 'CP7_OW04_NATIVE_EMPTY' if NATIVE_EMPTY else 'CP7_OW04_INITIAL'
OUT = p09.bundle.ROOT / ('cp6-proof/t3/'+LABEL+'.json')
RETURN_IDS = tuple('P11_RETURN_' + x for x in ('LIFECYCLE','SPLIT_GRADES','ALLOCATION_CAP','FIELDS',
    'PAID_REFUSAL','DATE_LOCATION','REPLAY','SOURCE_CHANGE','PERMISSIONS','PAGES','CONSUMED'))
READ_IDS = tuple('P11_READ_'+x for x in ('DRAFT_CANCEL','NATIVE_LIFECYCLE','EXACT_CENTS',
    'FINANCIAL_REDACTION','PRIVATE_READ_ONLY','COMPLETE_PAGES','QUERY_REFUSAL','EMPTY_MISSING'))
BASE_IDS = tuple(initial.NATIVE_IDS) + RETURN_IDS + READ_IDS + ('F03_E01_NATIVE_60_TO_CASH_RETURN',)
assert len(BASE_IDS) == len(set(BASE_IDS)) == 32
if NATIVE_EMPTY:
    import cp7_ow04_native_empty_cases as empty_cases
if FRACTIONAL_HPP:
    import cp7_ow04_fractional_hpp_cases as fractional_hpp
if SIGNED_SOURCE:
    import cp7_ow04_signed_source_cases as signed_source
    import cp7_ow04_signed_zero_difference_cases as signed_zero
IDS = BASE_IDS + (empty_cases.IDS if NATIVE_EMPTY else ()) + (fractional_hpp.IDS if FRACTIONAL_HPP else ()) + \
    (signed_source.IDS + (signed_zero.CASE_ID,) if SIGNED_SOURCE else ())
EXPECTED_COUNT = 63 if SIGNED_SOURCE else 58 if FRACTIONAL_HPP else 44 if NATIVE_EMPTY else 32
assert len(IDS) == len(set(IDS)) == EXPECTED_COUNT
DECLARATION_BYTES = (REPO/('docs/cp7/d17-14/ow04/NATIVE_SIGNED_SOURCE_QUALIFICATION.json' if SIGNED_SOURCE
                         else 'docs/cp7/d17-14/ow04/NATIVE_FRACTIONAL_QUALIFICATION.json' if FRACTIONAL_HPP
                         else 'docs/cp7/d17-14/ow04/NATIVE_EMPTY_QUALIFICATION.json' if NATIVE_EMPTY
                         else 'docs/cp7/d17-14/ow04/NATIVE_INITIAL_QUALIFICATION.json')).read_bytes()
DECLARATION = json.loads(DECLARATION_BYTES)
assert DECLARATION['expected_count']==EXPECTED_COUNT and tuple(DECLARATION['required_case_ids'])==IDS, 'OW04_DECLARED_CASES_CHANGED'
STATE = None
PREDECESSOR_INFO_SCHEMAS = ('cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance',
    'cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material',
    'cp7_supplier_return','cp7_invoice','cp7_receipt_fix')


def predecessor_info_manifest(cur):
    """Exact old default-deny INFO objects, after the raw predecessor verify."""
    return cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname=any(%s::text[])and c.relkind='r'and c.relrowsecurity "
        "and not exists(select 1 from pg_policy p where p.polrelid=c.oid)order by 1,2",
        (list(PREDECESSOR_INFO_SCHEMAS),)).fetchall()


def advisor_disposition(delta, manifest):
    # F05 already classifies this INFO condition as private default denial.
    # Restrict that disposition further to exact objects observed BEFORE OW04;
    # a new OW04 table, different finding, or warning is never explained here.
    existing = set(map(tuple,manifest))
    explained, unexplained = [], []
    for finding in delta.get('added',[]):
        meta = finding.get('metadata') or {}
        old = finding.get('name')=='rls_enabled_no_policy'and finding.get('level')=='INFO' \
            and meta.get('type')=='table'and(meta.get('schema'),meta.get('name'))in existing
        (explained if old else unexplained).append(finding)
    comparable = delta.get('status')in('NO_NEW_FINDINGS','REVIEW_REQUIRED')
    return dict(status='UNEXPLAINED_FINDINGS'if unexplained else
        'NOT_COMPARABLE'if not comparable else
        'ONLY_VERIFIED_PREDECESSOR_INFO'if explained else'NO_NEW_FINDINGS',
        exact_predecessor_info=explained,unexplained=unexplained,
        gate=bool(comparable and not unexplained))


def cases(cur, today):
    selected = initial.cases(cur, today) + retained_returns.cases(cur, today) + retained_reads.cases(cur, today) + retained_e01.cases(cur, today)
    if NATIVE_EMPTY:
        # N04 is an explicitly labelled upgrade fixture: install the exact
        # pre-extension private helpers, run a genuine old Native return, and
        # reapply this same candidate's exact overlays. No financial facts or
        # family ordinals are fabricated. Its case-level rollback restores DDL.
        before = [x['definition'] for x in STATE['native_empty']['before_helpers'].values()]
        selected += empty_cases.cases(cur,today,before_helpers=before,
            reapply_overlay=lambda cursor:cursor.execute(credit._actual_sql('native-empty/04_exact_overlays.sql'),prepare=False))
    if FRACTIONAL_HPP:
        selected += fractional_hpp.cases(cur, today)
    if SIGNED_SOURCE:
        selected += signed_source.cases(cur, today) + signed_zero.cases(cur, today)
    assert tuple(name for name, _ in selected) == IDS, 'OW04_PREDECLARED_CASE_SET_CHANGED'
    return selected


def verify(cur):
    if STATE is None:
        raise RuntimeError('OW04_NO_VERIFIED_INTEGRATED_CANDIDATE')
    exact = credit.verify(cur, STATE)
    # All predecessor checks remain, with the two declared SALES capabilities
    # and exact independent private-inverse composition checked above.
    predecessor.bundle.verify(cur)
    predecessor.payroll.verify(cur, True, True, True, True, True)
    predecessor.finance.verify(cur, customer_credit=True)
    predecessor.f03.journal.verify(cur)
    predecessor.f03.misc.verify(cur)
    predecessor.f03.installment.verify(cur)
    predecessor.f03.transaction_source.verify(cur)
    predecessor.f03.misc_correction.verify(cur)
    predecessor.payment_correction_ownership.verify(cur)
    predecessor.sales_chain_ownership.verify(cur)
    predecessor.f03.cutting_correction.verify(cur)
    return exact


def install_predecessor(cur, report):
    originals, installation = p09.install(cur)
    report['predecessor_installation'] = installation
    before = p09.functions(cur)
    internal = cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
    originals['erp.require_owner_admin()'] = cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
    f03 = predecessor.f03
    f03.note_report.capture(cur, originals)
    sql = '\n'.join((f03.extension(), predecessor.planning.extension(), predecessor.baseline.extension(),
        predecessor.supply.extension(), predecessor.schedule.extension(),
        predecessor.bundle.predecessor.extension(), predecessor.bundle.extension()))
    cur.execute(sql, prepare=False)
    after = p09.functions(cur)
    path = cur.execute('show search_path').fetchone()[0]
    cur.execute("select set_config('search_path','',true)")
    grants = {}
    for principal, signatures in predecessor.bundle.GRANTS.items():
        for sig in signatures:
            key = str(cur.execute('select %s::regprocedure::text',(sig,)).fetchone()[0])
            grants.setdefault(key,set()).add((principal,'EXECUTE',False))
    cur.execute("select set_config('search_path',%s,true)",(path,))
    expected = f03.note_report.expected_definitions(internal,originals,f03.patched_internal,f03.settlement.patched_owner)
    for sig, old in before.items():
        new = after[sig]
        definition = hashlib.md5(expected[sig].encode()).hexdigest() if sig in expected else old['definition']
        assert new['definition'] == definition and new['owner'] == old['owner'], ('OW04_PREDECESSOR_UNDECLARED_CHANGE',sig)
        assert {tuple(x) for x in new['acl'] or []} == {tuple(x) for x in old['acl'] or []} | grants.get(sig,set()), ('OW04_PREDECESSOR_ACL_CHANGE',sig)
    for sig, definition in expected.items():
        assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0] == definition
    p09.INSTALLED_FUNCTIONS = after
    report['predecessor_raw_verification'] = predecessor.verify(cur)
    return originals


def qualification_source_files():
    result = credit.source_files(native_empty=NATIVE_EMPTY)
    if FRACTIONAL_HPP:
        for name in ('EXPECTED.json', 'cp7_ow04_fractional_hpp_cases.py'):
            result['hpp-fractional/'+name] = hashlib.sha256((Path(fractional_hpp.__file__).parent/name).read_bytes()).hexdigest()
    if SIGNED_SOURCE:
        for name in ('EXPECTED.json', 'cp7_ow04_signed_source_cases.py',
                     'ZERO_DIFF_EXPECTED.json', 'cp7_ow04_signed_zero_difference_cases.py',
                     'cli_admission_recheck.py'):
            result['reconciliation/native/'+name] = hashlib.sha256((Path(signed_source.__file__).parent/name).read_bytes()).hexdigest()
    return result


def run():
    global STATE
    report = dict(label=LABEL,status='INCOMPLETE',expected_case_count=EXPECTED_COUNT,
        required_case_ids=list(IDS),production_go=False,independent_acceptance=False,
        feature_complete=False,browser_proven=False,races_proven=False,
        scope='EXPLICIT_SIGNED_SOURCE_INVERSE_AND_UNCHANGED_NATIVE58_REGRESSIONS' if SIGNED_SOURCE
            else 'EXPLICIT_FRACTIONAL_HPP_AND_UNCHANGED_NATIVE44_REGRESSIONS' if FRACTIONAL_HPP
            else 'EXPLICIT_INITIAL_SETTLEMENT_NATIVE_EMPTY_AND_RETAINED_CONTROLS' if NATIVE_EMPTY
            else 'EXPLICIT_INITIAL_NATIVE_SETTLEMENT_AND_UNCHANGED_P11_RETURN_E01_REGRESSIONS',
        source_sha256=qualification_source_files(),
        candidate_commit=subprocess.run(['git','-C',str(REPO),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip(),
        open_contract_blockers=([] if NATIVE_EMPTY else ['DIRECT_NATIVE_NEW_EMPTY_FAMILY_REGISTRATION'])+
            (['UNSUPPORTED_SOURCE_INVERSE_CLASSES','POSITIVE_AND_NEW_COHORT_RECONCILIATION',
              'SIGNED_SOURCE_HTTP_BROWSER_RACE_AND_RECOVERY'] if SIGNED_SOURCE else
             ['CORRECTED_FAMILY_RECONCILIATION','HTTP_BROWSER_RACE_AND_RECOVERY'])+
            ['CREDIT_APPLY_AND_CONSUMER_UNDO'],
        qualification_only=True,predeclared_case_sha256=hashlib.sha256(DECLARATION_BYTES).hexdigest())
    installed = False
    originals = {}
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            restore_before = restore_state.capture(cur,package.boundary.snapshot,predecessor.public_state,p09.functions)
            conn.rollback()
            originals = install_predecessor(cur, report)
            report['verified_predecessor_info_manifest'] = predecessor_info_manifest(cur)
            STATE = credit.install(cur,predecessor.verify,p09.functions,native_empty=NATIVE_EMPTY)
            # The exact target/reader/private/native proof precedes updating
            # the original harness's complete installed-function inventory.
            p09.INSTALLED_FUNCTIONS = p09.functions(cur)
            report['integrated_installation'] = {key:STATE[key] for key in
                ('approval','context_proof','refund_proof','source_sha256')}
            if NATIVE_EMPTY:
                report['native_empty_installation'] = STATE['native_empty']
            report['integrated_source_verification'] = verify(cur)
            conn.commit()
            installed = True
            conn.rollback()
        report['advisors_with_cp7'] = advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True) as catalog:
            report['native'] = native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison'] = catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                    credit.uninstall(cur,STATE)
                    for definition in originals.values(): cur.execute(definition,prepare=False)
                    for role in predecessor.bundle.ROLES:
                        cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
                    conn.commit()
                    report['cp6_restored'] = restore_state.prove(cur,restore_before,
                        package.boundary.snapshot,predecessor.public_state,p09.functions,report)
                    conn.rollback()
                    p09.wip.policy.bf.verified(cur)
                    conn.rollback()
                report['advisor_delta'] = advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition'] = advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate'] = report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group = report.get('native',{})
        report['observed_case_count'] = sum(group.get('counts',{}).values())
        report['required_case_ids_pass'] = set(group.get('cases',{})) == set(IDS)
        if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') \
                and group.get('counts') == {'PASS':EXPECTED_COUNT} and report['required_case_ids_pass'] \
                and group.get('database_remaining',0) == 0:
            report['status'] = 'PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key) for key in ('label','status','expected_case_count',
            'observed_case_count','cp6_restored','advisor_gate','error','traceback','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,feature_complete=False)


if __name__ == '__main__':
    if sys.argv[1:] not in ([],['--native-empty'],['--fractional-hpp'],['--signed-source']):
        raise SystemExit('Only explicit --native-empty, --fractional-hpp or --signed-source qualification options are supported')
    package._writer_runtime = lambda browser_mode=False:run()
    package.run('install')
