"""r5 fixes of the r4 audits (candidate 663f6fae), spliced into the CP17 harness after r4.

R5-01 (Sol SOL-R4-001, S1, r4 report audit/sol_cp17_r4): a valid FG_REPAIR Nota (two repair wages of 2 and 1 pcs at
2,000, saved and posted through the CP7 Nota route, 6,000) raised two CRITICAL `payroll_work_wrong_contractor` in
erp.run_v263a_payroll_integrity_checks(), because the checker resolved a line's contractor only through PRODUCTION and
REWORK sources (cp7_payroll_checks_bundle.py). Sol's case SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM
(audit/sol_cp17_r4/payroll_detector_dispute_cases.py) is used as written: the same fixture, the same resolved rows, the
same expected detector delta (none) and the same COUNTEREXAMPLE while the false alarm is there; the checker as it was
before R5-01 runs beside the installed one on the same books and must still count the two lines. Control: the checker
still counts a repair line whose wage belongs to another contractor and one whose wage is missing (the immutable-wage
guard is switched off only inside a rolled-back savepoint, labelled DETECTOR_CONTROL, like the CP17 legacy findings case).

R5-02 (owner D17-2, KNOWN-P19-DIRECT-LATENCY): in eleven STABLE report and check readers every literal
`erp.account_id('<KEY>')` became `(select erp.account_id('<KEY>'))`, evaluated once per query instead of once per journal
line (cp7_report_accounts_bundle.py). Native cases: each installed reader and the same reader without the change run side
by side on the CP17 books (every product, PO, pocket period, opening settlement and sale journal/PO pair the database
holds, and three report windows) and must give the same rows or the same refusal; the review fails for a reader whose
literal calls changed or that uses a key outside the listed core mappings; a core mapping cannot be deleted.
The CP17 books hold no opening credit, pocket period or sale journal, so a first run compared three readers on no input
at all (CI 3b9817ae, PASS on nothing). Inside the case's rolled-back savepoint the case now builds those rows through
the paths the BB and BE probes use (an opening import with three allowances and a customer credit applied to an opening
receivable; a production import with its historical pocket period posted; a sale of an opening finished good and its
return), and every reader must answer at least one input without a refusal, the three of them with a value.

r6 hardening (Sol's sealed r5 handoff, audit/sol_cp17_r5/WRITER_HANDOFF.md "Penguatan uji permanen"; test strength
only): Sol's case asserts all 167 detector identities at 0 before it starts; the control keeps all 167 detector outputs
per phase and each rollback must give the earlier output back exactly; the eleven pre-R5-02 readers are installed
together in erp inside a rolled-back savepoint, so nested and indirect calls (owner report -> period readiness ->
run_v267/run_v268; run_v267 -> pocket period checks -> pocket period book) use the old graph too; Sol's literal book (PO
120 -> FG 96/COGS 24 -> FG 108/COGS 12, lifecycle +24/-12, SQL NULL for a missing journal, empty and multirow answers) is
asserted on both graphs and a value must be non-zero; one manual PREPARE of the PO book answers 120 -> 0 -> 120 across an
FG_INVENTORY remap, with psycopg's auto-prepare off for its lifetime. Sol's three tool errors (AUDITOR_TOOL_FAILURES.json)
are avoided.
"""
from datetime import timedelta
from decimal import Decimal
import json,re,uuid
import psycopg
from psycopg import sql
import cp6_bd_probe as bd
import cp6_be_pocket_probe as pocket
import cp7_nota_cases as nota
import cp7_nota_source_cases as sources
import cp7_payroll_checks_bundle as payroll_checks
import cp7_report_accounts_bundle as report_accounts

NATIVE=['CP17_R5_01_VALID_FG_REPAIR_NOTA_ZERO_ALARM_SOL','CP17_R5_01_PAYROLL_CHECK_STILL_FINDS_WRONG_OR_MISSING_REPAIR',
        'CP17_R5_02_REPORT_READERS_SAME_ANSWER','CP17_R5_02_REPORT_READERS_REVIEWED']
RACES=[]
HTTP=[]
BROWSER=[]
FUNCTIONS=()
TARGET='run_v263a_payroll_integrity_checks:'+payroll_checks.CHECK
OWNER_AUTH=str(bd.chain.production.base.OPERATOR_AUTH)
WAGE_GUARD='trg_guard_fg_unsourced_repair_wages_v1_immutable'
# Sol's count of the Native detector identities on the r5 candidate (audit/sol_cp17_r5/WRITER_HANDOFF.md, point 1).
DETECTOR_IDENTITIES=167
PO_BOOK='erp.compute_po_hpp_gl_book_v2620e(uuid)'
NON_PO_BOOK='erp.compute_non_po_product_hpp_book_v2620f(uuid)'
LIFECYCLE='erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)'
OWNER_REPORT='erp.get_owner_financial_snapshot_v2(date,date,date)'
BOOK_KEYS=('fg_value','cogs_value','other_out_value')
ZERO=(Decimal(0),Decimal(0),Decimal(0))
PREPARED='cp17_r5_02_po_book'


def outputs(cur):
    """Every Native detector row (cp6_bc_probe.DETECTORS) as the owner reads it: identity -> the whole row (check_name,
    severity, issue_count, details). Exactly the 167 identities Sol counted, or the case stops."""
    out={}
    for function in bd.bcp.DETECTORS:
        bd.api.admin(cur);bd.chain.production.owner(cur)
        rows=cur.execute('select to_jsonb(x) from erp.'+function+'() x').fetchall()
        bd.api.admin(cur)
        for (row,) in rows:
            ident=function+':'+row['check_name'];assert ident not in out,('CP17_R5_DUPLICATE_DETECTOR',ident)
            row['issue_count']=int(row['issue_count']);out[ident]=row
    assert len(out)==DETECTOR_IDENTITIES,('CP17_R5_DETECTOR_IDENTITIES',len(out),DETECTOR_IDENTITIES)
    return out


def counts(out):return {k:v['issue_count'] for k,v in out.items()}


def detectors(cur):
    """Every Native detector identity and its count (all 167)."""
    return counts(outputs(cur))


def delta(before,after):
    assert set(before)==set(after),('CP17_R5_DETECTOR_SET_CHANGED',sorted(set(before)^set(after)))
    return {k:after[k]-before[k] for k in before if after[k]!=before[k]}


def types(signature):
    tail=signature.split('(')[1][:-1];return tail.split(',') if tail else []


def key(args):return tuple(None if v is None else str(v) for v in args)


def nulls(v):return (v is None,v or '')


def decode(text):
    """One to_jsonb(...)::text answer: SQL NULL stays None (never 0, never the string 'null'); numbers become Decimal."""
    return None if text is None else json.loads(text,parse_float=Decimal)


def meaningful(v):
    """A value: a non-zero number, a non-empty string or true somewhere in it (SQL NULL, JSON null, 0, '', {}, [] are not)."""
    if isinstance(v,dict):return any(meaningful(x) for x in v.values())
    if isinstance(v,list):return any(meaningful(x) for x in v)
    if isinstance(v,bool):return v
    if isinstance(v,(int,Decimal)):return v!=0
    return isinstance(v,str) and v!=''


def book(rows):
    """PO book rows (to_jsonb text) as (fg, cogs, other) Decimal triples."""
    return [tuple(Decimal(str(decode(r)[k])) for k in BOOK_KEYS) for r in rows]


def amounts(rows):
    """Scalar answers (to_jsonb text) as Decimal, SQL NULL as None."""
    return [None if decode(r) is None else Decimal(str(decode(r))) for r in rows]


def rows_of(answer):
    assert answer[0]=='ROWS',('CP17_R5_02_EXPECTED_ROWS',str(answer)[:400]);return answer[1]


def checker_before(cur):
    """Install, inside the caller's savepoint, the checker as it was before R5-01 under another name."""
    bd.api.admin(cur)
    installed=cur.execute('select pg_get_functiondef(%s::regprocedure)',(payroll_checks.SIGNATURE,)).fetchone()[0]
    old=payroll_checks.unpatched(installed)
    head='FUNCTION '+payroll_checks.SIGNATURE
    assert old.count(head)==1,'CP17_R5_01_CHECKER_HEAD_CHANGED'
    cur.execute('create schema cp17_r5_01')
    cur.execute(old.replace(head,'FUNCTION cp17_r5_01.checks_before()',1))
    # Called like the installed checker (owner context, role authenticated); the schema exists only inside the savepoint.
    cur.execute('grant usage on schema cp17_r5_01 to authenticated;grant execute on function cp17_r5_01.checks_before() to authenticated')
    def wrong():
        bd.api.admin(cur);bd.chain.production.owner(cur)
        n=cur.execute("select issue_count from cp17_r5_01.checks_before() where check_name=%s",(payroll_checks.CHECK,)).fetchone()[0]
        bd.api.admin(cur);return int(n)
    return wrong


def valid_nota(cur,today):
    """Sol's fixture: two Native repair wages (2 and 1 pcs at 2,000), then the public CP7 Nota SAVE and POST."""
    f=sources.repair(cur,today,qty=2)
    second=sources.ax.post(cur,sources.ax.repair_payload(f,1))
    bd.api.admin(cur)
    return f,second


def resolved_rows(cur,payroll_id):
    # Sol's resolution query, as written.
    return cur.execute("""select p.id::text,p.source_type,p.source_id::text,p.qty_payable::text,
      p.rate_snapshot::text,p.amount::text,ps.contractor_id::text,w.contractor_id::text,
      p.work_component_id::text,w.work_component_id::text,w.qty_pcs::text,w.rate_per_pcs::text,
      w.amount::text,w.status,r.status,w.receipt_id::text
      from erp.payroll_work_items p join erp.payroll_settlements ps on ps.id=p.payroll_id
      left join erp.fg_unsourced_repair_wages_v1 w on p.source_type='FG_REPAIR' and w.id=p.source_id
      left join erp.fg_unsourced_receipts_v1 r on r.id=w.receipt_id
      where p.payroll_id=%s order by w.qty_pcs,p.id""",(payroll_id,)).fetchall()


def cases(cur,today):
    # Imported here: the CP17 harness imports this module while it loads (finish_fixture and po_hpp are used at run time).
    import cp7_cp17_fix_cases as cp17

    # ---- R5-01: Sol's case, as written in audit/sol_cp17_r4/payroll_detector_dispute_cases.py (correct_repair).
    def sol_valid_repair_nota():
        o=dict(oracle_origin='SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM (PROMAX_INV_D02_HEALTHY_BOOK_ZERO)',
               fixture_origin='ACCEPTED_AX_NATIVE_REPAIR_QTY2_AND1_THEN_PUBLIC_CP7_NOTA_SAVE_POST',no_direct_fact_edit=True)
        before=detectors(cur)
        # Sol's point 1: the healthy-book contract starts from all 167 identities at 0 (each CP17 case is rolled back, so
        # the books before this one are the installed CP17 books); asserted, not only recorded.
        nonzero={k:v for k,v in before.items() if v}
        assert len(before)==DETECTOR_IDENTITIES and not nonzero,('CP17_R5_01_BASELINE_NOT_ZERO_167',len(before),nonzero)
        o['baseline_all_zero']=True;o['detector_identities']=len(before)
        cur.execute('savepoint cp17_r5_01_sol')
        try:
            old=checker_before(cur);old_before=old()
            f,second=valid_nota(cur,today)
            o.update(contractor_id=str(f['contractor']),receipt_ids=[f['receipt'],second['receipt_id']])
            assert delta(before,detectors(cur))=={},'CP17_R5_01_REPAIR_SOURCES_RAISED_ALARMS'
            draft=nota.command(cur,'SAVE',nota.payload(cur,f,today))
            assert delta(before,detectors(cur))=={},'CP17_R5_01_DRAFT_RAISED_ALARMS'
            posted=nota.act(cur,'POST',draft);bd.api.admin(cur)
            header=cur.execute('select id::text,contractor_id::text,status,labor_total::text,net_payable::text from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()
            assert header[1]==str(f['contractor']) and header[2]=='CALCULATED' and Decimal(header[3])==Decimal(header[4])==6000,header
            rows=resolved_rows(cur,posted['payroll_id'])
            assert len(rows)==2 and [Decimal(r[3]) for r in rows]==[1,2],rows
            for row in rows:
                assert row[1]=='FG_REPAIR' and row[6]==row[7]==header[1]
                assert row[8]==row[9] and Decimal(row[3])==Decimal(row[10])
                assert Decimal(row[4])==Decimal(row[11])==2000
                assert Decimal(row[5])==Decimal(row[12])==Decimal(row[3])*2000
                assert row[13]==row[14]=='POSTED' and row[15] in o['receipt_ids']
            assert sum(Decimal(r[5]) for r in rows)==6000
            observed=delta(before,detectors(cur))
            old_after=old()
            o.update(payroll_header=header,observed_delta=observed,checker_before_r5_01=dict(before=old_before,after=old_after))
            # Before the fix the same books carry the two false alarms (Sol: 0 -> 2).
            assert old_after-old_before==2,('CP17_R5_01_OLD_CHECKER_DID_NOT_REPRODUCE',old_before,old_after)
            if observed=={}:
                o.update(status='PASS',false_alarm_reproduced=False,contract_satisfied=True)
            elif observed=={TARGET:2}:
                o.update(status='COUNTEREXAMPLE',false_alarm_reproduced=True,contract_satisfied=False)
            else:
                raise AssertionError(('CP17_R5_01_UNEXPECTED_ALARM_SET',observed))
        finally:
            cur.execute('rollback to savepoint cp17_r5_01_sol');cur.execute('release savepoint cp17_r5_01_sol');bd.api.admin(cur)
        assert detectors(cur)==before,'CP17_R5_01_DETECTORS_NOT_RESTORED'
        assert cur.execute("select count(*) from pg_namespace where nspname='cp17_r5_01'").fetchone()[0]==0
        o['full_restore']=True
        return o

    # ---- R5-01 control: real wrong-contractor and missing repair sources still count.
    # Sol's point 5: all 167 detector outputs are kept for the healthy book, the valid Nota, each corruption and each
    # rollback; a rollback gives the earlier output back exactly. The guard refusing the write is no sensitivity control,
    # so the wage guard stays off for the corrupting write only (re-enabled before the detectors read).
    def wrong_or_missing_still_found():
        o=dict(phases=[])
        def phase(label):
            out=outputs(cur);o['phases'].append(dict(label=label,identities=len(out),nonzero={k:v for k,v in counts(out).items() if v},outputs=out))
            return out
        def guard_on():
            assert cur.execute("select tgenabled from pg_trigger where tgname=%s",(WAGE_GUARD,)).fetchone()[0]=='O','CP17_R5_01_WAGE_GUARD_OFF'
        def rollback(name):
            cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);bd.api.admin(cur)
        healthy=phase('HEALTHY_BOOK')
        assert not o['phases'][-1]['nonzero'],('CP17_R5_01_CONTROL_BASELINE_NOT_ZERO',o['phases'][-1]['nonzero'])
        cur.execute('savepoint cp17_r5_01_control')
        try:
            f,second=valid_nota(cur,today)
            posted=nota.act(cur,'POST',nota.command(cur,'SAVE',nota.payload(cur,f,today)));bd.api.admin(cur)
            wages=[r[2] for r in resolved_rows(cur,posted['payroll_id'])]
            assert len(wages)==2
            other=cur.execute('select id::text from erp.contractors where id<>%s order by id limit 1',(f['contractor'],)).fetchone()
            assert other,'CP17_R5_01_NO_OTHER_CONTRACTOR'
            valid=phase('VALID_NOTA_6000')
            assert counts(valid)==counts(healthy),('CP17_R5_01_CONTROL_VALID_NOTA_ALARM',delta(counts(healthy),counts(valid)))
            def without_guard(statement,args):
                # DETECTOR_CONTROL: corrupt one immutable wage inside this savepoint only.
                bd.api.admin(cur);cur.execute('alter table erp.fg_unsourced_repair_wages_v1 disable trigger '+WAGE_GUARD)
                try:cur.execute(statement,args)
                finally:bd.api.admin(cur);cur.execute('alter table erp.fg_unsourced_repair_wages_v1 enable trigger '+WAGE_GUARD)
                guard_on()
            cur.execute('savepoint cp17_r5_01_wrong')
            try:
                without_guard('update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s',(other[0],wages[0]))
                moved=delta(counts(valid),counts(phase('WAGE_OF_ANOTHER_CONTRACTOR')))
                without_guard('update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s',(f['contractor'],wages[0]))
                restored=delta(counts(valid),counts(phase('WAGE_GIVEN_BACK')))
            finally:rollback('cp17_r5_01_wrong')
            assert phase('ROLLBACK_WRONG_CONTRACTOR')==valid,'CP17_R5_01_CONTROL_WRONG_CONTRACTOR_NOT_RESTORED'
            cur.execute('savepoint cp17_r5_01_missing')
            try:
                without_guard('delete from erp.fg_unsourced_repair_wages_v1 where id=%s',(wages[1],))
                missing=delta(counts(valid),counts(phase('WAGE_MISSING')))
            finally:rollback('cp17_r5_01_missing')
            assert phase('ROLLBACK_MISSING_WAGE')==valid,'CP17_R5_01_CONTROL_MISSING_WAGE_NOT_RESTORED'
            # The target counts each corrupted line once; other detectors may notice the corruption too (recorded).
            assert moved.get(TARGET)==1 and restored=={} and missing.get(TARGET)==1,(moved,restored,missing)
            guard_on()
        finally:rollback('cp17_r5_01_control')
        assert phase('ROLLBACK_CONTROL')==healthy,'CP17_R5_01_CONTROL_NOT_RESTORED'
        target=[p['outputs'][TARGET]['issue_count'] for p in o['phases']]
        assert target==[0,0,1,0,0,1,0,0],('CP17_R5_01_CONTROL_TARGET_0_1_0',target)
        assert all(p['identities']==DETECTOR_IDENTITIES for p in o['phases'])
        o.update(status='PASS',wage_of_another_contractor_counted=moved,restored_wage_counts_nothing=True,
                 missing_wage_counted=missing,guard_switched_off_only_inside_rolled_back_savepoint=True,
                 target_by_phase=dict(zip([p['label'] for p in o['phases']],target)),all_167_outputs_each_phase=True,
                 rollback_outputs_equal_earlier_outputs=True)
        return o

    # ---- R5-02: every changed reader against itself without the change, on the same books.
    def reader_fixtures():
        """Rows the CP17 books lack for three readers, built inside the caller's savepoint (BB and BE probe paths)."""
        bbp=bd.bbp
        fx=bbp.financial_fixture(cur,today,documents=[('CUSTOMER_RECEIVABLE','R5-CA','100.00','30.00'),('SUPPLIER_PAYABLE','R5-SA','100.00','30.00'),
                                                      ('VENDOR_PAYABLE','R5-VA','100.00','30.00')],credits=[('R5-RC','25.00','0.00')])
        effective=str(fx['cutover']+timedelta(days=2))
        for number,kind in (('R5-CA','CUSTOMER_ALLOWANCE'),('R5-SA','SUPPLIER_ALLOWANCE'),('R5-VA','VENDOR_ALLOWANCE')):
            bbp.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='CREDIT',balance_id=fx['balances'][number],amount='10.00',effective_date=effective,
                    credit_kind=kind,credit_note_number='CN-'+number+'-'+fx['code'],reason='CP17 R5-02 reader input')
        credit=bbp.ws(cur,fx['batch'])['customer_credits'][0]
        bbp.act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='APPLY_OPENING_AR',credit_id=credit['credit_id'],balance_id=fx['balances']['R5-CA'],
                amount='20.00',effective_date=effective,reason='CP17 R5-02 reader input')
        cut=today-timedelta(days=10)
        f=bbp.production_post(cur,today,pocket.active_unit(cur,pocket.rows(cut)))
        p=pocket.preview(cur,cut-timedelta(days=1),cut)
        pool=pocket.call(cur,'POST_PERIOD',dict(period_start=p['period_start'],period_end=p['period_end'],expected_revision=p['revision'],
                                                reason='CP17 R5-02 reader input'))['id']
        lot,product,location=bd.q(cur,"""select m.lot_id::text,l.product_id::text,m.location_id::text from erp.be_pocket_sewing_v1 s
            join erp.fg_stock_movements m on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=s.opening_item_id and m.movement_type='OPENING'
            join erp.fg_lots l on l.id=m.lot_id where s.batch_id=%s and s.target_kind='FINISHED_GOODS'""",f['batch'])[0]
        customer=bd.chain.base.create_customer(cur,'R5-02-'+uuid.uuid4().hex[:8]);bd.chain.production.owner(cur)
        made=bd.one(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',json.dumps(dict(sale_number='R5-02-'+uuid.uuid4().hex[:10],
            customer_id=customer,source_location_id=location,sale_date=bd.iso(bd.chain.production.at(cut+timedelta(days=1),17)),
            reason='CP17 R5-02 reader input',items=[dict(product_id=product,qty_pcs=1,unit_price_snapshot='20000',discount_amount=0)])),str(uuid.uuid4()))
        sale=made['sale_id'];version=bd.one(cur,'select row_version from erp.sales_headers where id=%s',sale)
        bd.chain.production.owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale,uuid.uuid4(),version));bd.api.admin(cur)
        sale_return=pocket.return_sale(cur,sale,cut+timedelta(days=3));bd.api.admin(cur)
        return dict(opening_batch=str(fx['batch']),pocket_period=str(pool),sale=str(sale),sale_return=str(sale_return))
    # ---- r6 (Sol's r5 handoff, points 2-4): the old graph installed together, Sol's literal book, one manual PREPARE.
    def claims():
        # Installed and old readers run in one context: the database owner session (the internal readers are not granted to
        # the browser role) with the owner's claims, so erp.require_owner_admin() and erp.require_internal() see the owner.
        bd.api.admin(cur);cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=OWNER_AUTH,role='authenticated')),))
    def call(text,params,shape):
        claims();cur.execute('savepoint cp17_r5_02_call')
        try:return ('ROWS',shape(cur.execute(text,params).fetchall()))
        except psycopg.Error as e:
            cur.execute('rollback to savepoint cp17_r5_02_call');return ('ERR',e.sqlstate,str(e).split('\n')[0])
        finally:
            cur.execute('release savepoint cp17_r5_02_call');bd.api.admin(cur)
    def answer(signature,a):
        """One reader call: its rows as to_jsonb text (SQL NULL kept as None), or its refusal."""
        t=types(signature);assert len(a)==len(t),(signature,a)
        return call('select to_jsonb(x)::text from '+signature.split('(')[0]+'('+','.join('%s::'+k for k in t)+') x',list(a),
                    lambda rows:sorted((r[0] for r in rows),key=nulls))
    def single(signature,args,empty=False):
        """Sol's multirow control (reader_multirow_cases.py): one statement calls the reader once per input, ordinal kept;
        with `where false` the empty answer of the same statement."""
        t=types(signature);cells=[];params=[]
        for i,a in enumerate(args):
            assert len(a)==len(t),(signature,a);cells.append('('+str(i)+''.join(',%s::'+k for k in t)+')');params.extend(a)
        return call('with inputs('+','.join(['ordinal']+['a'+str(i) for i in range(len(t))])+') as(values '+','.join(cells)+')'
                    ' select i.ordinal,to_jsonb(x)::text from inputs i cross join lateral '+signature.split('(')[0]
                    +'('+','.join('i.a'+str(i) for i in range(len(t)))+') x'+(' where false' if empty else '')+' order by 1,2',
                    params,lambda rows:[[o,v] for o,v in rows])
    def definitions():
        bd.api.admin(cur)
        return {s:cur.execute('select pg_get_functiondef(%s::regprocedure)',(s,)).fetchone()[0] for s in report_accounts.READERS}
    def graph(inputs,pick=None):
        """The installed readers, then all eleven as they were before R5-02 installed together in erp inside a rolled-back
        savepoint (Sol's point 2), on the same inputs: every nested or indirect call of a reader then reaches the old body
        too, not only a call written in another reader. Same rows or the same refusal per input; with `pick`, also the
        multirow and empty answers of one statement."""
        installed=definitions();old={s:report_accounts.unwrap(s,d) for s,d in installed.items()}
        each=lambda:{s:[answer(s,a) for a in args] for s,args in inputs.items()}
        rows=lambda chosen:{s:dict(multirow=single(s,a),empty=single(s,a,True)) for s,a in chosen.items()}
        new=dict(each=each());chosen=pick(new['each']) if pick else {};new['rows']=rows(chosen)
        cur.execute('savepoint cp17_r5_02_old_graph')
        try:
            for s in report_accounts.READERS:bd.api.admin(cur);cur.execute(old[s],prepare=False)
            assert definitions()==old,'CP17_R5_02_OLD_GRAPH_NOT_INSTALLED'
            previous=dict(each=each(),rows=rows(chosen))
        finally:
            cur.execute('rollback to savepoint cp17_r5_02_old_graph');cur.execute('release savepoint cp17_r5_02_old_graph');bd.api.admin(cur)
        assert definitions()==installed,'CP17_R5_02_GRAPH_NOT_RESTORED'
        differences=[(s,str(a),str(x)[:400],str(y)[:400]) for s in inputs for a,x,y in zip(inputs[s],new['each'][s],previous['each'][s]) if x!=y]
        differences+=[(s,k,str(new['rows'][s][k])[:400],str(previous['rows'][s][k])[:400]) for s in chosen for k in ('multirow','empty')
                      if new['rows'][s][k]!=previous['rows'][s][k]]
        assert not differences,('CP17_R5_02_READER_ANSWER_CHANGED',differences[:2])
        # Recorded: the readers each old body names directly (indirect paths, e.g. the owner report through the period
        # readiness, reach the old bodies as well because the old graph replaced the installed one in erp).
        nested={s:[r for r in report_accounts.READERS if r!=s and re.search(r'\berp\.'+re.escape(r.split('(')[0].split('.')[1])+r'\s*\(',old[s])]
                for s in report_accounts.READERS}
        return dict(new=new,old=previous,chosen=chosen,nested={s:n for s,n in nested.items() if n})
    def produced():
        """Sol's PO (reader_graph_cases.produced): 10 pcs of one PO through the chain's writers to FG, HPP 120, one lot."""
        g=cp17.finish_fixture(cur,today,label='CP17-R5-02');bd.api.admin(cur)
        assert tuple(map(Decimal,cp17.po_hpp(cur,g['po'])))==(120,10),'CP17_R5_02_FIXTURE_HPP_120_QTY10'
        f=dict(po=str(g['po']),product=str(g['product']),lot=str(g['lot']))
        assert cur.execute('select po_id::text,lot_origin from erp.fg_lots where id=%s',(f['lot'],)).fetchone()==(f['po'],'PRODUCTION')
        locations=cur.execute('select distinct location_id::text from erp.fg_stock_movements where lot_id=%s',(f['lot'],)).fetchall()
        assert len(locations)==1,locations
        return dict(f,location=locations[0][0])
    def make_sale(f):
        """Sol's sale (reader_graph_cases.make_sale): 2 pcs of the PO's lot, saved and posted by the owner."""
        customer=bd.chain.base.create_customer(cur,'R5-02-PO-'+uuid.uuid4().hex[:8]);bd.chain.production.owner(cur)
        at=cur.execute("select statement_timestamp()-interval '10 minutes'").fetchone()[0]
        made=cur.execute('select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',(json.dumps(dict(sale_number='R5-02-PO-'+uuid.uuid4().hex[:10],
            customer_id=str(customer),source_location_id=f['location'],sale_date=at.isoformat(),reason='CP17 R5-02 reader input',
            items=[dict(product_id=f['product'],qty_pcs=2,unit_price_snapshot='20',discount_amount=0)])),uuid.uuid4())).fetchone()[0]
        bd.api.admin(cur);version=cur.execute('select row_version from erp.sales_headers where id=%s',(made['sale_id'],)).fetchone()[0]
        bd.chain.production.owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(made['sale_id'],uuid.uuid4(),version));bd.api.admin(cur)
        allocations=cur.execute('select a.lot_id::text,a.qty_pcs::text from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id'
                                ' where i.sale_id=%s',(made['sale_id'],)).fetchall()
        assert len(allocations)==1 and allocations[0][0]==f['lot'] and Decimal(allocations[0][1])==2,allocations
        return str(made['sale_id'])
    def make_return(sale):
        """Sol's return (reader_graph_cases.make_return): 1 pc of that sale, drafted and posted by the owner."""
        ident=str(uuid.uuid4());bd.chain.production.owner(cur)
        cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) select %s,%s,id,customer_id,"
                    "statement_timestamp(),erp.current_app_user_id() from erp.sales_headers where id=%s",(ident,'R5-02-RET-'+ident,sale))
        cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount)"
                    " select %s,a.id,l.product_id,l.id,a.location_id,1,20 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id"
                    " where a.sale_item_id in(select id from erp.sales_items where sale_id=%s)",(ident,sale))
        cur.execute('select erp.post_sales_return(%s)',(ident,));bd.api.admin(cur)
        return ident
    def journal(kind,source):
        bd.api.admin(cur)
        rows=cur.execute("select id::text from erp.journal_entries where source_type=%s and source_id=%s and status='POSTED'",(kind,source)).fetchall()
        assert len(rows)==1,('CP17_R5_02_LIFECYCLE_JOURNAL',kind,rows);return rows[0][0]
    def stage(label,f,expected,lifecycle,missing):
        """Sol's literal book at one stage (reader_graph_cases.full_graph): read directly (psycopg decodes numeric and SQL
        NULL itself), then on the installed and the old graph."""
        po=f['po'];pairs=[(j,po) for j,_ in lifecycle]+[(missing,po),(missing,missing),(None,None)]
        want=[Decimal(v) for _,v in lifecycle]+[None,None,None];expected=tuple(map(Decimal,expected))
        claims()
        direct=cur.execute('select fg_value,cogs_value,other_out_value from erp.compute_po_hpp_gl_book_v2620e(%s::uuid)',(po,)).fetchall()
        life=[cur.execute('select erp.sale_lifecycle_po_hpp_amount_v2620d(%s::uuid,%s::uuid)',p).fetchone()[0] for p in pairs]
        bd.api.admin(cur)
        assert direct==[expected],('CP17_R5_02_LITERAL_BOOK',label,direct,expected)
        assert life==want and [v is None for v in life]==[v is None for v in want],('CP17_R5_02_LITERAL_LIFECYCLE',label,life,want)
        g=graph({PO_BOOK:[(po,),(missing,),(None,)],LIFECYCLE:pairs})
        for side in ('new','old'):
            assert [book(rows_of(x)) for x in g[side]['each'][PO_BOOK]]==[[expected],[ZERO],[ZERO]],('CP17_R5_02_GRAPH_LITERAL_BOOK',label,side)
            assert [amounts(rows_of(x)) for x in g[side]['each'][LIFECYCLE]]==[[v] for v in want],('CP17_R5_02_GRAPH_LITERAL_LIFECYCLE',label,side)
        return dict(label=label,book=[str(v) for v in direct[0]],lifecycle=[[str(p[0]),str(p[1]),None if v is None else str(v)] for p,v in zip(pairs,life)],
                    old_graph_same=True)
    def prepared_mapping(f):
        """Sol's point 4 (reader_mapping_q3_cases.py): one manual PREPARE of the PO book answers FG_INVENTORY mapped to its
        account (120), to a new empty ASSET account (0) and to its account again (120)."""
        bd.api.admin(cur)
        mapping="select account_id::text from erp.accounting_account_mappings where mapping_key='FG_INVENTORY'"
        original=cur.execute(mapping).fetchone()[0]
        assert cur.execute("select erp.expected_mapping_account_type('FG_INVENTORY')").fetchone()[0]=='ASSET'
        # Every NOT NULL column of the new account comes from the mapped one (Sol's first tool error left report_group out).
        empty=cur.execute("insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active)"
                          " select %s,%s,account_type,report_group,normal_balance,true,true from erp.chart_accounts where id=%s returning id::text",
                          ('R5FG'+uuid.uuid4().hex[:12],'CP17 R5-02 empty FG account',original)).fetchone()[0]
        samples=[];conn=cur.connection;threshold=conn.prepare_threshold
        def execute(label,account,fg):
            claims()
            assert cur.execute("select erp.account_id('FG_INVENTORY')::text").fetchone()[0]==account,('CP17_R5_02_MAPPING_NOT_SET',label)
            statement=cur.execute('select name,statement,prepare_time::text from pg_prepared_statements where name=%s',(PREPARED,)).fetchall()
            assert len(statement)==1,('CP17_R5_02_PREPARED_STATEMENT_GONE',label)
            rows=cur.execute(sql.SQL('EXECUTE '+PREPARED+'({})').format(sql.Literal(uuid.UUID(f['po'])))).fetchall()
            bd.api.admin(cur);observed=book([r[0] for r in rows])
            samples.append(dict(label=label,mapping_account=account,expected_fg=fg,observed=[[str(v) for v in b] for b in observed],statement=list(statement[0])))
            assert observed==[(Decimal(fg),Decimal(0),Decimal(0))],('CP17_R5_02_PREPARED_MAPPING_STALE',label,observed)
        # psycopg 3.2.10 sends DEALLOCATE ALL after a ROLLBACK while its own auto-prepare cache holds names; that ended the
        # manual statement in Sol's Q2 run (AUDITOR_TOOL_FAILURES.json row 3). Auto-prepare is off for this statement's
        # lifetime, so only its own PREPARE and DEALLOCATE decide it, across the mapping savepoint's rollback too.
        conn.prepare_threshold=None
        try:
            cur.execute('savepoint cp17_r5_02_prepared')
            try:
                cur.execute('PREPARE '+PREPARED+'(uuid) AS SELECT to_jsonb(x)::text FROM erp.compute_po_hpp_gl_book_v2620e($1) x')
                execute('ORIGINAL',original,120)
                cur.execute('savepoint cp17_r5_02_mapping')
                bd.api.admin(cur);cur.execute("update erp.accounting_account_mappings set account_id=%s where mapping_key='FG_INVENTORY'",(empty,))
                execute('EMPTY_ASSET',empty,0)
                cur.execute('rollback to savepoint cp17_r5_02_mapping');cur.execute('release savepoint cp17_r5_02_mapping')
                execute('RESTORED',original,120)
                cur.execute('DEALLOCATE '+PREPARED)
            finally:
                # Recover the transaction before any cleanup, so a cleanup error cannot hide the first one (Sol's Q2: 26000
                # reported as 25P02).
                cur.execute('rollback to savepoint cp17_r5_02_prepared');cur.execute('release savepoint cp17_r5_02_prepared');bd.api.admin(cur)
                if cur.execute('select count(*) from pg_prepared_statements where name=%s',(PREPARED,)).fetchone()[0]:cur.execute('DEALLOCATE '+PREPARED)
        finally:
            conn.prepare_threshold=threshold
        assert not cur.execute('select count(*) from pg_prepared_statements where name=%s',(PREPARED,)).fetchone()[0],'CP17_R5_02_PREPARED_LEFT'
        assert cur.execute(mapping).fetchone()[0]==original,'CP17_R5_02_MAPPING_NOT_RESTORED'
        assert [s['label'] for s in samples]==['ORIGINAL','EMPTY_ASSET','RESTORED'] and len({s['statement'][2] for s in samples})==1,samples
        return dict(samples=samples,same_prepared_statement_120_0_120=True,psycopg_auto_prepare_off_during_lifetime=True,
                    deallocated=True,mapping_restored=True)
    def reader_inputs(f,journals,missing):
        bd.api.admin(cur)
        ids=lambda text:[(r[0],) for r in cur.execute(text).fetchall()]
        windows=[(today-timedelta(days=d),today,today) for d in (0,30,400)]
        out={
            'erp.bb_opening_credit_account_v1(uuid)':ids('select settlement_id from erp.bb_opening_credits_v1'
                ' union select id from(select id from erp.opening_subledger_settlements order by id limit 20)s order by 1 limit 300'),
            NON_PO_BOOK:ids('select id from erp.products order by id limit 300'),
            PO_BOOK:ids('select id from erp.production_orders order by id limit 300'),
            OWNER_REPORT:windows,
            'erp.pocket_period_book_v1(uuid)':ids('select id from erp.pocket_periods order by id limit 300'),
            # Every Sale lifecycle journal with each PO on its lines and two other POs (the reader answers 0 or null for those).
            LIFECYCLE:[tuple(r) for r in cur.execute(
                """select distinct e.id,x.po_id from erp.journal_entries e left join erp.journal_entries o on o.id=e.reversal_of_id
                   cross join lateral(select l.po_id from erp.journal_lines l where l.journal_entry_id=e.id and l.po_id is not null
                     union select id from(select id from erp.production_orders order by id limit 2)p) x(po_id)
                   where e.source_type in('SALE','SALES_RETURN') or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
                   order by 1,2 limit 300""").fetchall()]}
        def add(s,extra):
            seen={key(a) for a in out[s]}
            for a in extra:
                if key(a) not in seen:seen.add(key(a));out[s].append(a)
        for s in report_accounts.READERS:
            out.setdefault(s,[()])
            if types(s)==['uuid']:add(s,[(missing,),(None,)])
        # Sol's inputs (reader_graph_cases.expanded_inputs): the literal PO and its product, both lifecycle journals, a
        # missing journal, NULL arguments and a report window with no books.
        add(PO_BOOK,[(f['po'],)]);add(NON_PO_BOOK,[(f['product'],)])
        add(LIFECYCLE,[(journals[0],f['po']),(journals[1],f['po']),(missing,f['po']),(missing,missing),(None,None)])
        add(OWNER_REPORT,[(today-timedelta(days=500),today-timedelta(days=499),today-timedelta(days=499))])
        return out
    def pick(each,inputs,f,journals,missing):
        """Sol's multirow inputs (reader_multirow_cases.inputs): four ordinals per reader, with the missing and NULL uuid
        where the reader takes one; only inputs that answered on their own."""
        special=lambda a:a[0] is None or str(a[0])==str(missing);chosen={}
        for s,args in inputs.items():
            ok=[a for a,r in zip(args,each[s]) if r[0]=='ROWS']
            if s==PO_BOOK:chosen[s]=[(f['po'],),(missing,),(None,),(f['po'],)]
            elif s==LIFECYCLE:chosen[s]=[(journals[0],f['po']),(journals[1],f['po']),(missing,missing),(journals[0],f['po'])]
            elif not ok:continue
            elif types(s)==['uuid']:
                valued=[a for a,r in zip(args,each[s]) if r[0]=='ROWS' and not special(a) and any(meaningful(decode(v)) for v in r[1])]
                first=(valued or [a for a in ok if not special(a)] or ok)[0]
                chosen[s]=[first]+[a for a in ok if special(a)]+[first]
            else:chosen[s]=(ok*4)[:3]+ok[:1]
        return chosen
    def readers_same_answer():
        report=report_accounts.verify(cur);compared={};oracles={}
        missing=uuid.uuid4()
        cur.execute('savepoint cp17_r5_02_same')
        try:
            built=reader_fixtures()
            assert not cur.execute('select exists(select 1 from erp.journal_entries where id=%s) or exists(select 1 from erp.production_orders where id=%s)',
                                   (missing,missing)).fetchone()[0]
            # Sol's literal book (point 3): FG/COGS/other 120/0/0 -> sale of 2: 96/24/0, lifecycle +24 -> return of 1:
            # 108/12/0, lifecycle -12; a missing journal is SQL NULL.
            f=produced();built.update(po=f['po'],po_product=f['product'],po_lot=f['lot'])
            oracles['stages']=[stage('FG10',f,(120,0,0),[],missing)]
            oracles['prepared_mapping']=prepared_mapping(f)
            sale=make_sale(f);sold=journal('SALE',sale)
            oracles['stages'].append(stage('SALE2',f,(96,24,0),[(sold,24)],missing))
            ret=make_return(sale);returned=journal('SALES_RETURN',ret)
            oracles['stages'].append(stage('RETURN1',f,(108,12,0),[(sold,24),(returned,-12)],missing))
            built.update(po_sale=sale,po_sale_return=ret)
            journals=(sold,returned);inputs=reader_inputs(f,journals,missing)
            g=graph(inputs,lambda each:pick(each,inputs,f,journals,missing))
            for s in report_accounts.READERS:
                answered=[r for r in g['new']['each'][s] if r[0]=='ROWS']
                compared[s]=dict(inputs=len(inputs[s]),answered=len(answered),
                                 with_value=sum(any(meaningful(decode(v)) for v in r[1]) for r in answered))
            # Literal answers on both graphs, per input and in one statement (ordinals 0..3), and the empty answers.
            full=(Decimal(108),Decimal(12),Decimal(0))
            for side in ('new','old'):
                keyed={s:{key(a):r for a,r in zip(inputs[s],g[side]['each'][s])} for s in inputs}
                assert book(rows_of(keyed[PO_BOOK][key((f['po'],))]))==[full],('CP17_R5_02_FINAL_BOOK',side)
                life=[amounts(rows_of(keyed[LIFECYCLE][key(a)])) for a in ((sold,f['po']),(returned,f['po']),(missing,f['po']),(missing,missing),(None,None))]
                assert life==[[24],[-12],[None],[None],[None]],('CP17_R5_02_FINAL_LIFECYCLE',side,life)
                for s,args in g['chosen'].items():
                    multi=g[side]['rows'][s]['multirow']
                    assert multi[0]=='ROWS' and g[side]['rows'][s]['empty']==('ROWS',[]),('CP17_R5_02_EMPTY_OR_MULTIROW',s,side,str(g[side]['rows'][s])[:400])
                    for i,a in enumerate(args):
                        assert ('ROWS',sorted((v for o,v in multi[1] if o==i),key=nulls))==keyed[s][key(a)],('CP17_R5_02_MULTIROW_DIFFERS_FROM_ONE_CALL',s,side,i)
                po_rows=[book([v for o,v in g[side]['rows'][PO_BOOK]['multirow'][1] if o==i]) for i in range(4)]
                life_rows=[amounts([v for o,v in g[side]['rows'][LIFECYCLE]['multirow'][1] if o==i]) for i in range(4)]
                assert po_rows==[[full],[ZERO],[ZERO],[full]],('CP17_R5_02_MULTIROW_BOOK',side,po_rows)
                assert life_rows==[[24],[-12],[None],[24]],('CP17_R5_02_MULTIROW_LIFECYCLE',side,life_rows)
            oracles['final']=dict(multirow_readers=len(g['chosen']),po_multirow=[[[str(v) for v in b] for b in r] for r in po_rows],
                                  lifecycle_multirow=[[None if v is None else str(v) for v in r] for r in life_rows],empty_answers_equal_and_empty=True)
        finally:
            cur.execute('rollback to savepoint cp17_r5_02_same');cur.execute('release savepoint cp17_r5_02_same');bd.api.admin(cur)
        assert report_accounts.verify(cur)==report,'CP17_R5_02_READERS_NOT_RESTORED'
        # A reader compared on nothing proves nothing: each must answer at least one input, the three readers the books lack
        # rows for with a value (a non-zero number or a non-empty text; 0, NULL and {} are not values).
        idle=[s for s,c in compared.items() if not c['answered']]
        valueless=[s for s in ('erp.bb_opening_credit_account_v1(uuid)','erp.pocket_period_book_v1(uuid)',LIFECYCLE) if not compared[s]['with_value']]
        assert len(compared)==len(report_accounts.READERS) and not idle and not valueless,('CP17_R5_02_READER_NOT_EXERCISED',idle,valueless,compared)
        assert len(g['chosen'])==len(report_accounts.READERS),('CP17_R5_02_MULTIROW_NOT_EVERY_READER',sorted(set(report_accounts.READERS)-set(g['chosen'])))
        return dict(status='PASS',reviewed=report,fixture=built,inputs_compared=compared,same_rows_or_same_refusal=True,
                    old_graph_installed_together=True,old_graph_nested_reader_calls=g['nested'],literal_oracles=oracles)
    def readers_reviewed():
        bd.api.admin(cur);clean=report_accounts.verify(cur)
        signature='erp.run_v268_financial_report_checks()'
        installed=cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
        old=report_accounts.unwrap(signature,installed)
        refusals={}
        def refused(label,fn):
            try:fn()
            except AssertionError as e:refusals[label]=str(e.args[0][0] if isinstance(e.args[0],tuple) else e.args[0]);return
            raise AssertionError(('CP17_R5_02_REVIEW_ACCEPTED',label))
        # A reader that gained one more literal call, a key outside the core list, or text already wrapped is refused.
        refused('one_more_call',lambda:report_accounts.wrap(signature,old.replace("begin","begin perform erp.account_id('WIP');",1)))
        refused('unlisted_key',lambda:report_accounts.wrap(signature,old.replace("erp.account_id('WIP')","erp.account_id('LABOR_COST')",1)))
        refused('already_wrapped',lambda:report_accounts.wrap(signature,installed))
        # The install refuses a predecessor whose literal calls changed.
        cur.execute('savepoint cp17_r5_02_review')
        try:
            cur.execute(old.replace("begin","begin perform erp.account_id('WIP');",1))
            try:cur.execute(report_accounts.block(signature));raise AssertionError('CP17_R5_02_INSTALL_ACCEPTED_CHANGED_READER')
            except psycopg.errors.RaiseException as e:refusals['install_changed_reader']=str(e).split('\n')[0]
        finally:cur.execute('rollback to savepoint cp17_r5_02_review');cur.execute('release savepoint cp17_r5_02_review');bd.api.admin(cur)
        # Every key is a core mapping: deleting one is refused by the Native guard.
        cur.execute('savepoint cp17_r5_02_mapping')
        try:
            try:cur.execute("delete from erp.accounting_account_mappings where mapping_key='WIP'");raise AssertionError('CP17_R5_02_CORE_MAPPING_DELETED')
            except psycopg.errors.RaiseException as e:refusals['core_mapping_delete']=str(e).split('\n')[0]
        finally:cur.execute('rollback to savepoint cp17_r5_02_mapping');cur.execute('release savepoint cp17_r5_02_mapping');bd.api.admin(cur)
        assert len(refusals)==5,refusals
        return dict(status='PASS',reviewed=clean,refusals=refusals)

    named=[sol_valid_repair_nota,wrong_or_missing_still_found,readers_same_answer,readers_reviewed]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):return []


def http_cases(http,today):return []
