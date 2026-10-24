"""Three explicit successors: same financial oracles after lawful prerequisites."""
from datetime import timedelta
from pathlib import Path
import ast,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(HERE))
import prerequisites,cash_oracle,wash_oracle

spec=importlib.util.spec_from_file_location('ready3_original_crossflow',REPO/'scripts/current-cp6-crossflow-qualification/cases.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
IDS=('CURRENT_VENDOR_PAYMENT_LINKED_INVERSE_READY','CURRENT_VENDOR_PAYMENT_DATE_DETECTOR_READY','CURRENT_FAILED_WASH_CHRONOLOGY_READY')
LEGACY_IDS=dict(zip(IDS,('CASH_LINKED:1','CASH_LINKED:4','H_R02')))


def function_source(path,name):
    text=path.read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name)
    return '\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])+'\n'


def declared_cases():
    transforms=json.loads((HERE/'TRANSFORMS.json').read_bytes())['functions']
    assert len(transforms)==5
    for item in transforms:
        raw=function_source(REPO/item['source'],item['function'])
        if item['old']:
            assert raw.count(item['old'])==1
            raw=raw.replace(item['old'],item['new'])
        assert function_source(HERE/item['file'],item['function'])==raw,('ORIGINAL_BUSINESS_ORACLE_CHANGED',item)
    actual={name for name,_ in original.original.phase_cases('crossflow')}
    assert set(LEGACY_IDS.values())<=actual
    return IDS


def cases(cur,today,*,current,evidence):
    declared_cases()
    # Same original seed, attendance reservation and three-day clock preparation.
    original.cases(cur,today,current=current,evidence=evidence)
    day=today-timedelta(days=3);result=[]
    for name in IDS:
        def run(n=name):
            refill=original.attendance.fill_for_other_case(cur,day)
            first=len(prerequisites.EVIDENCE);funded=None
            if n.startswith('CURRENT_VENDOR_PAYMENT'):
                original.original.actors.admin(cur)
                cash=cur.execute('select id from erp.cash_accounts where is_active order by id limit 1').fetchone()[0]
                funded=prerequisites.fund_payment_bank(cur,cash)
                fn=cash_oracle.lifecycle if n==IDS[0]else cash_oracle.detector_fault
                row=fn(cur,cash,'VENDOR_PAYMENT')
                assert row['status']=='CONTROL_PASS',row
            else:
                row=wash_oracle.case_r02(cur);assert row['status']=='PASS',row
            links=prerequisites.EVIDENCE[first:];assert len(links)==1
            return dict(status='PASS',original_result=row,represented_legacy_id=LEGACY_IDS[n],
                seed_gap_refill=refill,explicit_Native_payroll_prerequisite=links[0],fixture_capital=funded,
                unchanged_date_money_READY_and_corruption_oracles=True,legacy_failure_relabelled=False)
        result.append((name,run))
    return result
