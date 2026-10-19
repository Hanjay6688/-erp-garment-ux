"""Strict negative vectors for the repaired checker; synthetic detector control.

One immutable-wage trigger is disabled only for each declared corrupting write,
re-enabled before detection and restored by savepoint rollback. This is not an
ordinary-write, permission, or guard-prevention proof.
"""
from decimal import Decimal as D
from hashlib import sha256
import json
import reader_graph_cases as g
from detector_case import detector_rows, counts

ID='SOL_R5_REPAIR_CHECKER_FULL_167_NEGATIVE_VECTORS'
TARGET='run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor'
GUARD='trg_guard_fg_unsourced_repair_wages_v1_immutable'


def cases(cur,today):
    def strict(o):
        bd=g.bd
        o.update(oracle_origin='SOL_LITERAL_HEALTHY_ZERO_WRONG_ONE_MISSING_ONE_ALL_OTHER166_ZERO',
                 fixture_origin='ACCEPTED_AX_NATIVE_REPAIR2_AND1_RATE2000_PUBLIC_CP7_NOTA6000',
                 fixture_class='CONTROLLED_LEGACY_INCONSISTENCY_NOT_UI_AUTHORIZATION',phases=[])
        def phase(label,expected):
            rows=detector_rows(cur);values=counts(rows)
            o['phases'].append(dict(label=label,expected_nonzero=expected,rows=rows))
            assert len(values)==167 and {k:v for k,v in values.items()if v}==expected,('SOL_R5_REPAIR_FULL_VECTOR',label,{k:v for k,v in values.items()if v})
            return values
        phase('INITIAL_HEALTHY',{})
        f=g.sources.repair(cur,today,qty=2)
        g.sources.ax.post(cur,g.sources.ax.repair_payload(f,1));bd.api.admin(cur)
        posted=g.nota.act(cur,'POST',g.nota.command(cur,'SAVE',g.nota.payload(cur,f,today)));bd.api.admin(cur)
        header=cur.execute('select contractor_id::text,status,net_payable::text from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()
        assert header==(str(f['contractor']),'CALCULATED','6000.00'),header
        rows=cur.execute("select p.source_id::text,p.qty_payable::text,p.amount::text,w.contractor_id::text,p.work_component_id::text,w.work_component_id::text from erp.payroll_work_items p join erp.fg_unsourced_repair_wages_v1 w on w.id=p.source_id where p.payroll_id=%s and p.source_type='FG_REPAIR' order by p.qty_payable,p.id",(posted['payroll_id'],)).fetchall()
        assert len(rows)==2 and [D(r[1])for r in rows]==[D(1),D(2)] and sum(D(r[2])for r in rows)==6000
        assert all(r[3]==header[0] and r[4]==r[5]for r in rows)
        wages=[r[0]for r in rows]
        originals=cur.execute('select to_jsonb(w) from erp.fg_unsourced_repair_wages_v1 w where id=any(%s::uuid[]) order by id',(wages,)).fetchall()
        other=cur.execute('select id::text from erp.contractors where id<>%s order by id limit 1',(f['contractor'],)).fetchone()[0]
        guard=cur.execute("select t.tgenabled,pg_get_triggerdef(t.oid),pg_get_functiondef(t.tgfoid) from pg_trigger t where t.tgrelid='erp.fg_unsourced_repair_wages_v1'::regclass and t.tgname=%s",(GUARD,)).fetchone()
        assert guard[0]=='O'
        facts=g.protected.fingerprints(cur)
        phase('VALID_NOTA_6000',{})
        for label,statement,args in [('WRONG_CONTRACTOR',"update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s",(other,wages[0])),
                                     ('MISSING_WAGE',"delete from erp.fg_unsourced_repair_wages_v1 where id=%s",(wages[1],))]:
            cur.execute('savepoint sol_r5_repair_negative')
            try:
                bd.api.admin(cur);cur.execute('alter table erp.fg_unsourced_repair_wages_v1 disable trigger '+GUARD)
                cur.execute(statement,args)
                cur.execute('alter table erp.fg_unsourced_repair_wages_v1 enable trigger '+GUARD)
                assert cur.execute("select tgenabled from pg_trigger where tgrelid='erp.fg_unsourced_repair_wages_v1'::regclass and tgname=%s",(GUARD,)).fetchone()[0]=='O'
                phase(label,{TARGET:1})
                assert g.protected.fingerprints(cur)==facts
            finally:
                cur.execute('rollback to savepoint sol_r5_repair_negative');cur.execute('release savepoint sol_r5_repair_negative');bd.api.admin(cur)
            phase('ROLLBACK_'+label,{})
            assert cur.execute('select to_jsonb(w) from erp.fg_unsourced_repair_wages_v1 w where id=any(%s::uuid[]) order by id',(wages,)).fetchall()==originals
            assert cur.execute("select t.tgenabled,pg_get_triggerdef(t.oid),pg_get_functiondef(t.tgfoid) from pg_trigger t where t.tgrelid='erp.fg_unsourced_repair_wages_v1'::regclass and t.tgname=%s",(GUARD,)).fetchone()==guard
            assert g.protected.fingerprints(cur)==facts
        o.update(payroll_id=posted['payroll_id'],header=header,resolved_rows=rows,original_wage_rows=originals,
                 immutable_wage_guard=dict(name=GUARD,enabled_before_detection=True,definition_sha256=sha256(guard[2].encode()).hexdigest(),all_trigger_properties_restored=True),
                 all167_vectors_exported=True,exact_nonzero_sequences=[{}, {TARGET:1},{}, {TARGET:1},{}],
                 financial_stock_HPP_facts_unchanged=True,no_permission_or_guard_prevention_claim=True)
    return [g.record(ID,strict)]
