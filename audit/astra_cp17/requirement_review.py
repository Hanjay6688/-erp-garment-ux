"""Clause-specific evidence routing. A match is a pointer, never an automatic PASS.

Review profiles below were chosen against the actual factory plans and contract
text. Raw results, provenance and gaps remain separate from requirement verdicts.
"""
from pathlib import Path
import json, re, hashlib, collections
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audit/astra_cp17'
REG=ROOT/'docs/cp7/framework-v2/registries'
profiles={}
def profile(key, pattern, sources, focus, limit=''):
    profiles[key]=dict(case_pattern=pattern, sources=sources.split(), review_focus=focus, boundary=limit)

profile('units',r'ACCESSORY_CONNECTED|UOM|COUNT|ROUNDING|PRECISION|DOZEN|D09|D08',
 'scripts/cp6_ar_trial.py scripts/cp6_bc_probe.py scripts/cp6_bc_browser.mjs tests/cp7/SalesPages.dozenHelper.dom.test.tsx',
 'Exact PCS and decimal-money/unit parsing; stale price and posted immutability; real 7-PCS note browser and carried P11 dozen proof.',
 'The retired SALES_MANUAL_13 is supported only by the previously accepted XC2 P11 desktop/phone evidence, not by this DOM test alone.')
profile('accessory',r'^(B0[1-7]:|C0[1-5]:|C09:|C10:|C11:|C12:|D0[5-8]:|D12:|ALL:C0[23]|BC_|DEC0[267]:|REV:LINKED|F[14]:)',
 'scripts/cp6_bc_probe.py scripts/cp6_bc_modes.py scripts/cp6_bc_browser.mjs',
 'Stock custody, usage, inspection, credit and payroll sources remain separate; capacity, exact cents and inverse history checked.')
profile('accessory_race',r'BC_RACE|AR_RACE|ACCESSORY.*(STALE|POSTED|REFUSAL|REPLAY)|BC_HTTP|BC_BROWSER',
 'scripts/cp6_bc_modes.py scripts/cp6_bc_browser.mjs scripts/cp6_ar_trial.py',
 'Two transactions contend for the same native source; current permissions, stable request identity and browser recovery are observed.')
profile('conversion',r'BE0[123]:|BE_RACE|BE_HTTP|BE_BROWSER|CONVERSION|REDYE|R0[789]:|R11:',
 'scripts/cp6_be_probe.py scripts/cp6_be_modes.py scripts/cp6_be_browser.mjs scripts/cp6_bf_combined_modes.py',
 'Conversion/rework/redye uses source stock and actual accessory/service costs once, carries late corrections to descendants, and preserves history.')
profile('opening',r'^(A[139]:|F:|P:|W:|ALL:|W05:)|OPENING|IMPORTED|IMPORT|BB_|PRODUCTION_ORIGIN|PREPAYMENT',
 'scripts/cp6_ba_probe.py scripts/cp6_bb_probe.py scripts/cp6_bb_modes.py scripts/cp6_bb_browser.mjs',
 'Opening import provenance/control totals and supported business continuation; no invented historic transaction and no double opening.')
profile('pocket',r'BE04:|POCKET|BE_.*POCKET',
 'scripts/cp6_be_probe.py scripts/cp6_be_pocket_probe.py scripts/cp6_ar_trial.py',
 'Historical and native pocket sources, numerator/denominator, rounded allocations and recost to WIP/FG/COGS.',
 'Closed-period/date assertions use the explicit owner-approved C6 disposition; old raw statuses are retained.')
profile('laundry',r'T0[2-8]:|T1[23567]:|T2[01234]:|DEC0[1246]:|W05:|D0[79]:|D12:|LAU_T14|BD_|REV:X0[1235]|R13:|CP17-ASTRA-CLAIM-',
 'scripts/cp6_bd_probe.py scripts/cp6_bd_revision_cases.py scripts/cp6_bd_modes.py scripts/cp6_bd_revision_modes.py scripts/cp6_bd_browser.mjs audit/astra_cp17/cases_claim_date.py',
 'Vendor/version/source-specific prices, known subtotal versus unknown total, billable capacity, accrued AP and downstream cost; correction/claim credit follows source.')
profile('laundry_race',r'BD_RACE|BD_HTTP|BD_BROWSER|T32:|REV:X03|REV:X05',
 'scripts/cp6_bd_modes.py scripts/cp6_bd_revision_modes.py scripts/cp6_bd_browser.mjs',
 'Real Auth, overlapping writers, price/version revalidation and desktop/phone mixed-coverage controls; no guessed price.')
profile('recost_close',r'S06:|B04:|P0[147]:|W9:|A6:|AY:|AZ:|G8C0:|RECOST|PERIOD|LATE|AS20C-09',
 'scripts/cp6_aw_probe.py scripts/cp6_ba_probe.py scripts/cp6_ay_probe.py scripts/cp6_az_probe.py scripts/cp7_finance_cases.py scripts/cp7_recost_cases.py',
 'Economic/physical/book dates, late source correction, source-chain valuation, close preflight and immutable filed versus current report.',
 'AW pre-BA changed_since_filing expectations and CONTROL_PASS/OBSERVED vocabulary are qualified separately; never relabel their raw results.')
profile('procurement',r'P09|RECEIPT|RF_|MATERIAL|SUPPLIER|A4:|CP17-ASTRA-R3-03-CUTTING',
 'scripts/cp7_procurement_cases.py scripts/cp7_receipt_correction_cases.py scripts/cp6_ba_probe.py audit/astra_cp17/cases_fable_seams.py',
 'Receipt/invoice/source return and supplier settlement conserve document cents, quantity, dated stock and journal/subledger amounts.')
profile('sales',r'P10|P11|SALE|SALES|RETURN|REFUND|PAYMENT_CORRECTION|F03_CASH|SKN22',
 'scripts/cp7_sales_chain_cases.py scripts/cp7_sales_payment_cases.py scripts/cp7_sales_return_correction_cases.py audit/astra_cp17/cases_integration.py',
 'Actual FG, draft reservation, posted sale, receipt, return/refund and linked correction are separate native effects.')
profile('payroll',r'P12|PAYROLL|ATTENDANCE|ROSTER|F03_E05|NOTE_|CP17-ASTRA-(PAY|HPP|FIN|POOL)|CP17-ASTRA-R3-.*REWORK|AS20-18',
 'scripts/cp7_installment_cases.py audit/astra_cp17/cases_payroll_leads.py audit/astra_cp17/cases_integration.py audit/astra_cp17/cases_finance_observability.py audit/astra_cp17/cases_fable_seams.py audit/astra_cp17/cases_pool_closure.py',
 'Accrual/attendance/source entitlement and settlement are distinct; duplicate-source negative controls and dated payable report.',
 'FIN-01, RWK-01 and HPP-01 are confirmed blocking defects. Passing ordinary payroll cases cannot override it; Fable overlap claims are narrowed to the tested source identity.')
profile('finance',r'P13|P19R|FINANCE|FINANCIAL|AS20-33|SKN22|FIN-07|PAY-06|CP17-ASTRA-CLAIM-',
 'scripts/cp7_finance_cases.py scripts/cp7_p19_report_v2_cases.py audit/astra_cp17/cases_integration.py audit/astra_cp17/cases_claim_date.py',
 'Owner report uses exact money/dated ledger sources, separates cash/revenue/profit/AP/AR, retains archived original and current-change marker.',
 'FIN-01 and FIN-02 remain blocking for dated payroll/vendor liabilities even when totals balance.')
profile('identity_policy',r'POLICY|STOP|PAUSED|MEMBERSHIP|SUCCESSOR|R03:|R06:|R12:|AS20-16|AS20C-08',
 'contracts/cp7/production-policy.ts scripts/cp6_bf_combined_modes.py tests/cp7/productionPolicy.test.ts',
 'Commercial brand/size membership and production state are versioned; STOP/PAUSED forbid new starts without deleting existing work.')
profile('supply',r'WIP|SUPPLY|SOURCE_CAPACITY|LINEAGE|MATCH|NETTING|YIELD|AS20-15|AS20-21|PL5H|P18_FULL',
 'scripts/cp7_planning_supply_cases.py scripts/cp7_pl5_history_yield_cases.py tests/cp7/nativeSourceCapacity.test.ts',
 'Unique parent/child source conservation across stages, compatibility edges, conditional allocation and history-based yield.',
 'PR44 netting includes Astra-authored code: prior Fable peer acceptance is explicitly carried, not self-certified.')
profile('schedule',r'SCHEDULE|TIMELINE|LATE_SUPPLY|UNKNOWN_(WORK|CAPACITY)|FEASIB|P19P|AS20C-22|O0[2345789]|O1[0679]|X(06|08|10|11|12|18)',
 'scripts/cp7_planning_schedule_cases.py scripts/cp7_p19_plan_v2_cases.py tests/cp7/families/f04/run.mjs tests/cp7/families/f04/continuation.mjs',
 'Dated timeline, early gap, material/capacity limit, rounding and current revalidation before apply; exact specification vectors are private-kernel evidence, linked to native capture separately.')
profile('models',r'MODEL|HOLDOUT|KNOWLEDGE|BASELINE|AVAILABILITY|P05_NATIVE|PL5H|AS20-20|AS20-24|O1[12]|O20|M0[1-8]|X1[345]',
 'scripts/cp7_model_native_cases.py scripts/cp7_pl5_history_yield_cases.py tests/cp7/families/f04/run.mjs tests/cp7/families/f04/continuation.mjs',
 'Observed zero/stockout/unknown, no future leakage, training and holdout separation, finite kernel vectors and explicit fallback.',
 'Synthetic fixtures establish implementation behavior; they do not certify predictive accuracy on factory demand.')
profile('material_capacity',r'MATERIAL|FABRIC|P08_|BOM|CAPACITY|FEASIB|O09|O10|X21',
 'scripts/cp7_fabric_recipe_cases.py scripts/cp7_fabric_physical_cases.py tests/cp7/families/f04/run.mjs',
 'Eligible free stock and installed/allocated facts remain distinct; gap, feasible quantity and unresolved quantity are not conflated.',
 'DATA_BERSYARAT rows certify only behavior when the necessary lineage/input exists and truthful UNKNOWN when it does not.')
profile('analysis',r'P14|P15|P19R|ANALYSIS|REPORT|AS20C-01|AS20-41|AS20-33|AS20-28|AS20-49|X16|O13|O14',
 'scripts/cp7_analysis_cases.py scripts/cp7_obligation_report_cases.py scripts/cp7_p19_report_v2_cases.py tests/cp7/families/f05-report-render.test.ts',
 'Shared run/scope/scenario, source operands, exact metric context, original publications, revisions and archived/current separation.')
profile('staged',r'P19_|P19[ARPM]|K[246]|AS20C-37|AS20-0[12]|AS20-3[579]|AS20-40|TRANSPORT|SCALE|LOAD',
 'scripts/cp7_p19_staged_cases.py scripts/cp7_p19_transport_cases.py scripts/cp7_p19_scale_cases.py scripts/cp7_p19_native_load_cases.py',
 'Complete multipage capture, bounded worker transport, request identity, full population and source/hash equivalence.',
 'Measured fixture sizes and runtimes are evidence, not a claimed factory-wide capacity/SLA. Accepted AS20-39 semantic-corruption detector boundary remains visible.')
profile('attention',r'ATTENTION|OBLIGATION|REMINDER|RULE|EPISODE|P18_E01|P19M|X2[234]',
 'scripts/cp7_attention_cases.py scripts/cp7_obligation_report_cases.py scripts/cp7_rule_lifecycle_cases.py scripts/cp7_p19_reminder_v2_cases.py',
 'Server-backed manual attention, source episodes and native obligations; ACK/snooze/DONE does not settle money or resolve underlying facts.',
 'Local preview/test-sink evidence is not evidence of real provider delivery or scheduled CP7C operation.')
profile('ai',r'P19A|AI|PROMPT|CLIPBOARD|POPUP|UTF8|AS20-36|X17',
 'scripts/cp7_p19_ai_v2_cases.py tests/cp7/automation.test.ts',
 'Role-scoped snapshot, bounded text with caveats, honest clipboard/popup fallback and no automatic AI writeback or URL payload.')
profile('auth_recovery',r'HTTP|ACCESS|AUTH|REVOK|REPLAY|RECOVERY|TRANSPORT|CLOSED_FENCE|CURRENT_RIGHT|ATOMIC|SESSION',
 'scripts/cp6_auditor_modes.py scripts/cp6_bc_modes.py scripts/cp6_bd_modes.py scripts/cp7_p19_transport_cases.py',
 'Real Auth plus SQL negative controls are separated; permission checked at use/replay, ambiguous commit keeps its request identity.')
profile('ui',r'BROWSER|DESKTOP|MOBILE|PHONE|TABLET|D09|LAU_T36',
 'scripts/cp6_bb_browser.mjs scripts/cp6_bc_browser.mjs scripts/cp6_bd_browser.mjs scripts/cp6_be_browser.mjs tests/browser/cp7-shell.spec.ts',
 'Owning screen to real Auth/API/server readback and phone layout; shell DOM/render tests remain a separate evidence class.',
 'A browser emulated phone/tablet is not a physical-device compatibility certification.')
profile('ownership_restore',r'RESTORE|P21|K3|RETENTION|CLEANUP|IMMUTAB|INVERSE|REFUSAL',
 'audit/astra_cp17/full_stack.py scripts/cp7_p21_full_rehearsal_probe.py scripts/cp7_restore_state.py scripts/check-source-ownership.mjs',
 'Installed runtime/source identity, complete catalog owners/ACLs, row boundary, refusal and disposal; no live release.',
 'CP1 historical replay limits, CP2 unavailable database restore, known pg_cron restore explanation, and original Q02 outer fixture limitation stay explicit.')

routes={}
def assign(ids, keys, note=''):
    for id in ids.split():
        assert id not in routes,id
        routes[id]=dict(profiles=keys.split(), note=note)
def seq(prefix,a,b):return ' '.join(f'{prefix}{i:02d}' for i in range(a,b+1))

assign(seq('ACC-A',1,8),'units accessory payroll')
assign(seq('ACC-B',1,7),'accessory procurement')
assign('ACC-C01 ACC-C02 ACC-C03 ACC-C04 ACC-C05 ACC-C09 ACC-C10 ACC-C11 ACC-C12','accessory')
assign('ACC-C06 ACC-C07 ACC-C08','conversion accessory')
assign(seq('ACC-D',1,7),'accessory_race accessory')
assign('ACC-D08','accessory recost_close');assign('ACC-D09 ACC-D10','ui accessory_race')
assign('ACC-D11','ownership_restore accessory');assign('ACC-D12','accessory staged')
assign('ALL-A01 ALL-A02 ALL-A03 ALL-P02 ALL-P03 ALL-P04 ALL-S01 ALL-S02 ALL-S03 ALL-W01 ALL-W02 ALL-W03 ALL-W04 ALL-W06 ALL-Y01 ALL-Y02','opening')
assign('ALL-C01 ALL-C02 ALL-C03','opening accessory');assign('ALL-C04','opening pocket')
assign('ALL-P01','opening procurement recost_close');assign('ALL-W05','opening laundry')
assign('AUD-A01 AUD-A02 AUD-A03 AUD-G07 AUD-G15','auth_recovery ui')
assign('AUD-A04','supply staged');assign('AUD-A05 AUD-S01','units')
assign('AUD-B01 AUD-B02 AUD-B03','opening');assign('AUD-B04 AUD-S06','recost_close finance')
assign('AUD-G01','procurement ui');assign('AUD-G02 AUD-G13','accessory ui')
assign('AUD-G03','conversion sales ui');assign('AUD-G04','sales ui')
assign('AUD-G05','payroll ui');assign('AUD-G06','finance attention recost_close')
assign('AUD-G08','opening ui');assign('AUD-G09','models schedule analysis')
assign('AUD-G14','staged','Fixture workload measurements are supplied; no unsupported claim of measured real-factory capacity.')
assign('AUD-G16','ui ownership_restore');assign('AUD-S02 AUD-S04','procurement recost_close')
assign('AUD-S03','procurement');assign('AUD-S05','opening staged')
assign('AUD-T01 AUD-T02','ownership_restore','Current runtime verification and qualified harness deltas, not the superseded draft/old runner, define the candidate.')

br={
1:'analysis staged attention',2:'analysis auth_recovery',3:'schedule supply',4:'schedule',5:'schedule',6:'supply schedule attention',
7:'supply staged',8:'supply',9:'supply',10:'supply laundry',11:'sales models',12:'models',13:'models',14:'schedule identity_policy',
15:'schedule units',16:'identity_policy',17:'laundry finance analysis',18:'staged supply',19:'material_capacity',20:'material_capacity accessory',
21:'material_capacity schedule',22:'schedule',23:'schedule',24:'analysis finance',25:'finance sales payroll',26:'analysis',28:'analysis',
29:'recost_close analysis',30:'recost_close analysis',31:'staged schedule',32:'staged auth_recovery',33:'auth_recovery',34:'attention',35:'ai analysis',
36:'staged analysis',37:'staged',38:'analysis attention',39:'ownership_restore',40:'ui schedule analysis'}
for n,keys in br.items():assign(f'BR-T{n:02d}',keys)
cp={1:'identity_policy',2:'identity_policy',3:'identity_policy supply',4:'supply schedule',5:'supply',6:'supply',7:'supply',8:'supply laundry',9:'schedule',10:'sales models',11:'models',12:'schedule units',13:'schedule',14:'auth_recovery',15:'ai',16:'staged',17:'schedule',18:'ai ui',19:'models',20:'models',21:'models',22:'models schedule',23:'schedule auth_recovery',24:'supply laundry',25:'supply',26:'supply procurement',27:'supply laundry conversion',28:'supply schedule',29:'supply',30:'supply staged',31:'identity_policy supply',32:'staged supply',33:'schedule models',34:'identity_policy schedule',35:'analysis ai auth_recovery'}
for n,keys in cp.items():assign(f'CP7-{n:02d}',keys)
assign('CROSS-T01','opening procurement laundry sales recost_close')
assign('CROSS-T02','sales accessory');assign('CROSS-T03','conversion accessory laundry')
assign('CROSS-T04','accessory payroll laundry');assign('CROSS-T05','auth_recovery accessory_race laundry_race')
assign('CROSS-T06','recost_close ownership_restore')
for n in range(1,37):
    keys='laundry'
    if n in (27,28):keys+=' conversion'
    if n in (22,23,34):keys+=' recost_close finance'
    if n in (30,31,32,33):keys+=' laundry_race'
    if n==35:keys+=' ownership_restore'
    if n==36:keys+=' ui'
    assign(f'LAU-T{n:02d}',keys)
for n in list(range(1,18))+[27,32,33,34,35,36]:
    keys='attention'
    if n in (2,11,27,33):keys+=' auth_recovery'
    if n in (3,7,8,10):keys+=' material_capacity'
    if n in (9,15):keys+=' accessory'
    if n in (14,17):keys+=' laundry finance'
    if n==16:keys+=' recost_close'
    if n==32:keys+=' ai'
    if n in (6,35):keys+=' staged'
    if n==36:keys+=' ownership_restore'
    assign(f'RMD-T{n:02d}',keys)
ux={1:'ui schedule',2:'ui analysis',3:'schedule',4:'supply',5:'staged auth_recovery',6:'attention supply',7:'identity_policy schedule',8:'supply laundry',9:'schedule auth_recovery',10:'analysis ui',11:'ui auth_recovery',12:'analysis attention identity_policy'}
for n,k in ux.items():assign(f'UX32-T{n:02d}',k)
wip={1:'supply schedule',2:'supply',3:'supply laundry',4:'supply',5:'supply',6:'schedule',7:'laundry finance',8:'schedule auth_recovery',9:'identity_policy',10:'staged supply',11:'supply material_capacity',12:'analysis attention auth_recovery'}
for n,k in wip.items():assign(f'WIP-T{n:02d}',k)

# The 84 charters overlap the 271 requirement groups. They are tracked separately,
# never added to the business execution count merely because they exist on paper.
charters={}
def charter(prefix,mapping):
    for n,keys in mapping.items():charters[f'{prefix}{n:02d}']=keys.split()
charter('O',{1:'schedule supply',2:'schedule',3:'schedule',4:'supply',5:'supply schedule',6:'sales models',7:'identity_policy schedule',8:'schedule units',9:'material_capacity',10:'schedule',11:'models',12:'models',13:'analysis finance',14:'finance',15:'supply',16:'schedule supply',17:'identity_policy',18:'pocket',19:'supply staged',20:'models'})
charter('E',{1:'opening procurement supply laundry sales finance',2:'supply laundry',3:'sales accessory',4:'conversion recost_close',5:'payroll',6:'recost_close',7:'pocket',8:'analysis attention ai',9:'staged auth_recovery',10:'schedule auth_recovery',11:'schedule',12:'auth_recovery',13:'recost_close sales',14:'auth_recovery',15:'staged supply',16:'analysis',17:'attention',18:'ai',19:'ui',20:'staged supply',21:'ownership_restore',22:'analysis auth_recovery',23:'identity_policy',24:'procurement accessory'})
charter('M',{1:'models',2:'models',3:'models',4:'models',5:'models',6:'models schedule',7:'schedule models',8:'models'})
charter('X',{1:'identity_policy',2:'models identity_policy',3:'identity_policy',4:'identity_policy laundry',5:'units identity_policy',6:'supply',7:'units finance',8:'supply',9:'staged',10:'schedule',11:'schedule',12:'schedule',13:'models',14:'models',15:'models',16:'analysis finance',17:'ai',18:'schedule',19:'analysis supply',20:'attention supply',21:'attention material_capacity',22:'attention finance',23:'attention',24:'attention',25:'attention auth_recovery',26:'attention auth_recovery',27:'attention auth_recovery',28:'attention auth_recovery',29:'attention',30:'attention ownership_restore',31:'ownership_restore',32:'ownership_restore'})
assert len(charters)==84

def primary_pattern(id):
    if id.startswith('ACC-'):
        s=id[4:]
        exact={'A01':'ACCESSORY_CONNECTED:|D09|DOZEN','A02':'OVER_STOCK|D01|D02','A03':'ACCESSORY_CONNECTED:|UOM',
            'A04':'ACCESSORY_CONNECTED_REFUSAL|COUNT|INVALID_NUMBERS','A05':'MATERIAL|UOM','A06':'STALE_PRICE|STALE_VERSION',
            'A07':'POSTED_EDIT|NOTE_|CARRY','A08':'A08:|ROUNDING','C06':'BE01:|CONVERSION','C07':'BE01:ACTUAL|UNSOURCED_COST',
            'C08':'LATE_INVOICE|RECOVERY|CONVERSION','D01':'BC_RACE:.*D01','D02':'BC_RACE:.*D02','D03':'ACCESSORY_CONNECTED_REFUSAL:STALE|POSTED_EDIT',
            'D04':'BC_RACE:.*(RET|D04|C02)','D05':'D05:|REPLAY','D06':'BC_HTTP|D06:','D07':'D07:',
            'D08':'D08:|WIB','D09':'BC_BROWSER:NOTE','D10':'BC_BROWSER|RECOVERY','D11':'RESTORE|INVERSE','D12':'D12:SERVER_PAGINATION'}
        return exact.get(s,re.escape(s)+':')
    if id.startswith('LAU-T'):
        n=int(id[-2:]);extra={1:'VENDOR:|AUTHORITY|RECEIPT_AFTER_A_LATER',9:'UNKNOWN_COMPONENT|UNKNOWN_PRICE',10:'UNINVOICED|ESTIMATE',11:'FREE|WAIVED',14:'LAU_T14|VERSION_AFTER',18:'BILLING_SOURCE|PARTIAL_NM',19:'INV_TWO_POSTS|CAPACITY',25:'NO_SKU|UNBOUND|PRICED|PACKAGE',26:'SCOPED_SIZE|MULTI_SIZE|RANGE:|EXPLICIT_SIZE',27:'ATTEMPT|R13:|REDYE',28:'REWASH|FREE|WAIVED',29:'CLAIM|W05:',30:'BD_RACE:INV',31:'BD_RACE:PRC|VERSION_AFTER',32:'T32:|BD_HTTP|BD_BROWSER',33:'BD_HTTP|REV_HTTP',34:'RECOST_ALARM|UNKNOWN_PRICE_CLOSE',35:'RESTORE|INVERSE',36:'BD_BROWSER|PAGES_55'}
        return f'T{n:02d}:|'+extra.get(n,'^NO_EXTRA_CASE$')
    if id.startswith('ALL-'):return re.escape(id[4:])+r'|OPENING'
    return None

def build():
    rows=json.loads((REG/'requirements.json').read_text())
    ledger=json.loads((OUT/'CASE_LEDGER_FINAL.json').read_text())['rows']
    extra=OUT/'CASE_LEDGER_CONTINUATION.json'
    if extra.exists():ledger+=json.loads(extra.read_text())['rows']
    kernel_path=OUT/'continuation/38558702641/11891469186/original/f04-private-kernels.json'
    kernel=json.loads(kernel_path.read_text())
    assert kernel['source_head']=='0b7049d9203bac52b47a4c89f3e0d75646067a8f'
    assert len(kernel['cases'])==143 and kernel['passed']==143 and not kernel['failures']
    for item in ledger:item['evidence_class']='NATIVE_BUSINESS_HTTP_BROWSER_CASE'
    for item in kernel['cases']:
        ledger.append(dict(run_id=38558702641,artifact_id=11891469186,
            original=str(kernel_path.relative_to(OUT)),group='F04_PRIVATE_KERNEL',case_id=item['id'],status=item['status'],
            evidence_class='PRIVATE_SQL_KERNEL_ONLY',business_case_credit=0))
    evidence_index={}
    for i,item in enumerate(ledger,1):
        item['_evidence_key']=f'EV{i:05d}'
        evidence_index[item['_evidence_key']]={k:item.get(k)for k in ('run_id','artifact_id','original','group','case_id','status','disposition','evidence_class')}
    def links(keys,pattern=None):
        return [item['_evidence_key']for item in ledger if any(re.search(profiles[key]['case_pattern'],item['case_id'],re.I)for key in keys)
                and (pattern is None or re.search(pattern,item['case_id'],re.I))]
    for row in rows:
        if row['scope'] in ('CP7C_FUTURE','CP7.5_FUTURE','CP8_FUTURE','OPTIONAL_NOT_SELECTED'):
            row['astra_review']=dict(disposition='EXPLICITLY_OUTSIDE_CURRENT_GATE',reason='Frozen framework scope plus owner CP7C/Drive HOLD; future phase or unselected optional feature. No PASS claim.',profiles=[],case_evidence=[])
            continue
        cfg=routes[row['id']]
        disposition='REVIEWED_WITH_BOUNDED_EXECUTION_AND_SOURCE_EVIDENCE'
        if row['id']=='AUD-G05':disposition='BLOCKED_BY_FIN01_RWK01_HPP01_PAYROLL_BASIS'
        if row['id'] in ('AUD-G06','BR-T25'):disposition='BLOCKED_BY_FIN01_AND_FIN02_DATED_LIABILITIES'
        if row['id']=='AUD-S04':disposition='BLOCKED_BY_STK01_PUBLIC_RESTATED_HISTORY'
        if row['id']=='AUD-G14':disposition='FIXTURE_LOAD_MEASURED_REAL_FACTORY_CAPACITY_NOT_VERIFIED'
        if row['id'] in ('CP7-18','BR-T40','UX32-T11'):disposition='BROWSER_EMULATION_VERIFIED_PHYSICAL_OWNER_DEVICE_NOT_VERIFIED'
        row['astra_review']=dict(disposition=disposition,**cfg,case_evidence=links(cfg['profiles']),
            primary_case_evidence=links(cfg['profiles'],primary_pattern(row['id'])),
            scope_split='Only current CP7 portion; actual scheduling/delivery/Drive remains CP7C HOLD' if row['scope']=='CP7_AND_CP7C' else None,
            acceptance='NO_UNQUALIFIED_ROW_PASS_OR_FEATURE_COMPLETENESS_CERTIFICATION',
            evidence_warning='Links are selected by reviewed semantics and then pattern matched for lookup. Case PASS is not an automatic every-clause certification.')
    assert len(rows)==271 and len({x['id']for x in rows})==271
    active={r['id']for r in rows if r['astra_review']['profiles']}
    assert active==set(routes),(active-set(routes),set(routes)-active)
    for key,p in profiles.items():
        p['source_inventory']=[dict(path=s,exists=(ROOT/s).exists(),sha256=hashlib.sha256((ROOT/s).read_bytes()).hexdigest() if (ROOT/s).exists() else None) for s in p['sources']]
    result=dict(candidate='0b7049d9203bac52b47a4c89f3e0d75646067a8f',status='REVIEW_DISPOSITIONS_COMPLETE_ACCEPTANCE_WITHHELD',profiles=profiles,rows=rows,
        counts=dict(total=len(rows),active=len(active),outside=len(rows)-len(active),dispositions=dict(collections.Counter(r['astra_review']['disposition']for r in rows))),production_go=False)
    (OUT/'REQUIREMENT_CROSSWALK.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    (OUT/'CASE_EVIDENCE_INDEX.json').write_text(json.dumps(evidence_index,indent=2)+'\n')
    journey_rows=json.loads((REG/'cases.json').read_text())
    for row in journey_rows:
        keys=charters[row['id']]
        row['astra_review']=dict(profiles=keys,case_evidence=links(keys),exact_oracle_case_evidence=[x['_evidence_key']for x in ledger if x['case_id'].startswith(row['id']+'.')],
            disposition='REVIEWED_CHARTER_LINKED_TO_EXECUTIONS_AND_SOURCE',
            scope='X25..X30 local backbone only; real schedule/provider/restore delivery remains CP7C HOLD' if row['id']in [f'X{i:02d}'for i in range(25,31)] else 'See profile boundary; an E2E charter is not automatically one continuous browser journey')
    owner_rows=json.loads((REG/'owner_delta.json').read_text())
    for row in owner_rows:
        row['astra_review']=dict(charters=row['case_ids'],profiles=sorted({k for id in row['case_ids']for k in charters[id]}),
            disposition='CURRENT_SCOPE_MAPPED_WITH_CP7C_HOLD' if row['id']=='OWN28-08' else 'MAPPED_TO_REVIEWED_CHARTERS')
    (OUT/'CHARTER_AND_OWNER_CROSSWALK.json').write_text(json.dumps(dict(charters=journey_rows,owner_rows=owner_rows),indent=2,ensure_ascii=False)+'\n')
    def esc(s):return str(s or '').replace('|','/').replace('\n',' ')
    md=['# Matriks review CP1–CP7: kebutuhan, charter, dan keputusan owner','',
        'Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`. Semua 271 baris diinventarisasi: 254 dalam lingkup kini dan 17 future/opsional tidak dipilih. Ini disposisi review dengan bukti terbatas, **bukan 254 klaim lulus seluruh klausul**. FIN01, FIN02, RWK01, STK01, HPP01 dan pemulihan CP2 tetap menghalangi penerimaan penuh. Daftar sumber/hash dan seluruh tautan EV ada di `REQUIREMENT_CROSSWALK.json` dan `CASE_EVIDENCE_INDEX.json`.','',
        'Setiap profil menjelaskan jalur sah, refusal/replay/koreksi, pembaca hilir, serta batasnya. EV berisi Original/run/artifact/group/case/status mentah. Pencarian pola hanya alat navigasi; tidak mengubah PASS suatu kasus menjadi sertifikat setiap kombinasi requirement. Bukti private SQL kernel 143 kasus dipisah dari browser/Auth dan tidak ditambahkan ke jumlah kasus bisnis.','',
        '| ID | Lingkup | Skenario / expected | Disposisi | Profil / petunjuk EV utama |','|---|---|---|---|---|']
    for row in rows:
        r=row['astra_review'];ids=r.get('primary_case_evidence',r.get('case_evidence',[]))
        md.append('| '+ ' | '.join(map(esc,[row['id'],row['scope'],row['scenario']+' → '+row['expected'],r['disposition'],', '.join(r['profiles'])+'; '+', '.join(ids[:5])+(' … seluruh ID di JSON' if len(ids)>5 else '')]))+' |')
    md+=['','## Profil review dan batas','', '| Profil | Yang diperiksa | Batas | Sumber |','|---|---|---|---|']
    for key,p in profiles.items():md.append('| '+' | '.join(map(esc,[key,p['review_focus'],p['boundary'],'; '.join(p['sources'])]))+' |')
    md+=['','## 84 charter O/E/M/X','', 'Charter bisa mempunyai beberapa kasus pembukti. Angka 84 bukan tambahan 84 run atau 84 perjalanan browser kontinu.','', '| ID | Expected | Profil | Oracle bernama persis | Batas |','|---|---|---|---|---|']
    for row in journey_rows:
        r=row['astra_review'];md.append('| '+' | '.join(map(esc,[row['id'],row['expected'],', '.join(r['profiles']),', '.join(r['exact_oracle_case_evidence']) or 'Bukti komposisi pada JSON; bukan oracle tunggal bernama sama',r['scope']]))+' |')
    md+=['','## 10 kebutuhan tambahan owner','', '| ID | Kebutuhan | Charter | Disposisi |','|---|---|---|---|']
    for row in owner_rows:md.append('| '+' | '.join(map(esc,[row['id'],row['need'],', '.join(row['case_ids']),row['astra_review']['disposition']]))+' |')
    (OUT/'REQUIREMENT_REVIEW.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(result['counts']))
    print('source_path_corrections_needed',sorted({s['path'] for p in profiles.values()for s in p['source_inventory'] if not s['exists']}))
if __name__=='__main__':build()
