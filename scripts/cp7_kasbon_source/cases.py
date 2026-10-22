"""OW-08b kasbon Native cases: a kasbon journal and its cancellation open the kasbon from the ledger.

Kasbon rows and journals come only from the retained kasbon writer (erp_cp7_save_kasbon_v1). The original reader (as
left by OW06) is read side by side on the same state inside a rolled-back savepoint: it answered UNSUPPORTED_SOURCE for
CP7_KASBON, and it answers every other family exactly as the patched reader does.
"""
from datetime import timedelta
import json
import uuid

import psycopg

import cp7_cp17_fix_cases as c17
from cp7_kasbon_source import native_delta

auth,b=c17.auth,c17.b
IDS=('OW08B_KASBON_GIVE_JOURNAL_OPENS_KASBON',
     'OW08B_KASBON_CANCEL_INVERSE_OPENS_SAME_KASBON',
     'OW08B_KASBON_SOURCE_RIGHTS_AND_UNKNOWN_REFUSED',
     'OW08B_OTHER_SOURCE_FAMILIES_UNCHANGED')
ORIGINALS=None  # set by the probe: the exact OW06 reader this stage replaced
AS_OWNER=None   # set by the probe: OW06's verified function_ddl (replace as the reader's own owner)
AS_POSTGRES=None  # set by the probe: the verified installer switch to postgres (the harness admin role cannot run DDL)
BEFORE=None     # set by the probe: the captured catalog the DDL owner check reads


def one(cur,sql,args=()):
    return cur.execute(sql,args).fetchone()[0]


def resolve(cur,source_type,source_id,subject=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_resolve_transaction_source_v1(%s::jsonb)',(json.dumps(dict(source_type=source_type,source_id=str(source_id))),))
    b.api.admin(cur);return r


def original(cur,fn):
    """The same read through the exact OW06 reader, then restored."""
    name='ow08b_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_POSTGRES(cur,'postgres'):
            for sig in native_delta.SIGNATURES:
                with AS_OWNER(cur,sig,BEFORE):cur.execute(ORIGINALS[sig],prepare=False)
        b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)


def same(a,b_):
    strip=lambda r:{k:v for k,v in r.items()if k!='read_at'}
    return strip(a)==strip(b_)


def given(cur,today,amount='1200.00'):
    f=c17.s.review.fixture(cur,today);c=f['contractor'];day=c17.accrued_day(cur,c);bank=c17.s.cash(cur)
    kday=max(c17.funding.open_day(cur),day-timedelta(days=1))
    k=c17.kasbon_give(cur,c,bank,amount,kday)['advance'];b.api.admin(cur)
    journal=one(cur,"select id from erp.journal_entries where source_type='CP7_KASBON'and source_id=%s and status='POSTED'",(k['id'],))
    return dict(contractor=c,payroll=f['payroll'],bank=bank,day=kday,kasbon=k,journal=str(journal))


def expected(r,k,contractor,status):
    d=r['document']
    assert r['status']=='AVAILABLE'and r['business_DML']is False,r
    assert d=={'domain':'KASBON','route':'finance-payroll','id':k['id'],'number':k['number'],'status':status,'revision':None,
        'focus':{'kind':'KASBON','id':k['id'],'parent_id':contractor,'page_offset':0}},d


def cases(cur,today):
    def give():
        g=given(cur,today);k=g['kasbon']
        r=resolve(cur,'CP7_KASBON',k['id'])
        expected(r,k,g['contractor'],'GIVEN')
        old=original(cur,lambda:resolve(cur,'CP7_KASBON',k['id']))
        assert old['status']=='UNSUPPORTED_SOURCE'and old['document']is None,old
        line=one(cur,"select count(*)from erp.journal_lines where journal_entry_id=%s",(g['journal'],))
        return dict(status='PASS',kasbon=k['number'],before='UNSUPPORTED_SOURCE (sumber belum didukung)',after=r['document'],journal_lines=line)

    def cancel():
        g=given(cur,today,'800.00');k=g['kasbon']
        w=c17.kasbon_read(cur,g['contractor'])
        done=c17.kasbon(cur,'CANCEL',dict(contractor_id=g['contractor'],advance_id=k['id'],reason='OW08b kasbon salah catat'),w)
        assert done['advance']['status']=='CANCELLED',done
        inverse=one(cur,"select j.id from erp.journal_entries j join cp7_kasbon.advances a on a.cancel_journal_id=j.id where a.id=%s and j.reversal_of_id=a.journal_id",(k['id'],))
        kind,source=cur.execute('select source_type,source_id from erp.journal_entries where id=%s',(inverse,)).fetchone()
        assert kind=='JOURNAL_REVERSAL'and str(source)==g['journal'],(kind,source)
        r=resolve(cur,kind,source)
        expected(r,k,g['contractor'],'CANCELLED')
        again=resolve(cur,'CP7_KASBON',k['id']);expected(again,k,g['contractor'],'CANCELLED')
        old=original(cur,lambda:resolve(cur,kind,source))
        assert old['status']=='UNSUPPORTED_SOURCE',old
        return dict(status='PASS',inverse_journal=str(inverse),opens=r['document']['number'],status_shown='CANCELLED')

    def rights():
        g=given(cur,today,'300.00');k=g['kasbon']
        unknown=auth.refused(cur,lambda:resolve(cur,'CP7_KASBON',uuid.uuid4()),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
        # The kasbon panel is OWNER/ADMIN only, so the reader must not route anyone else there.
        subject=c17.master.role_actor(cur,'KEUANGAN')
        role=one(cur,"select id from erp.app_roles where role_code='KEUANGAN'")
        perms={x for x,in cur.execute('select permission_key from erp.app_role_permissions where role_id=%s',(role,)).fetchall()}
        denied=auth.refused(cur,lambda:resolve(cur,'CP7_KASBON',k['id'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
        return dict(status='PASS',unknown_kasbon=unknown,non_owner_admin=denied,role_has_payroll_view='finance.payroll.view'in perms)

    def unchanged():
        # Every other journal family the database holds resolves exactly as the original OW06 reader resolved it.
        b.api.admin(cur)
        rows=cur.execute("""select distinct on(source_type)source_type,source_id from erp.journal_entries
            where source_id is not null and source_type<>'CP7_KASBON'order by source_type,created_at desc,id""").fetchall()
        checked={}
        for kind,source in rows:
            def read(kind=kind,source=source):
                point='ow08b_read_'+uuid.uuid4().hex;cur.execute('savepoint '+point)
                try:
                    r=resolve(cur,kind,source);cur.execute('release savepoint '+point);return r
                except psycopg.Error as error:  # the same refusal must come from both readers
                    cur.execute('rollback to savepoint '+point);cur.execute('release savepoint '+point);b.api.admin(cur)
                    return dict(refused=str(error).splitlines()[0])
            name='ow08b_each_'+uuid.uuid4().hex;cur.execute('savepoint '+name)
            try:now=read()
            finally:cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)
            before=original(cur,read)
            assert('refused'in now)==('refused'in before)and(now==before if'refused'in now else same(now,before)),(kind,now,before)
            checked[kind]=now.get('status',now.get('refused'))
        assert len(checked)>=10,checked
        return dict(status='PASS',families_compared=len(checked),results=checked)

    operations=(give,cancel,rights,unchanged)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
