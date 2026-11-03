"""Actual-domain Mandor helpers; no connection, install or scenario on import.

The owning caller must first admit the accepted Afui parent, acquire its real
domain modules BEFORE composing Mandor, and verify the combined installation.
Draft payroll headers use the existing unmodified fixture; posted invoice,
stock, COGS, approval, payment and reversals use existing public commands.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from hashlib import sha256
import gzip,json,uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def require(value,message):
    if not value:raise ValueError(message)


def local(cur):
    c=cur.connection.info
    require(c.host in('127.0.0.1','localhost')and c.port==54322,'MANDOR_NATIVE_ONLY_DISPOSABLE_LOOPBACK')
    require(cur.execute('select current_database()').fetchone()==('cp6_rollback',),'MANDOR_NATIVE_ONLY_ROLLBACK_DATABASE')
    require(cur.execute("select current_setting('transaction_isolation')").fetchone()==('read committed',),'MANDOR_NATIVE_FRESH_READ_COMMITTED')


class Native:
    """A reviewed caller context, never a replacement for an ERP domain module."""
    def __init__(self,modules,afui_fixture,finish,master,sales,draft,mandor,mandor_state,*,funding,scope='NATIVE9'):
        self.modules=modules;self.afui_fixture=afui_fixture;self.finish=finish
        self.master=master;self.sales=sales;self.draft=draft;self.mandor=mandor;self.state=mandor_state
        self.funding=funding
        require(scope in('NATIVE9','COMMITTED_USE'),'MANDOR_NATIVE_FIXED_OBSERVATION_SCOPE')
        self.scope=scope;self.observation=0

    def admin(self,cur):
        # Refuse a remote or wrong database before even changing its session.
        local(cur);self.modules.bc.api.admin(cur)

    def committed_foundation(self,cur):
        """Recreate the original foundation after strict_group rolls it back.

        The ordinary fixture can seed only an empty local copy. Existing
        users and roles must already be valid; this never promotes them.
        """
        self.admin(cur);api=self.modules.bc.api
        count=cur.execute('select count(*) from erp.app_users').fetchone()[0]
        require(type(count)is int and count>=0,'MANDOR_NATIVE_EXACT_FIXTURE_USER_COUNT_REQUIRED')
        if count==0:api.seed(cur)
        self.admin(cur)
        rows=cur.execute('select u.is_active,r.role_code,r.is_active from erp.app_users u '
            'join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s',
            (api.base.OPERATOR_AUTH,)).fetchall()
        require(rows==[(True,'OWNER',True)],'MANDOR_NATIVE_ORIGINAL_ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION')
        return dict(status='ORIGINAL_ORDINARY_OWNER_FOUNDATION_READY',initial_app_users=count,
            unchanged_original_foundation_loaded=count==0,existing_actor_or_role_promoted=False,
            product_permission_grants_added=False,actual_case_credit=0)

    def public(self,cur,query,args,actor):
        self.admin(cur);local(cur)
        self.sales.auth.actor(cur,actor)
        value=cur.execute(query,args).fetchone()[0]
        self.admin(cur)
        return value

    def boundary(self,cur):
        self.admin(cur);local(cur)
        with self.modules.control.product_catalog(cur):
            self.mandor.verify(cur,self.state)
            catalogue=self.modules.product.runtime()[-1]
            return dict(actual_all22=catalogue._catalog_rows(cur),full_data_and_sequences=catalogue._data(cur))

    def original(self,label,value):
        """Retain complete observations once; keep huge metadata out of logs."""
        require(label in('REPLAY_BEFORE','REPLAY_AFTER','REFUSAL_BEFORE','REFUSAL_AFTER'),'MANDOR_NATIVE_FIXED_OBSERVATION_LABEL')
        self.observation+=1
        name=f'MANDOR_{self.scope}_{self.observation:04d}_{label}.json.gz'
        raw=(json.dumps(value,sort_keys=True,separators=(',',':'),default=str)+'\n').encode()
        packed=gzip.compress(raw,mtime=0);directory=ROOT/'cp6-proof/t3/MANDOR_NATIVE_ORIGINALS'
        directory.mkdir(parents=True,exist_ok=True);path=directory/name
        require(not path.exists(),'MANDOR_NATIVE_FIRST_ORIGINAL_OVERWRITE_REFUSED:'+name)
        with path.open('xb')as output:output.write(packed)
        return dict(path='MANDOR_NATIVE_ORIGINALS/'+name,raw=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),
            compressed=dict(bytes=len(packed),sha256=sha256(packed).hexdigest()),complete_actual22_data_and_sequences=True)

    def replay(self,cur,operation,expected):
        before=self.boundary(cur);actual=operation();after=self.boundary(cur)
        require(actual==expected,'MANDOR_NATIVE_REPLAY_REPLY_CHANGED')
        require(after==before,'MANDOR_NATIVE_REPLAY_CHANGED_DATA_CATALOGUE_OR_SEQUENCE')
        return dict(status='PASS',reply=actual,before_original=self.original('REPLAY_BEFORE',before),
            after_original=self.original('REPLAY_AFTER',after),full_observations_equal=True)

    def refusal(self,cur,operation,message,*,sqlstate='P0001'):
        require(sqlstate in('P0001','42501'),'MANDOR_NATIVE_FIXED_REFUSAL_SQLSTATE')
        before=self.boundary(cur);cur.execute('savepoint mandor_native_expected_refusal')
        caught=None
        try:operation()
        except Exception as error:
            caught=error
        finally:
            cur.execute('rollback to savepoint mandor_native_expected_refusal')
            cur.execute('release savepoint mandor_native_expected_refusal')
        self.admin(cur)
        require(caught is not None and getattr(caught,'sqlstate',None)==sqlstate,'MANDOR_NATIVE_REAL_EXPECTED_SQL_REFUSAL_REQUIRED')
        primary=getattr(getattr(caught,'diag',None),'message_primary',None)
        require(primary==message,'MANDOR_NATIVE_UNEXPECTED_REFUSAL:'+str(primary))
        after=self.boundary(cur)
        require(before==after,'MANDOR_NATIVE_REFUSAL_CHANGED_DATA_CATALOGUE_OR_SEQUENCE')
        return dict(status='PASS',SQLSTATE=sqlstate,message=primary,before_original=self.original('REFUSAL_BEFORE',before),
            after_original=self.original('REFUSAL_AFTER',after),full_observations_equal=True)

    def physical(self,cur,today):
        self.admin(cur);local(cur)
        require(cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()==(today,),'MANDOR_NATIVE_GENUINE_WIB_DATE_REQUIRED')
        # The corrected Afui fixture creates every new commercial master at
        # the genuine database clock. Its pickup/receipt lineage remains an
        # earlier physical fact, while GOOD and the sale happen today.
        f=self.afui_fixture.prepare(cur,today,self.modules)
        self.afui_fixture.post_good(cur,self.modules,f)
        result=self.finish.finish_command(cur,self.finish.finish_workspace(cur,f['po']),
            reason='Actual Mandor invoice fixture: finish real production and GOOD before sale')
        self.admin(cur)
        require(self.finish.po_state(cur,f['po'])['status']=='FINISHED','MANDOR_NATIVE_REAL_FINISHED_PO_REQUIRED')
        require(self.finish.po_wip_balance(cur,f['po'])==0,'MANDOR_NATIVE_FINISHED_PO_ZERO_WIP_REQUIRED')
        require(self.modules.bd.lot_value(cur,f['lot'])>0,'MANDOR_NATIVE_POSITIVE_KNOWN_FINISHED_HPP_REQUIRED')
        sale_at,sale_day,after_good=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta'),"
            "(statement_timestamp()at time zone'Asia/Jakarta')::date,statement_timestamp()>%s::timestamptz",
            (f['good_payload']['physical_at'],)).fetchone()
        require(sale_day==today and after_good is True,'MANDOR_NATIVE_SALE_MUST_FOLLOW_CURRENT_GOOD_AT_GENUINE_CLOCK')
        actor=self.master.role_actor(cur,'OWNER');tag='MANDOR-NATIVE-'+uuid.uuid4().hex[:12]
        sale=dict(f,actor=actor,tag=tag,location=self.modules.bd.chain.base.LOCATION,
            sale_at=sale_at.isoformat())
        require(f['good_day']==today and f['day']<today,'MANDOR_NATIVE_EARLIER_PHYSICAL_LINEAGE_CURRENT_GOOD_REQUIRED')
        return sale,dict(finished=result,physical_day=str(f['day']),good_day=str(f['good_day']),
            sale_at=sale['sale_at'],genuine_database_clock=True,actor=actor)

    def create_invoice(self,cur,f,amount='300000.00'):
        self.admin(cur)
        code=cur.execute('select contractor_code from erp.contractors where id=%s::uuid',
            (f['contractor'],)).fetchone()[0]
        options=self.public(cur,'select public.erp_cp7_get_mandor_shop_buyers_v1(%s,%s,null,25)',
            ('CREATE',code),f['actor'])
        choices=[x for x in options['rows']if x['contractor_id']==f['contractor']]
        require(len(choices)==1 and choices[0]['can_select']is True,'MANDOR_NATIVE_EXPLICIT_ACTIVE_BUYER_REQUIRED')
        buyer=choices[0];f['customer']=buyer['customer_id']
        # Four actual PCS, no synthetic FG/HPP/payment row is inserted.
        unit=Decimal(amount)/4;require(unit==unit.quantize(Decimal('.01')),'MANDOR_NATIVE_EXACT_PRICE_FIXTURE')
        payload=self.draft.payload(f,qty='4',price=str(unit),discount='0')
        payload['mandor_buyer']=dict(contractor_id=f['contractor'],review_token=buyer['review_token'])
        key=uuid.uuid4();before=self.sales.accounts(cur)
        def create():return self.public(cur,'select public.erp_cp7_save_mandor_shop_sale_v1(%s,%s::jsonb,%s::uuid,null)',
            ('CREATE',json.dumps(payload),key),f['actor'])
        made=create();f['sale']=made['sale_id']
        f['customer']=cur.execute('select customer_id::text from erp.sales_headers where id=%s::uuid',(f['sale'],)).fetchone()[0]
        replay=self.replay(cur,create,made)
        require(self.sales.accounts(cur)==before,'MANDOR_NATIVE_DRAFT_MUST_NOT_POST_MONEY')
        review,version=self.sale_review(cur,f);post_key=uuid.uuid4()
        def post():return self.sales.command(cur,'POST',review,version,post_key,f['actor'])
        posted=post();post_replay=self.replay(cur,post,posted)
        require(posted['status']=='POSTED','MANDOR_NATIVE_EXISTING_INVOICE_POST_REQUIRED')
        state=self.invoice(cur,f)
        require(Decimal(state['paid'])==0 and Decimal(state['outstanding'])==Decimal(amount),'MANDOR_NATIVE_SAME_UNPAID_INVOICE_REQUIRED')
        return dict(payload=payload,created=made,create_replay=replay,posted=posted,post_replay=post_replay,invoice=state)

    def payroll(self,cur,f,today,*,gross='2000000.00',back=7):
        self.admin(cur)
        # Reuse the unchanged existing fixture to create a DRAFT header only.
        # This is an explicit Native manual adjustment, not seeded wages or
        # an invented posted payable; Native APPROVE owns expense recognition.
        payroll=self.modules.bc.payroll(cur,f['accessory'],today,gross,back)
        selected=today-timedelta(days=back);start=selected-timedelta(days=selected.weekday());end=start+timedelta(days=6)
        # Extend the newly created empty DRAFT to the explicitly selected whole
        # week. This changes no posted financial fact or authoritative source.
        require(cur.execute('select count(*)from erp.payroll_work_items where payroll_id=%s::uuid',(payroll,)).fetchone()==(0,),'MANDOR_NATIVE_EMPTY_DRAFT_WEEK_REQUIRED')
        row=cur.execute("update erp.payroll_settlements set period_start=%s,period_end=%s,"
            "payment_date=case when %s then null else payment_date end,"
            "payment_cash_account_id=case when %s then null else payment_cash_account_id end "
            "where id=%s::uuid and status='DRAFT' returning id::text",(start,end,back<0,back<0,payroll)).fetchone()
        require(row==(payroll,),'MANDOR_NATIVE_ONLY_NEW_EMPTY_DRAFT_WEEK')
        self.modules.bc.boundary.historical.prior.set_open_period(cur,today)
        row=cur.execute('select contractor_id::text,period_start::text,period_end::text,status,payment_date,payment_cash_account_id from erp.payroll_settlements where id=%s::uuid',
            (payroll,)).fetchone()
        require(row[0]==f['contractor']and row[3]=='DRAFT','MANDOR_NATIVE_EXPLICIT_SAME_MANDOR_DRAFT_PAYROLL')
        require(row[1:3]==(str(start),str(end)),'MANDOR_NATIVE_EXPLICIT_SELECTED_WHOLE_WEEK')
        if back<0:require(start>today and row[4:] == (None,None),'MANDOR_NATIVE_FUTURE_DRAFT_HAS_NO_PRETENDED_PAYMENT')
        require(row[1]!=f['sale_at'][:10],'MANDOR_NATIVE_MANUALLY_DISTINCT_PAYROLL_PERIOD')
        return payroll

    def payroll_document(self,cur,f,payroll):
        value=self.public(cur,'select public.erp_cp7_get_payroll_workspace_v1(%s,%s::jsonb)',
            ('WORK',json.dumps(dict(id=payroll,limit=25,offset=0))),f['actor'])
        require(value['document']['id']==payroll,'MANDOR_NATIVE_SELECTED_PAYROLL_READER')
        return value['document']

    def fund_payroll(self,cur,f,payroll,today):
        document=self.payroll_document(cur,f,payroll)
        amount=Decimal(document['net_payable'])
        require(amount>=0,'MANDOR_NATIVE_NONNEGATIVE_PAYROLL_FIXTURE')
        self.admin(cur)
        if amount:
            self.funding.fund(cur,f['accessory']['cash'],str(amount),today)
            self.admin(cur)
        return dict(amount=str(amount),payment_day=str(today),ordinary_Native_capital_command=bool(amount),
            seeded_posted_cash_or_journal=False)

    def payroll_command(self,cur,f,payroll,action,*,today=None,key=None):
        doc=self.payroll_document(cur,f,payroll)
        payload=dict(id=payroll,review_token=doc['review_token'],change_reason='Actual Mandor financial review and selected payroll')
        if action=='PAY':payload.update(payment_date=str(today),cash_account_id=f['accessory']['cash'])
        request=key or uuid.uuid4()
        def call():return self.public(cur,'select public.erp_cp7_save_payroll_v1(%s,%s::jsonb,%s::uuid,%s)',
            (action,json.dumps(payload),request,doc['row_version']),f['actor'])
        reply=call()
        return reply,call

    def workspace(self,cur,f,payroll):
        return self.public(cur,'select public.erp_cp7_get_mandor_shop_payroll_v1(%s::uuid,null)',(payroll,),f['actor'])

    def sale_document(self,cur,f):
        return self.public(cur,'select public.erp_cp7_get_sales_v1(%s::jsonb)',
            (json.dumps(dict(q=f['tag'],sale_id=f['sale'])),),f['actor'])['detail']

    def sale_review(self,cur,f):
        document=self.sale_document(cur,f)
        require(document['id']==f['sale'],'MANDOR_NATIVE_EXACT_SALE_REVIEW_ACTOR_AND_ID')
        return dict(sale_id=document['id'],review_token=document['review_token'],
            change_reason='Review the same Mandor invoice and authoritative financial sources'),document['row_version']

    def sale_intent(self,cur,f,action,extra=None):
        payload,version=self.sale_review(cur,f);payload.update(extra or {});request=uuid.uuid4()
        def call():return self.public(cur,'select public.erp_cp7_save_sale_v1(%s,%s::jsonb,%s::uuid,%s)',
            (action,json.dumps(payload),request,version),f['actor'])
        return call

    def return_intent(self,cur,f):
        workspace=self.public(cur,'select public.erp_cp7_get_sales_returns_v1(%s::jsonb)',
            (json.dumps(dict(sale_id=f['sale'],kind='ALLOCATIONS')),),f['actor'])
        rows=workspace['page']['rows'];require(len(rows)==1,'MANDOR_NATIVE_SINGLE_REAL_SALE_ALLOCATION')
        self.admin(cur)
        now=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')").fetchone()[0]
        return self.sale_intent(cur,f,'RETURN',dict(return_number='MANDOR-RET-'+uuid.uuid4().hex[:12],
            physical_at=now.isoformat(),notes='Return one actual sold piece after lawful offset reversal',
            items=[dict(allocation_id=rows[0]['allocation_id'],location_id=f['location'],qty_pcs='1',
                quality_grade='GRADE_A',refund_amount='75000.00',notes='Original allocation and original selling price')]))

    def correction_intent(self,cur,f):
        d=self.sale_document(cur,f);require(len(d['items'])==1,'MANDOR_NATIVE_SINGLE_CORRECTED_LINE')
        payload=dict(sale_id=d['id'],review_token=d['review_token'],sale_number=d['number'],
            customer_id=d['customer_id'],source_location_id=d['location_id'],sale_date=d['physical_at'],
            due_date=d['due_date'],payment_terms=d['payment_terms'],notes=d['notes'],
            change_reason='Correct the original price after reversing the payroll offset',
            items=[dict(product_id=i['product_id'],qty_pcs=i['qty_pcs'],unit_price_snapshot='75001.00',
                discount_amount=i['financial']['discount'],notes=i['notes'])for i in d['items']])
        request=uuid.uuid4()
        def call():return self.public(cur,'select public.erp_cp7_correct_note_v1(%s::jsonb,%s::uuid,%s)',
            (json.dumps(payload),request,d['row_version']),f['actor'])
        return call

    def installments(self,cur,f,payroll):
        return self.public(cur,'select public.erp_cp7_get_payroll_installments_v1(%s::jsonb)',
            (json.dumps(dict(payroll_id=payroll)),),f['actor'])

    def installment_intent(self,cur,f,payroll,action,*,today=None,amount=None,payment=None):
        workspace=self.installments(cur,f,payroll);doc=workspace['document']
        require(doc['payroll_id']==payroll,'MANDOR_NATIVE_EXACT_INSTALLMENT_PAYROLL')
        payload=dict(payroll_id=payroll,review_token=doc['review_token'],
            change_reason='Review actual installment, selected invoice offset and current sources')
        if action=='PAY':
            self.admin(cur)
            # A private observer supplies the same source token shown by the
            # public reader; the monetary command keeps the ordinary actor.
            cash=cur.execute('select cp7_installment.cash(%s::uuid)',(f['accessory']['cash'],)).fetchone()[0]
            require(cash is not None and cash['eligible']is True,'MANDOR_NATIVE_ELIGIBLE_INSTALLMENT_CASH_REQUIRED')
            payload.update(amount=amount,payment_date=str(today),cash_account_id=cash['id'],cash_review_token=cash['review_token'])
        elif action=='REVERSE_PAYMENT':payload['payment_id']=payment
        else:require(action=='REVERSE_PAYROLL','MANDOR_NATIVE_FIXED_INSTALLMENT_ACTION')
        request=uuid.uuid4()
        def call():return self.public(cur,'select public.erp_cp7_save_payroll_installment_v1(%s,%s::jsonb,%s::uuid,%s)',
            (action,json.dumps(payload),request,doc['row_version']),f['actor'])
        return call

    def allocation(self,cur,f,payroll,amount,*,release=None,key=None):
        workspace=self.workspace(cur,f,payroll)
        require(workspace['payroll_id']==payroll and workspace['contractor_id']==f['contractor'],'MANDOR_NATIVE_SELECTED_WEEK_AND_IDENTITY')
        cards=[x for x in workspace['cards']if x['sale_id']==f['sale']]
        require(len(cards)==1,'MANDOR_NATIVE_ONE_SAME_INVOICE_CARD')
        card=cards[0];action='RELEASE'if release else'RESERVE'
        payload=dict(contract_version='cp7.mandor-shop-allocation-command.v1',payroll_id=payroll,
            sale_id=f['sale'],review_token=card['review_token'])
        if release:payload['allocation_id']=release
        else:payload['amount']=str(amount)
        request=key or uuid.uuid4()
        def call():return self.public(cur,'select public.erp_cp7_save_mandor_shop_allocation_v1(%s,%s::jsonb,%s::uuid)',
            (action,json.dumps(payload),request),f['actor'])
        reply=call();replay=self.replay(cur,call,reply)
        return dict(before_workspace=workspace,payload=payload,reply=reply,replay=replay)

    def invoice(self,cur,f):
        self.admin(cur)
        row=cur.execute('select erp.sale_net_total(%s::uuid)::text,cp7_credit.current_effective_paid(%s::uuid)::text,customer_id::text,status from erp.sales_headers where id=%s::uuid',
            (f['sale'],f['sale'],f['sale'])).fetchone()
        require(row is not None,'MANDOR_NATIVE_SAME_INVOICE_EXISTS')
        return dict(sale_id=f['sale'],net=row[0],paid=row[1],outstanding=str(Decimal(row[0])-Decimal(row[1])),customer_id=row[2],status=row[3])

    def observe(self,cur,f,payroll):
        self.admin(cur);invoice=self.invoice(cur,f)
        balances={k:str(v)for k,v in self.sales.accounts(cur).items()}
        inventory={}
        for table in ['fg_stock_movements','fg_inventory_balances','hpp_versions','hpp_version_components','sale_stock_allocations']:
            # The table names are fixed observer source, never caller input.
            inventory[table]=cur.execute('select coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),\'[]\'::jsonb)from erp.'+table+' t').fetchone()[0]
        payments=cur.execute('select coalesce(jsonb_agg(to_jsonb(p)order by p.id),\'[]\'::jsonb)from erp.sales_payments p where p.sale_id=%s::uuid',(f['sale'],)).fetchone()[0]
        states=cur.execute('select coalesce(jsonb_agg(to_jsonb(s)order by s.allocation_id),\'[]\'::jsonb)from cp7_mandor_shop.allocation_states s where s.sale_id=%s::uuid',(f['sale'],)).fetchone()[0]
        return dict(invoice=invoice,payroll=self.payroll_document(cur,f,payroll),balances=balances,
            inventory=inventory,ordinary_sales_payment_rows=payments,allocation_states=states)
