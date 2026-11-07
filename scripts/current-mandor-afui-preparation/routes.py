"""Exact source-only adoption of the current Afui parent and report writer."""
from hashlib import sha256

BASE = 'c296fd06167ddd177e1192c1008992e2a1e3d628'
BASE_TREE = 'fdd36962a7de81482ccca02e6ff96597cfc20081'
AFUI = 'fd797083eab093d9dc97f2d52ca61dc37812b437'
AFUI_TREE = '02a8812e9eae2272a976d1dbd1e21aff8c022467'
PRIOR_AFUI = '76b3f1e1bcce49cc405e55f92a733dcd0f360cad'
NS = 'scripts/current-mandor-shop-native-qualification/'
PINS = {
    'additional_cases.py': (11438, '2fef6edab13d9b7fcf716fb85a5e8da08dc1d144713109950fc29cb8b9cedfa9'),
    'advisor_review.py': (8140, '4bfe15aedd3d61228f7f59b8b863b6109b8c8d6779797ccf0e9b9f4fe9da17e8'),
    'cases.py': (11526, 'fefe8106c36976a4853703244f2cc3b48f9bf2b93b95a5b9bbe9a42a2773d8fd'),
    'oracle.py': (5845, '046702c7847e85d74c0f928e4d3db5dd86867272317f5618fbe7f3d444851230'),
    'native_fixture.py': (21060, '8036269e118b7a657205f9c167090d4aca47b1b9cb44b1828507d8a9d1699384'),
    'runtime_prerequisites.py': (8078, '282b13f9d2b6bfe89b30a88adb117d8eceeea97d09a8f7ce8ba502ed15d33d58'),
    'test_runtime_prerequisites.py': (10212, 'c55310b1bb7051403ecb9dbabdac41c083e7ee48f36b75d15c9b321f8c16236e'),
    'assembly.py': (5817, 'e734356cace6a72b7f3614cd56170d9b1b1ad5645293b933693ae8f5eccd041a'),
    'admission.py': (1447, '609db7cade09a03be8aa4777adac6e11fdf3fc5aec672e625ed96705381e3b6c'),
    'qualification.py': (7161, '3f4bf0cfccbf650240729e01909dcb39b3e88371e59ee14a3bffc5f05934de0b'),
    'component.py': (7956, '31b7626e2488fd4371daa2bf21254583b86299673b91130eb0736778126f5044'),
    'access_runtime.py': (8404, '4718579f49a6ad7cc5b4ac0e229d474a61dfe8e13f0e544b6ecf3ac49699a487'),
    'browser_observer.py': (3746, '0458e0314827d2ff2b7c1ac13157e7fc34730f7231289b515c29c280594250f4'),
    'browser_gate.py': (10213, '8b213c1f7bc4232b9edc43471c16e4b0aeb5404c9784359024d9242074a019ad'),
    'preflight.py': (10968, 'ea789817b7ec0c48ca3fb702c5f1a8045853438f87302ea38d81f89595a5069d'),
}


PRODUCT_GUARD = 'scripts/cp7_mandor_shop/payment_guards.sql'
PRODUCT_PIN = (10946, '0405c0a9c807ef0be3881c2a32c69a152e2a0614bc8efb1f5572ac715683d771')

TERMINAL_REPAIR = {
    'advisor_review.py': (("PLAN_PIN=dict(bytes=13274,sha256='341f2cbd4a0e361bee275f9e66a15c5362a8cee9d3ba91e619b95f376aa7098a')\n", "PLAN_PIN=dict(bytes=13274,sha256='677cd27d61a44b875b9d0745fbba7eeb1c23588093fad299e7639c07c5dc2316')\n"),),
    'native_fixture.py': (
        ('        require(cur.execute(\'select count(*)from erp.payroll_work_items where payroll_id=%s::uuid\',(payroll,)).fetchone()==(0,),\'MANDOR_NATIVE_EMPTY_DRAFT_WEEK_REQUIRED\')\n        row=cur.execute("update erp.payroll_settlements set period_start=%s,period_end=%s,"\n            "payment_date=case when %s then null else payment_date end,"\n            "payment_cash_account_id=case when %s then null else payment_cash_account_id end "\n            "where id=%s::uuid and status=\'DRAFT\' returning id::text",(start,end,back<0,back<0,payroll)).fetchone()\n        require(row==(payroll,),\'MANDOR_NATIVE_ONLY_NEW_EMPTY_DRAFT_WEEK\')\n        self.modules.bc.boundary.historical.prior.set_open_period(cur,today)\n',
         '        require(cur.execute(\'select count(*)from erp.payroll_work_items where payroll_id=%s::uuid\',(payroll,)).fetchone()==(0,),\'MANDOR_NATIVE_EMPTY_DRAFT_WEEK_REQUIRED\')\n        row=cur.execute("update erp.payroll_settlements set period_start=%s,period_end=%s,"\n            "payment_cash_account_id=case when %s then null else payment_cash_account_id end "\n            "where id=%s::uuid and status=\'DRAFT\' returning id::text",(start,end,back<0,payroll)).fetchone()\n        require(row==(payroll,),\'MANDOR_NATIVE_ONLY_NEW_EMPTY_DRAFT_WEEK\')\n        self.modules.bc.boundary.historical.prior.set_open_period(cur,today)\n'),
        ("        require(row[0]==f['contractor']and row[3]=='DRAFT','MANDOR_NATIVE_EXPLICIT_SAME_MANDOR_DRAFT_PAYROLL')\n        require(row[1:3]==(str(start),str(end)),'MANDOR_NATIVE_EXPLICIT_SELECTED_WHOLE_WEEK')\n        if back<0:require(start>today and row[4:] == (None,None),'MANDOR_NATIVE_FUTURE_DRAFT_HAS_NO_PRETENDED_PAYMENT')\n        require(row[1]!=f['sale_at'][:10],'MANDOR_NATIVE_MANUALLY_DISTINCT_PAYROLL_PERIOD')\n        return payroll\n",
         "        require(row[0]==f['contractor']and row[3]=='DRAFT','MANDOR_NATIVE_EXPLICIT_SAME_MANDOR_DRAFT_PAYROLL')\n        require(row[1:3]==(str(start),str(end)),'MANDOR_NATIVE_EXPLICIT_SELECTED_WHOLE_WEEK')\n        # Native requires a date on DRAFT. The inherited placeholder has no cash account.\n        if back<0:require(start>today and row[4:] == (today,None),'MANDOR_NATIVE_FUTURE_DRAFT_HAS_NO_PRETENDED_PAYMENT')\n        require(row[1]!=f['sale_at'][:10],'MANDOR_NATIVE_MANUALLY_DISTINCT_PAYROLL_PERIOD')\n        return payroll\n"),
    ),
    'cases.py': (
        ("    held2=n.allocation(cur,f,payroll,'200000.00');before_cancel=n.observe(cur,f,payroll)\n    reply,call=n.payroll_command(cur,f,payroll,'CANCEL');after_cancel=n.observe(cur,f,payroll)\n    automatic=oracle.released(before_cancel,after_cancel,'200000.00')\n    oracle.require(after_cancel['payroll']['status']=='REVERSED','MANDOR_NATIVE_UNPAID_CANCELLATION_STATUS')\n    oracle.require(all(x['state']=='RELEASED'for x in after_cancel['allocation_states']),'MANDOR_NATIVE_CANCEL_MUST_RELEASE_ALL_ALLOCATIONS')\n    return dict(status='PASS',physical=physical,sale=sale,reserve=held,release=released,explicit_release=explicit,\n        second_reserve=held2,cancel=reply,automatic_release=automatic,cancel_replay=n.replay(cur,call,reply))\n",
         "    held2=n.allocation(cur,f,payroll,'200000.00');before_cancel=n.observe(cur,f,payroll)\n    reply,call=n.payroll_command(cur,f,payroll,'CANCEL');after_cancel=n.observe(cur,f,payroll)\n    after_workspace=n.workspace(cur,f,payroll)\n    sale_id=f['sale']\n    before_card=next(x for x in held2['before_workspace']['cards'] if x['sale_id']==sale_id)\n    after_card=next(x for x in after_workspace['cards'] if x['sale_id']==sale_id)\n    automatic=oracle.cancelled_release(before_cancel,after_cancel,before_card,after_card,'200000.00')\n    oracle.require(after_workspace['can_change'] is False,'MANDOR_NATIVE_CANCELLED_PAYROLL_NOT_EDITABLE')\n    return dict(status='PASS',physical=physical,sale=sale,reserve=held,release=released,explicit_release=explicit,\n        second_reserve=held2,cancel=reply,automatic_release=automatic,cancel_replay=n.replay(cur,call,reply))\n"),
        ("def ordinary_store(n,cur,today):\n    f,physical=n.physical(cur,today);n.admin(cur)\n    f['customer']=str(n.modules.bd.chain.base.create_customer(cur,f['tag']))\n    before=n.sales.accounts(cur);value=D(str(n.modules.bd.lot_value(cur,f['lot'])))\n    payload=n.draft.payload(f,qty='4',price='75000',discount='0');key=uuid.uuid4()\n",
         "def ordinary_store(n,cur,today):\n    f,physical=n.physical(cur,today);n.admin(cur)\n    f['customer']=str(n.modules.bd.chain.base.create_customer(cur,f['tag'].removeprefix('MANDOR-NATIVE-')))\n    before=n.sales.accounts(cur);value=D(str(n.modules.bd.lot_value(cur,f['lot'])))\n    payload=n.draft.payload(f,qty='4',price='75000',discount='0');key=uuid.uuid4()\n"),
    ),
    'oracle.py': (
        ('\n\ndef reversal(before_approval,after_payment,after_reversal,amount):\n    amount=money(amount);unchanged_sale_assets(after_payment,after_reversal)\n',
         "\n\ndef cancelled_release(before,after,before_reservation,after_cancellation,amount):\n    amount=money(amount);unchanged_sale_assets(before,after)\n    require(deltas(before,after)=={},'MANDOR_ORACLE_RELEASE_OR_UNPAID_CANCEL_POSTED_MONEY')\n    require(before['invoice']==after['invoice'],'MANDOR_ORACLE_CANCEL_CHANGED_INVOICE')\n    require(after['payroll']['status']=='REVERSED','MANDOR_NATIVE_UNPAID_CANCELLATION_STATUS')\n    require(after['payroll']['net_payable']==before['payroll']['net_payable'],'MANDOR_ORACLE_CANCEL_REWROTE_HISTORICAL_NET')\n    old={row['allocation_id']:row for row in before['allocation_states']}\n    new={row['allocation_id']:row for row in after['allocation_states']}\n    require(set(old)==set(new)and all(row['state']=='RELEASED'for row in new.values()),\n        'MANDOR_NATIVE_CANCEL_MUST_RELEASE_ALL_ALLOCATIONS')\n    reserved=sum(money(str(row['amount'])) for row in old.values() if row['state']=='RESERVED')\n    require(reserved==amount,'MANDOR_ORACLE_CANCEL_WRONG_RESERVED_AMOUNT')\n    require(money(after_cancellation['available_to_reserve'])==money(before_reservation['available_to_reserve'])\n        and money(after_cancellation['allocated_amount'])==money(before_reservation['allocated_amount']),\n        'MANDOR_ORACLE_CANCEL_DID_NOT_RETURN_EXACT_INVOICE_CAPACITY')\n    return dict(status='PASS',released=str(amount),cash_delta='0',invoice_paid_delta='0',\n        historical_payroll_net_unchanged=True,invoice_capacity_restored=True)\n\n\ndef reversal(before_approval,after_payment,after_reversal,amount):\n    amount=money(amount);unchanged_sale_assets(after_payment,after_reversal)\n"),
    ),
    'payment_guards.sql': (
        ("    raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_JOURNAL_INSERT_REQUIRED';end if;\n  else\n   select *into s_ from cp7_mandor_shop.settlements where journal_id=j_.id and id=j_.source_id;\n   if ctx_.action not in('REOPEN','REVERSE')or work_.native_before_status is distinct from'PAID'\n    or s_.id is null or s_.payroll_id is distinct from work_.payroll_id\n    or old_.status is distinct from'POSTED'or j_.status is distinct from'REVERSED'\n    or(to_jsonb(j_)-array['status','updated_at'])is distinct from(to_jsonb(old_)-array['status','updated_at'])then\n    raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_REVERSAL_REQUIRED';end if;\n  end if;\n",
         "    raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_JOURNAL_INSERT_REQUIRED';end if;\n  else\n   -- PostgreSQL computes period_shifted after BEFORE triggers from the protected dates.\n   select *into s_ from cp7_mandor_shop.settlements where journal_id=j_.id and id=j_.source_id;\n   if ctx_.action not in('REOPEN','REVERSE')or work_.native_before_status is distinct from'PAID'\n    or s_.id is null or s_.payroll_id is distinct from work_.payroll_id\n    or old_.status is distinct from'POSTED'or j_.status is distinct from'REVERSED'\n    or(to_jsonb(j_)-array['status','updated_at','period_shifted'])is distinct from(to_jsonb(old_)-array['status','updated_at','period_shifted'])then\n    raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_REVERSAL_REQUIRED';end if;\n  end if;\n"),
        ("   raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_INVERSE_REQUIRED';end if;\n  if tg_op='UPDATE'and(old_.reversal_of_id is not null or j_.reversal_of_id is distinct from original_.id\n   or(to_jsonb(j_)-array['reversal_of_id','updated_at'])is distinct from(to_jsonb(old_)-array['reversal_of_id','updated_at']))then\n   raise exception 'CP7_MANDOR_SHOP_PROTECTED_INVERSE_HISTORY_IMMUTABLE';end if;\n end if;\n",
         "   raise exception 'CP7_MANDOR_SHOP_EXACT_OWNING_OFFSET_INVERSE_REQUIRED';end if;\n  if tg_op='UPDATE'and(old_.reversal_of_id is not null or j_.reversal_of_id is distinct from original_.id\n   or(to_jsonb(j_)-array['reversal_of_id','updated_at','period_shifted'])is distinct from(to_jsonb(old_)-array['reversal_of_id','updated_at','period_shifted']))then\n   raise exception 'CP7_MANDOR_SHOP_PROTECTED_INVERSE_HISTORY_IMMUTABLE';end if;\n end if;\n"),
    ),
}

def replacements(name):
    if name == 'native_fixture.py':
        return (
            ('from datetime import timedelta\n',
             'from datetime import timedelta\nfrom zoneinfo import ZoneInfo\n'),
            ('ROOT=HERE.parents[1]\n',
             "ROOT=HERE.parents[1]\nWIB=ZoneInfo('Asia/Jakarta')\n"),
            ('        sale_at,sale_day,after_good=cur.execute("select(statement_timestamp()at time zone\'Asia/Jakarta\'),"',
             '        # Keep the database instant intact when the sales RPC parses the payload in UTC.\n        sale_at,sale_day,after_good=cur.execute("select statement_timestamp(),"'),
            ('            sale_at=sale_at.isoformat())\n',
             '            sale_at=sale_at.astimezone(WIB).isoformat())\n'),
            ('        now=cur.execute("select(statement_timestamp()at time zone\'Asia/Jakarta\')").fetchone()[0]\n        return self.sale_intent(cur,f,\'RETURN\',dict(return_number=\'MANDOR-RET-\'+uuid.uuid4().hex[:12],\n            physical_at=now.isoformat(),notes=\'Return one actual sold piece after lawful offset reversal\',',
             '        now=cur.execute("select statement_timestamp()").fetchone()[0]\n        return self.sale_intent(cur,f,\'RETURN\',dict(return_number=\'MANDOR-RET-\'+uuid.uuid4().hex[:12],\n            physical_at=now.astimezone(WIB).isoformat(),notes=\'Return one actual sold piece after lawful offset reversal\','),
        ) + TERMINAL_REPAIR[name] + (
            ("    def payroll(self,cur,f,today,*,gross='2000000.00',back=7):\n        self.admin(cur)\n", "    def payroll(self,cur,f,today,*,gross='2000000.00',back=7,keep_posting_day_open=False):\n        self.admin(cur)\n        if keep_posting_day_open:\n            require(cur.execute('select erp.resolve_accounting_transaction_date(%s::date)',(today,)).fetchone()==(today,),\n                'MANDOR_NATIVE_RETURN_POSTING_DAY_MUST_REMAIN_OPEN')\n"),
            ('        self.modules.bc.boundary.historical.prior.set_open_period(cur,today)\n', '        if not keep_posting_day_open:\n            self.modules.bc.boundary.historical.prior.set_open_period(cur,today)\n'),
        )
    if name == 'additional_cases.py':
        return (('def correction_return(n,cur,today):\n    from cases import approved,pay\n    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f);payroll=n.payroll(cur,f,today)\n', 'def correction_return(n,cur,today):\n    from cases import approved,pay\n    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f)\n    # This sale and return share the current open WIB posting day.\n    payroll=n.payroll(cur,f,today,keep_posting_day_open=True)\n'),)
    if name == 'runtime_prerequisites.py':
        return (
            ("        actor['permissions']={key:cur.execute('select erp.has_permission(%s)',(key,)).fetchone()[0]for key in PERMISSIONS}\n",
             "        access=cur.execute('select public.erp_get_my_access_v1()').fetchone()[0]\n        profile=access.get('profile') if type(access) is dict else None\n        permissions=access.get('permissions') if type(access) is dict else None\n        if (type(profile) is not dict or access.get('allowed') is not True\n            or profile.get('role_code')!='OWNER' or profile.get('is_active') is not True\n            or type(permissions) is not list or any(type(key) is not str for key in permissions)):\n            raise ValueError('MANDOR_PREREQUISITE_EXACT_ORDINARY_OWNER_ACCESS_SNAPSHOT_REQUIRED')\n        actor['permission_source']='public.erp_get_my_access_v1()'\n        actor['permissions']={key:key in permissions for key in PERMISSIONS}\n"),
            ("    actor=value['owner_actor'];require(actor['identity']==['authenticated','authenticated','OWNER'],'ORDINARY_OWNER_REQUIRED')\n",
             "    actor=value['owner_actor'];require(actor['identity']==['authenticated','authenticated','OWNER'],'ORDINARY_OWNER_REQUIRED')\n    require(actor.get('permission_source')=='public.erp_get_my_access_v1()','EXACT_OWNER_PUBLIC_ACCESS_SOURCE_REQUIRED')\n"),
        )
    if name == 'test_runtime_prerequisites.py':
        return (
            ("        elif 'erp.has_permission' in query:rows=[(self.permissions[args[0]],)]\n",
             "        elif 'public.erp_get_my_access_v1' in query:\n            rows=[(dict(allowed=True,profile=dict(role_code='OWNER',is_active=True),\n                permissions=[key for key,allowed in self.permissions.items() if allowed]),)]\n"),
            ("            self.assertEqual(model.calls.count('original_actor'),1)\n",
             "            self.assertEqual(model.calls.count('original_actor'),1)\n            self.assertEqual(model.calls.count('select public.erp_get_my_access_v1()'),1)\n            self.assertFalse(any('erp.has_permission' in sql for sql in model.calls))\n"),
            ("                lambda v:v['owner_actor']['permissions'].__setitem__(prerequisites.PERMISSIONS[0],1),\n",
             "                lambda v:v['owner_actor']['permissions'].__setitem__(prerequisites.PERMISSIONS[0],1),\n                lambda v:v['owner_actor'].pop('permission_source'),\n"),
        )
    if name == 'assembly.py':
        return (('        self.domain_modules=self.fixture.admitted_modules(cur,qualified_Afui)\n', "        from importlib.util import module_from_spec, spec_from_file_location\n        path=ROOT/'scripts/current-mandor-afui-preparation/report_io.py'\n        spec=spec_from_file_location('mandor_afui_fixture_admission',path)\n        report_io=module_from_spec(spec);spec.loader.exec_module(report_io)\n        self.domain_modules=report_io.admit_afui_fixture(cur,qualified_Afui,self.fixture)\n"),)
    if name == 'preflight.py':
        return (
            ("admission['PARENT_HEAD']=='" + PRIOR_AFUI + "'", "admission['PARENT_HEAD']=='" + AFUI + "'"),
            ("admission['PARENT_TREE']=='b3182ae21e3981e91d6d3730ec4ffb33dce1afb4'",
             "admission['PARENT_TREE']=='" + AFUI_TREE + "'"),
            ("admission['PARENT_RUN']==41596005356", "admission['PARENT_RUN'] is None"),
            ("admission['PARENT_JOB']==125783405360", "admission['PARENT_JOB'] is None"),
        )
    if name == 'admission.py':
        return (
            ("PARENT_HEAD='" + PRIOR_AFUI + "'", "PARENT_HEAD='" + AFUI + "'"),
            ("PARENT_TREE='b3182ae21e3981e91d6d3730ec4ffb33dce1afb4'", "PARENT_TREE='" + AFUI_TREE + "'"),
            ('PARENT_RUN=41596005356', 'PARENT_RUN=None'),
            ('PARENT_JOB=125783405360', 'PARENT_JOB=None'),
        )
    if name == 'qualification.py':
        return (
            ('    text,engine_proof=package_engine.derive(original.read_bytes())\n',
             '    text,engine_proof=package_engine.derive(original.read_bytes())\n'
             "    report_io=load('mandor_current_complete_report_writer',ROOT/'scripts/current-mandor-afui-preparation/report_io.py')\n"
             "    text,output_proof=report_io.derive_packet(text,'mandor17')\n"
             '    text=report_io.derive_parent_install(text)\n'
             "    output_proof['exact_parent_install_authority_route']=True\n"
             '    engine_proof=dict(retained_complete_engine=engine_proof,complete_report_output=output_proof)\n'),
            ("    engine=ModuleType('writer_a_mandor_exact_whole_package_engine');engine.__file__=str(original)\n",
             "    engine=ModuleType('writer_a_mandor_exact_whole_package_engine');engine.__file__=str(original)\n"
             '    engine.__dict__[report_io.HELPER]=report_io.write_complete\n'
             '    engine.install_qualified_parent=lambda cur:report_io.install_qualified_parent(cur,product.parent().install)\n'),
            ("ROOT/'scripts/current-unified-candidate/check_source.py'", "ROOT/'scripts/current-mandor-afui-preparation/check_source.py'"),
            ("        original=engine.package._writer_runtime;original_output=engine.package.OUT\n        try:\n            engine.package._writer_runtime=lambda browser_mode=False:engine.run()\n            # Only the artifact destination moves to the owning candidate;\n            # the original package and complete backup drill remain exact.\n            engine.package.OUT=ROOT/'cp6-proof/t3'\n            import package_identity\n            with package_identity.scope(),attempts.single_attempt(business_day):engine.package.run('install')\n        finally:\n            engine.package._writer_runtime=original;engine.package.OUT=original_output\n",
             "        import package_identity\n        report_io=load('mandor_scoped_package_identity',ROOT/'scripts/current-mandor-afui-preparation/report_io.py')\n        run_package=report_io.private_package_run(engine.package,ROOT/'cp6-proof/t3',lambda browser_mode=False:engine.run())\n        with report_io.package_identity_scope(package_identity),attempts.single_attempt(business_day):run_package('install')\n"),
        )
    if name == 'component.py':
        return (
            ('    import cp7_cash_funding as funding\n    from assembly import FROZEN\n',
             "    from assembly import FROZEN\n    # The strict group can cache a same-named helper from the SKU worktree.\n    funding = load('mandor_exact_afui_cash_funding', FROZEN/'scripts/cp7_cash_funding.py')\n"),
            ('    observed=native.strict_group(NATIVE_LABEL,factory,verify)\n',
             "    report_io=load('mandor_current_owning_group_report_writer',ROOT/'scripts/current-mandor-afui-preparation/report_io.py')\n"
             "    output=load('mandor_current_complete_case_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
             "    with report_io.group_scope(native.r1),output.case_scope(native,'native'):\n"
             '        observed=native.strict_group(NATIVE_LABEL,factory,verify)\n'),
            ("        raw=path.read_bytes()\n"
             "        if target.exists():require(target.read_bytes()==raw,'MANDOR_NATIVE_FIRST_STRICT_ORIGINAL_CHANGED')\n"
             "        else:\n"
             "            with target.open('xb')as output:output.write(raw)\n"
             "        originals.append(source_record(target))\n",
             "        originals.append(output.copy_exact(path,target))\n"),
        )
    if name == 'browser_observer.py':
        return ((
            '    docs=[]\n'
            "    for name,env in(('MANDOR_BROWSER_FIXTURE.json','MANDOR_BROWSER_FIXTURE_SHA256'),\n"
            "            ('MANDOR_BROWSER_STATE.json','MANDOR_BROWSER_STATE_SHA256')):\n"
            "        path=ROOT/'cp6-proof/t3'/name;require(not path.is_symlink(),'MANDOR_BROWSER_NO_INPUT_SYMLINK')\n"
            "        data=path.read_bytes();require(sha256(data).hexdigest()==os.environ[env],'MANDOR_BROWSER_EXACT_OWNING_ORIGINAL')\n"
            '        docs.append(json.loads(data))\n'
            '    fixture,state=docs\n',
            '    import access_runtime\n'
            "    directory=ROOT/'cp6-proof/t3'\n"
            "    path=directory/'MANDOR_BROWSER_FIXTURE.json'\n"
            "    require(not path.is_symlink(),'MANDOR_BROWSER_NO_INPUT_SYMLINK')\n"
            '    data=path.read_bytes()\n'
            "    require(sha256(data).hexdigest()==os.environ['MANDOR_BROWSER_FIXTURE_SHA256'],'MANDOR_BROWSER_EXACT_OWNING_ORIGINAL')\n"
            '    fixture=json.loads(data)\n'
            "    state_io=access_runtime.load('mandor_complete_browser_state',ROOT/'scripts/current-mandor-afui-preparation/state_io.py')\n"
            "    state=state_io.observer_state(fixture,directory,os.environ['MANDOR_BROWSER_STATE_SHA256'],\n"
            "        os.environ['MANDOR_BROWSER_STATE_CACHE_SHA256'])\n"),)
    if name == 'browser_gate.py':
        return ((
            "    state=pinned(p,directory,part['browser_state_original'],'MANDOR_BROWSER_STATE.json')\n",
            "    state_io=access_runtime.load('mandor_final_complete_state_io',access_runtime.ROOT/'scripts/current-mandor-afui-preparation/state_io.py')\n"
            "    state=state_io.verified(p,directory,part['browser_state_original'],part['browser_state_cache_original'])\n"
            "    p.exact(fixture['observer_catalogue'],state_io.observer_catalogue(state,part['browser_state_original'],\n"
            "        part['browser_state_cache_original']),'MANDOR_BROWSER_OBSERVER_CATALOGUE_MATCHES_FULL_DECODED_STATE')\n"),)
    if name == 'access_runtime.py':
        save = (
            "    path=ROOT/'cp6-proof/t3'/name\n"
            "    raw=(json.dumps(value,sort_keys=True,default=str)+'\\n').encode()\n"
            "    require(not path.exists(),'MANDOR_FIRST_SESSION_ORIGINAL_OVERWRITE_REFUSED')\n"
            "    path.parent.mkdir(parents=True,exist_ok=True)\n"
            "    with path.open('xb')as stream:stream.write(raw)\n"
            "    return dict(name=path.name,bytes=len(raw),sha256=sha256(raw).hexdigest())\n",
            "    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
            "    return output.save_access(value,name)\n")
        scoped = []
        for key in ('access_copy_authority', 'http_copy_authority', 'browser_copy_authority'):
            before = "    with copy_scope(modes,product,state)as copies:\n        report['" + key + "']=copies\n"
            after = ("    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
                     "    with output.case_scope(modes,'copies',retention=access_cases),copy_scope(modes,product,state)as copies:\n"
                     "        report['" + key + "']=copies\n")
            scoped.append((before, after))
        state_routes = (
            ("        MANDOR_BROWSER_STATE_SHA256=report['browser_state_original']['sha256'],\n",
             "        MANDOR_BROWSER_STATE_SHA256=report['browser_state_original']['sha256'],\n"
             "        MANDOR_BROWSER_STATE_CACHE_SHA256=report['browser_state_cache_original']['sha256'],\n"),
            ("    report['browser_fixture_original']=save(fixture,'MANDOR_BROWSER_FIXTURE.json')\n"
             "    report['browser_state_original']=save(state,'MANDOR_BROWSER_STATE.json')\n"
             "    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n",
             "    report['browser_state_original']=save(state,'MANDOR_BROWSER_STATE.json')\n"
             "    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')\n"
             '    state_io=output.load_state_io()\n'
             "    report['browser_state_cache_original']=state_io.reference(report['browser_state_original'])\n"
             "    catalogue=state_io.observer_catalogue(state,report['browser_state_original'],report['browser_state_cache_original'])\n"
             "    report['browser_fixture_original']=save(dict(fixture,observer_catalogue=catalogue),'MANDOR_BROWSER_FIXTURE.json')\n"),
        )
        return (save, *scoped, *state_routes)
    if name in TERMINAL_REPAIR:
        return TERMINAL_REPAIR[name]
    raise ValueError('MANDOR_CURRENT_ONLY_REVIEWED_CALLER_SOURCES')


def derive(raw, name):
    expected = PRODUCT_PIN if name == 'payment_guards.sql' else PINS.get(name)
    if (len(raw), sha256(raw).hexdigest()) != expected:
        raise ValueError('MANDOR_CURRENT_EXACT_PREPARED_CALLER_SOURCE_REQUIRED:' + name)
    source = raw.decode()
    routes = replacements(name)
    for before, after in routes:
        if source.count(before) != 1 or after in source:
            raise ValueError('MANDOR_CURRENT_ONE_EXACT_CALLER_ROUTE_REQUIRED:' + name)
        source = source.replace(before, after, 1)
    restored = source
    for before, after in reversed(routes):
        if restored.count(after) != 1:
            raise ValueError('MANDOR_CURRENT_ONE_EXACT_INVERSE_ROUTE_REQUIRED:' + name)
        restored = restored.replace(after, before, 1)
    if restored.encode() != raw:
        raise ValueError('MANDOR_CURRENT_COMPLETE_PREPARED_CALLER_NOT_RECOVERED:' + name)
    if name != 'payment_guards.sql':
        compile(source, 'current-mandor-afui-caller::' + name, 'exec', dont_inherit=True)
    return source.encode(), dict(original_bytes=len(raw), original_sha256=expected[1],
                                 derived_sha256=sha256(source.encode()).hexdigest(), exact_routes=len(routes),
                                 whole_original_caller_recovered=True, actual_ERP_cases=0, production_go=False)
