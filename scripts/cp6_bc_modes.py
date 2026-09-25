"""BC (writer): two-session races and real-HTTP cases of the accessory service workflow (auditor round 11, item 4: "race dua sesi,
HTTP Auth"), run in the auditor runtime (cp6-auditor-scenario.yml, phase after = the candidate with BC) as the writer's own
scenario file. Label: WRITER_SCENARIO on the auditor runtime, not independent evidence, not release evidence.

Oracles (written before the runs, from the contract and the BC probe oracles, r9_acc_oracle.md D01/D02/D04 and C02):
  RACE  the second session waits for the first (a row or advisory lock the first holds) and, once the first commits, is refused
        with the capacity code; when the first aborts, the second succeeds. Stock never goes negative and is used once.
          D01 two internal uses of 4 from a warehouse holding 7            -> 'stock would become negative'; stock 3 either way
          D02 a service-post fill of 4 vs a mandor note of 4 on stock 7    -> the later one refused; stock 3 either way
          C02 two inspections of the same 10 returned pieces               -> BC_INSPECT_EXCEEDS_WAITING (the probe's C02 code); 10 inspected once
          RET two return receipts of 2 on one note line of 3               -> BC_RETURN_EXCEEDS_SOURCE; 2 received once
          D04 a note return credit vs the payroll draft taking the same note line: afterwards the payroll deduction never
              exceeds what is still collectible (0 < allocated <= collectible; a populate refused by the kasbon guard because it
              read the note before the credit committed must succeed on a retry) and the books equal the subledger
          POL two owner policy changes from the same version                 -> STALE_VERSION; one version step
  HTTP  real Auth users through the real PostgREST: OWNER fills a service post; GUDANG (can view accessories, cannot adjust
        stock) and anon are refused and nothing changes; GUDANG reads the workspace without values (M:10.2); ADMIN may not set
        an owner policy (BC_OWNER_ONLY).
"""
from datetime import timedelta
import json,uuid
import cp6_bc_probe as bcp

api=bcp.api
D=bcp.D


def _fixture(tools,today,stock_qty=7,cost='2.00'):
    with tools.connect() as conn,conn.cursor() as cur:
        fx=bcp.fixture(cur,today,stock_qty=stock_qty,cost=cost);conn.commit()
    return fx


def _stock(tools,fx,location='main'):
    with tools.connect() as conn,conn.cursor() as cur:
        value=bcp.stock(cur,fx['material'],fx[location]);conn.rollback()
    return value


def _clean(tools):
    with tools.connect() as conn,conn.cursor() as cur:
        rows=bcp.findings(cur);conn.rollback()
    return {k:v for k,v in rows.items() if k!=bcp.STALE_F2}


def _verdict(race,commit,held,contention,outcome,code,state,ok_state):
    refused=not outcome.get('ok') and code in (outcome.get('message') or '')
    ok=(contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True
        and (refused if commit else outcome.get('ok') is True) and ok_state)
    return dict(status='PASS' if ok else 'FAIL',race=race,first_committed=commit,held=str(held)[:300],contention=contention,second=outcome,state=state,
                expected=dict(second='REFUSED '+code if commit else 'SUCCEEDS'))


def _use(fx,qty,day):
    def op(cur):
        return bcp.use(cur,fx,fx['main'],[(qty,day,9,'FACTORY_USE')])['document_id']
    return op


def d01_two_uses(tools,today,commit):
    day=today-timedelta(days=1);fx=_fixture(tools,today)
    held,contention,outcome=tools.two_sessions(_use(fx,4,day),_use(fx,4,day),commit)
    left=_stock(tools,fx);findings=_clean(tools)
    return _verdict('D01_TWO_USES',commit,held,contention,outcome,'stock would become negative',dict(stock=str(left),findings=findings),
                    left==3 and not findings)


def _fill(fx,qty,day):
    def op(cur):return bcp.fill(cur,fx,qty,day)['document_id']
    return op


def _note(fx,qty,day):
    def op(cur):return bcp.note(cur,fx,qty,'3.00',day)[0]
    return op


def d02_fill_vs_note(tools,today,commit):
    day=today-timedelta(days=1);fx=_fixture(tools,today)
    held,contention,outcome=tools.two_sessions(_fill(fx,4,day),_note(fx,4,day),commit)
    left=_stock(tools,fx);findings=_clean(tools)
    return _verdict('D02_FILL_VS_NOTE',commit,held,contention,outcome,'stock would become negative',dict(stock=str(left),findings=findings),
                    left==3 and not findings)


def _received_lot(tools,fx,day,qty=10):
    with tools.connect() as conn,conn.cursor() as cur:
        lot=bcp.receive(cur,fx,'TEARDOWN',[(qty,None)],day,8,reference='BC race')['lot_ids'][0];conn.commit()
    return lot


def _inspect(fx,lot,day):
    # A teardown return has no book value yet: inspection classifies it where it lies (it enters stock only through valuation).
    def op(cur):return bcp.inspect(cur,lot,bcp.local_at(day,9),'Ani',usable=10)['document_id']
    return op


def c02_two_inspections(tools,today,commit):
    day=today-timedelta(days=1);fx=_fixture(tools,today,stock_qty=100)
    lot=_received_lot(tools,fx,day)
    held,contention,outcome=tools.two_sessions(_inspect(fx,lot,day),_inspect(fx,lot,day),commit)
    with tools.connect() as conn,conn.cursor() as cur:
        state=bcp.lot_state(cur,lot);conn.rollback()
    findings=_clean(tools)
    return _verdict('C02_TWO_INSPECTIONS',commit,held,contention,outcome,'BC_INSPECT_EXCEEDS_WAITING',
                    dict(lot={k:str(v) for k,v in state.items()},findings=findings),
                    state['inspected_usable']==10 and state['waiting']==0 and not findings)


def _note_line(tools,fx,day,qty=3):
    with tools.connect() as conn,conn.cursor() as cur:
        issue,item=bcp.note(cur,fx,qty,'3.00',day);conn.commit()
    return issue,item


def _receive_note(fx,item,day,qty):
    def op(cur):return bcp.receive(cur,fx,'NOTE_RETURN',day=day,hour=10,note_item_id=item,qty=str(qty))['lot_ids'][0]
    return op


def ret_two_receipts(tools,today,commit):
    day=today-timedelta(days=1);fx=_fixture(tools,today,stock_qty=100)
    _,item=_note_line(tools,fx,day-timedelta(days=1))
    held,contention,outcome=tools.two_sessions(_receive_note(fx,item,day,2),_receive_note(fx,item,day,2),commit)
    with tools.connect() as conn,conn.cursor() as cur:
        received=bcp.one(cur,"""select coalesce(sum(l.qty_received),0) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
            where l.note_item_id=%s and d.status='POSTED'""",item);conn.rollback()
    return _verdict('RET_TWO_RECEIPTS',commit,held,contention,outcome,'BC_RETURN_EXCEEDS_SOURCE',dict(received=str(received)),received==2)


def d04_credit_vs_payroll(tools,today,first):
    """A note of 10 @ 3.00 (30.00), 5 returned and inspected usable; ACC-DEC05 CREDIT_UNPAID_ONLY. One session credits the 5
    returned pieces (15.00 off the unpaid receivable), the other populates the mandor's draft payroll, which takes what is
    collectible. Either order: payroll never deducts more than is collectible and the books equal the subledger."""
    day=today-timedelta(days=1);fx=_fixture(tools,today,stock_qty=100)
    issue,item=_note_line(tools,fx,day-timedelta(days=2),qty=10)
    with tools.connect() as conn,conn.cursor() as cur:
        lot=bcp.receive(cur,fx,'NOTE_RETURN',day=day-timedelta(days=1),hour=10,note_item_id=item,qty='5')['lot_ids'][0]
        bcp.inspect(cur,lot,bcp.local_at(day-timedelta(days=1),11),'Ani',usable=5)
        bcp.policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
        # A payroll deducts a note only from what it pays (earnings 100.00 here), as in the probe's C09.
        payroll=bcp.payroll(cur,fx,today,'100.00',1);conn.commit()
    def credit(cur):return bcp.credit(cur,lot,'USABLE',5,bcp.local_at(day,9),fx['main'])['document_id']
    def populate(cur):
        api.admin(cur);cur.execute('grant usage on schema erp to authenticated');bcp.session(cur)
        cur.execute('select erp.populate_payroll_draft(%s)',(payroll,));api.admin(cur);cur.execute('revoke usage on schema erp from authenticated')
        return 'POPULATED'
    ops=dict(CREDIT=credit,PAYROLL=populate);other='PAYROLL' if first=='CREDIT' else 'CREDIT'
    held,contention,outcome=tools.two_sessions(ops[first],ops[other],True)
    # A populate that waited on the credit read the note before the credit committed; the kasbon guard refuses that stale
    # amount atomically. The payroll must then populate on a retry with what is still collectible (never stuck).
    retried=None
    if first=='CREDIT' and not outcome.get('ok'):
        with tools.connect() as conn,conn.cursor() as cur:
            retried=populate(cur);conn.commit()
    with tools.connect() as conn,conn.cursor() as cur:
        collectible=bcp.one(cur,'select erp.bc_note_item_collectible_v1(%s)',item)
        allocated=bcp.one(cur,'select erp.bc_note_item_allocated_v1(%s)',item)
        books=abs(bcp.gl(cur,'MATERIAL_INVENTORY')-bcp.subledger_value(cur))<=D('0.05')
        conn.rollback()
    findings=_clean(tools)
    ok=D(0)<D(str(allocated))<=D(str(collectible)) and books and not findings and (outcome.get('ok') is True or bool(outcome.get('message')))
    return dict(status='PASS' if ok else 'FAIL',race='D04_CREDIT_VS_PAYROLL',first=first,held=str(held)[:300],contention=contention,second=outcome,retried=retried,
                state=dict(collectible=str(collectible),allocated=str(allocated),books_equal_subledger=books,findings=findings),
                expected='0 < allocated <= collectible, books = subledger, detectors clean')


def pol_two_owner_sets(tools,today):
    with tools.connect() as conn,conn.cursor() as cur:
        version=next(p for p in bcp.ws(cur)['policies'] if p['key']=='ACC-DEC01')['version'];conn.commit()
    def op(cur):
        return bcp.svc(cur,'SET_POLICY',dict(policy_key='ACC_DEC01',operation='SET',expected_version=version,reason='BC race policy',
                                             value=dict(mode='BOTH_REAL_TIMELINES')))['status']
    held,contention,outcome=tools.two_sessions(op,op,True)
    with tools.connect() as conn,conn.cursor() as cur:
        after=next(p for p in bcp.ws(cur)['policies'] if p['key']=='ACC-DEC01');conn.rollback()
    ok_state=int(after['version'])==int(version)+1 and after['status']=='SET'
    return _verdict('POL_TWO_OWNER_SETS',True,held,contention,outcome,'STALE_VERSION',dict(before=version,after=after['version']),ok_state)


def races(tools,today):
    return [('BC_RACE:D01_TWO_USES_FIRST_COMMITS',lambda:d01_two_uses(tools,today,True)),
            ('BC_RACE:D01_TWO_USES_FIRST_ABORTS',lambda:d01_two_uses(tools,today,False)),
            ('BC_RACE:D02_FILL_VS_NOTE_FIRST_COMMITS',lambda:d02_fill_vs_note(tools,today,True)),
            ('BC_RACE:D02_FILL_VS_NOTE_FIRST_ABORTS',lambda:d02_fill_vs_note(tools,today,False)),
            ('BC_RACE:C02_TWO_INSPECTIONS_FIRST_COMMITS',lambda:c02_two_inspections(tools,today,True)),
            ('BC_RACE:C02_TWO_INSPECTIONS_FIRST_ABORTS',lambda:c02_two_inspections(tools,today,False)),
            ('BC_RACE:RET_TWO_NOTE_RECEIPTS_FIRST_COMMITS',lambda:ret_two_receipts(tools,today,True)),
            ('BC_RACE:RET_TWO_NOTE_RECEIPTS_FIRST_ABORTS',lambda:ret_two_receipts(tools,today,False)),
            ('BC_RACE:D04_CREDIT_FIRST_THEN_PAYROLL',lambda:d04_credit_vs_payroll(tools,today,'CREDIT')),
            ('BC_RACE:D04_PAYROLL_FIRST_THEN_CREDIT',lambda:d04_credit_vs_payroll(tools,today,'PAYROLL')),
            ('BC_RACE:POL_TWO_OWNER_SETS_SAME_VERSION',lambda:pol_two_owner_sets(tools,today))]


# ---------------------------------------------------------------- real HTTP (Auth + PostgREST)

def _save(user,action,payload):
    return user.rpc('erp_save_accessory_service_action_v1',dict(p_action=action,p_payload=payload,p_client_request_id=str(uuid.uuid4())))


def http_cases(http,today):
    day=today-timedelta(days=1)

    def fill_roles():
        with http.connect() as conn,conn.cursor() as cur:
            fx=bcp.fixture(cur,today,stock_qty=20);conn.commit()
        owner=http.login('OWNER','bc-owner');store=http.login('GUDANG','bc-gudang')
        payload=dict(from_location_id=fx['main'],to_location_id=fx['SERVICE_POST'],physical_at=bcp.local_at(day,9),
                     items=[dict(material_id=fx['material'],qty='5')],reason='BC HTTP isi pos')
        check=lambda:str(_stock_http(http,fx,'SERVICE_POST'))
        before=check()
        denied=_save(store,'FILL_POST',payload)
        anon=http.anon_rpc('erp_save_accessory_service_action_v1',dict(p_action='FILL_POST',p_payload=payload,p_client_request_id=str(uuid.uuid4())))
        unchanged=check()
        done=_save(owner,'FILL_POST',payload)
        after=check()
        read=store.rpc('erp_get_accessory_service_workspace_v1',dict(p_filters=dict(query=fx['code'])))
        values=[s.get('value') for s in (read['body'] or {}).get('stock',[])] if read['status']==200 and isinstance(read['body'],dict) else None
        ok=(denied['status']>=400 and 'warehouse.stock.adjust' in json.dumps(denied['body']) and anon['status'] in (401,403) and unchanged==before
            and done['status']==200 and isinstance(done['body'],dict) and done['body'].get('status')=='POSTED' and D(after)==D(before)+5
            and read['status']==200 and bool(values) and all(v is None for v in values))
        return dict(status='PASS' if ok else 'FAIL',gudang=dict(status=denied['status'],body=str(denied['body'])[:300]),anon=dict(status=anon['status']),
                    owner=dict(status=done['status'],body=str(done['body'])[:300]),before=before,unchanged=unchanged,after=after,
                    gudang_read=dict(status=read['status'],values=values))

    def policy_owner_only():
        admin=http.login('ADMIN','bc-admin');owner=http.login('OWNER','bc-owner-policy')
        read=owner.rpc('erp_get_accessory_service_workspace_v1',dict(p_filters={}))
        version=next(p for p in read['body']['policies'] if p['key']=='ACC-DEC01')['version']
        payload=dict(policy_key='ACC_DEC01',operation='SET',expected_version=version,reason='BC HTTP policy',value=dict(mode='BOTH_REAL_TIMELINES'))
        refused=_save(admin,'SET_POLICY',payload)
        done=_save(owner,'SET_POLICY',payload)
        after=owner.rpc('erp_get_accessory_service_workspace_v1',dict(p_filters={}))
        now=next(p for p in after['body']['policies'] if p['key']=='ACC-DEC01')
        ok=(refused['status']>=400 and 'BC_OWNER_ONLY' in json.dumps(refused['body']) and done['status']==200
            and now['status']=='SET' and int(now['version'])==int(version)+1)
        return dict(status='PASS' if ok else 'FAIL',admin=dict(status=refused['status'],body=str(refused['body'])[:300]),
                    owner=dict(status=done['status'],body=str(done['body'])[:300]),policy=now)

    return [('BC_HTTP:FILL_POST_STOCK_ADJUST_ONLY_VALUES_HIDDEN',fill_roles),
            ('BC_HTTP:SET_POLICY_OWNER_ONLY',policy_owner_only)]


def _stock_http(http,fx,location):
    with http.connect() as conn,conn.cursor() as cur:
        value=bcp.stock(cur,fx['material'],fx[location]);conn.rollback()
    return value
