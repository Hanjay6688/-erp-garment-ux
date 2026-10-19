"""Fable r5 probe on 17fa2507 (R5-02, owner D17-2). Oracle fixed before any run.

FABLE_R5:READERS_MAPPING_EDITS — R5-02 claim: each of the eleven readers whose literal erp.account_id('<KEY>') became
  (select erp.account_id('<KEY>')) answers exactly as the same reader with the inline call. The writer's CP17 cases compare
  the readers on fixed mappings and refuse one core delete; this probe attacks the mapping itself.
  Before-copies are rebuilt by Fable from the installed text (own inverse regex, independent of the writer's unwrap) into
  schema fable_r5, same attributes. Both run in one context (database owner session with the owner's claims), each answer
  inside its own savepoint, compared as sorted rows (to_jsonb) or as sqlstate + first message line.
  Inputs: the no-argument readers, three owner snapshot windows, and up to 25 ids per uuid reader that the disposable book
  holds (products, POs, pocket periods, opening settlements, sale journal/PO pairs).
  States, each inside a rolled-back savepoint, written straight to erp.accounting_account_mappings with its triggers active:
   BASE;
   for each of the 17 core keys: REMAP (account_id pointed to another active account of the same type, an existing one or
   a copy of the mapped account), NULL (account_id set null), DELETE, RENAME (mapping_key changed);
   MULTI_ROW: every uuid reader called on all its inputs inside one query.
  Refused edits are recorded with their message; accepted ones are compared.
  COUNTEREXAMPLE: in any accepted state an installed reader and its before-copy give different rows or a different refusal
  for the same input.
  FAIL (not meaningful): no reader compared in BASE. INCOMPLETE: no REMAP could be made for any key (recorded why).
"""
import json,re
import psycopg
import cp7_r5_cases as r5
import cp7_report_accounts_bundle as accounts

bd=r5.bd
WRAPPED=re.compile(r"\(select erp\.account_id\('([A-Z0-9_]+)'\)\)")


def cases(cur,today):
    def q(sql,args=()):return cur.execute(sql,args).fetchall()
    def one(sql,args=()):return cur.execute(sql,args).fetchone()[0]

    def probe():
        out=dict(readers={},states={},edits={})
        bd.api.admin(cur);cur.execute('savepoint fable_r5_case')
        try:
            cur.execute('create schema fable_r5')
            for signature in accounts.READERS:
                name=signature.split('(')[0];installed=one('select pg_get_functiondef(%s::regprocedure)',(signature,))
                before,n=WRAPPED.subn(lambda m:"erp.account_id('%s')"%m.group(1),installed)
                head='FUNCTION '+name+'('
                assert n>0 and '(select erp.account_id(' not in before and before.count(head)==1,('FABLE_R5_BEFORE_COPY',signature,n)
                cur.execute(before.replace(head,'FUNCTION fable_r5.'+name.split('.')[1]+'(',1),prepare=False)
                out['readers'][signature]=dict(wrapped_calls=n)
            ids=lambda sql:[(r[0],) for r in q(sql)]
            windows=[(today,today,today),(today.replace(day=1),today,today),(today.replace(year=today.year-1),today,today)]
            inputs={s:[()] for s in accounts.READERS}
            inputs.update({
                'erp.bb_opening_credit_account_v1(uuid)':ids('select id from erp.opening_subledger_settlements order by id limit 25'),
                'erp.compute_non_po_product_hpp_book_v2620f(uuid)':ids('select id from erp.products order by id limit 25'),
                'erp.compute_po_hpp_gl_book_v2620e(uuid)':ids('select id from erp.production_orders order by id limit 25'),
                'erp.get_owner_financial_snapshot_v2(date,date,date)':windows,
                'erp.pocket_period_book_v1(uuid)':ids('select id from erp.pocket_periods order by id limit 25'),
                'erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)':[tuple(r) for r in q(
                    """select distinct l.journal_entry_id,l.po_id from erp.journal_lines l join erp.journal_entries e on e.id=l.journal_entry_id
                       where l.po_id is not null and e.source_type in('SALE','SALES_RETURN') order by 1,2 limit 25""")]})
            out['inputs']={s:len(v) for s,v in inputs.items()}

            def answer(fn,a):
                bd.api.admin(cur);cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=r5.OWNER_AUTH,role='authenticated')),))
                cur.execute('savepoint fable_r5_call')
                try:
                    rows=q('select to_jsonb(x)::text from '+fn+'('+','.join(['%s']*len(a))+') x',a)
                    return ('ROWS',sorted(r[0] for r in rows))
                except psycopg.Error as e:
                    cur.execute('rollback to savepoint fable_r5_call');return ('ERR',e.sqlstate,str(e).split('\n')[0])
                finally:
                    cur.execute('release savepoint fable_r5_call');bd.api.admin(cur)

            def compare(label,limit=None):
                diffs=[];n=0;errs=0
                for signature in accounts.READERS:
                    name=signature.split('(')[0]
                    for a in inputs[signature][:limit]:
                        new,old=answer(name,a),answer('fable_r5.'+name.split('.')[1],a);n+=1;errs+=new[0]=='ERR'
                        if new!=old:diffs.append(dict(reader=signature,args=str(a),installed=str(new)[:300],before=str(old)[:300]))
                out['states'][label]=dict(compared=n,refusals=errs,differences=diffs[:5],difference_count=len(diffs))
                return diffs

            bad=[]
            bad+=compare('BASE')
            # MULTI_ROW: each uuid reader over all its inputs inside one query.
            multi=[]
            for signature in accounts.READERS:
                args=inputs[signature]
                if len(args)<2 or len(args[0])!=1:continue
                name=signature.split('(')[0]
                def agg(fn):
                    bd.api.admin(cur);cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=r5.OWNER_AUTH,role='authenticated')),))
                    cur.execute('savepoint fable_r5_call')
                    try:return ('ROWS',sorted(r[0] for r in q('select to_jsonb(x)::text from unnest(%s::uuid[]) i(id) cross join lateral '+fn+'(i.id) x',([a[0] for a in args],))))
                    except psycopg.Error as e:cur.execute('rollback to savepoint fable_r5_call');return ('ERR',e.sqlstate,str(e).split('\n')[0])
                    finally:cur.execute('release savepoint fable_r5_call');bd.api.admin(cur)
                new,old=agg(name),agg('fable_r5.'+name.split('.')[1])
                multi.append(dict(reader=signature,inputs=len(args),same=new==old,installed=str(new)[:200] if new!=old else None,before=str(old)[:200] if new!=old else None))
                if new!=old:bad.append(dict(state='MULTI_ROW',reader=signature))
            out['states']['MULTI_ROW']=multi

            fk=q("""select confrelid::regclass::text from pg_constraint where conrelid='erp.accounting_account_mappings'::regclass and contype='f'
                    and conkey=array[(select attnum from pg_attribute where attrelid='erp.accounting_account_mappings'::regclass and attname='account_id')]""")
            acct=fk[0][0] if fk else None;out['account_table']=acct
            cols={r[0] for r in q("select attname from pg_attribute where attrelid=%s::regclass and attnum>0 and not attisdropped",(acct,))} if acct else set()
            remaps=0
            for key in accounts.KEYS:
                ed=out['edits'][key]={}
                current=one('select account_id::text from erp.accounting_account_mappings where mapping_key=%s',(key,))
                def attempt(label,sql,args):
                    bd.api.admin(cur);cur.execute('savepoint fable_r5_edit')
                    try:
                        cur.execute('reset role');cur.execute(sql,args);bd.api.admin(cur)
                        ed[label]='ACCEPTED';d=compare(label+'_'+key,limit=10)
                        if d:bad.append(dict(state=label,key=key,first=d[0]))
                        return True
                    except psycopg.Error as e:
                        ed[label]='REFUSED: '+str(e).split('\n')[0][:200];return False
                    finally:cur.execute('rollback to savepoint fable_r5_edit');cur.execute('release savepoint fable_r5_edit');bd.api.admin(cur)
                # REMAP: another active account of the expected type, else a copy of the mapped account with a new id and code.
                other=None
                if acct and 'account_type' in cols:
                    filt=' and is_active' if 'is_active' in cols else ''
                    r=q('select a.id::text from '+acct+' a where a.account_type::text=(select account_type::text from '+acct+' where id=%s) and a.id<>%s'+filt+' order by a.id limit 1',(current,current))
                    other=r[0][0] if r else None
                if other:
                    remaps+=attempt('REMAP','update erp.accounting_account_mappings set account_id=%s where mapping_key=%s',(other,key))
                elif acct and 'code' in cols:
                    remaps+=attempt('REMAP',"""with c as(insert into """+acct+""" select (jsonb_populate_record(null::"""+acct+""",to_jsonb(a)||jsonb_build_object('id',gen_random_uuid(),'code',a.code||'-F5'))).* from """+acct+""" a where a.id=%s returning id)
                                         update erp.accounting_account_mappings set account_id=(select id from c) where mapping_key=%s""",(current,key))
                else:ed['REMAP']='NOT_ATTEMPTED: no account table/type column found'
                attempt('NULL','update erp.accounting_account_mappings set account_id=null where mapping_key=%s',(key,))
                attempt('DELETE','delete from erp.accounting_account_mappings where mapping_key=%s',(key,))
                attempt('RENAME',"update erp.accounting_account_mappings set mapping_key=mapping_key||'_FABLE' where mapping_key=%s",(key,))
            base=out['states']['BASE']['compared']
            out.update(remaps_compared=remaps,counterexamples=bad[:10],counterexample_count=len(bad),
                       status='COUNTEREXAMPLE' if bad else ('FAIL' if not base else ('PASS' if remaps else 'INCOMPLETE')),
                       oracle='R5-02: installed reader and its before-copy answer alike in every accepted mapping state')
            return out
        finally:
            cur.execute('rollback to savepoint fable_r5_case');cur.execute('release savepoint fable_r5_case');bd.api.admin(cur)

    return [('FABLE_R5:READERS_MAPPING_EDITS',probe)]

def races(tools,today):return []
def http_cases(http,today):return []
