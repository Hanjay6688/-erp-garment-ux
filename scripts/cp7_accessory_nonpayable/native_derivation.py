"""Counted Native derivations; no connection, installation, or ERP imports."""
from hashlib import sha256
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
SNAPSHOT = 'erp.ensure_fg_accessory_cost_snapshot(uuid)'
ACCRUAL = 'erp.post_accessory_reimbursement_accrual(uuid)'
RECOST = 'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'
REWORK = 'erp.reverse_rework_completion(uuid,text)'
NOTE = 'erp.save_accessory_issue_action_v1(text,jsonb,uuid)'


def originals():
    value = json.loads((HERE/'NATIVE_ORIGIN.json').read_bytes())
    return {name:(HERE/row['file']).read_text() for name,row in value['functions'].items()}


def derive(actual):
    origin = json.loads((HERE/'NATIVE_ORIGIN.json').read_bytes())
    if set(actual) != set(origin['functions']):
        raise ValueError('NONPAYABLE_EXACT_NATIVE_SOURCE_SET_REQUIRED')
    for name,row in origin['functions'].items():
        raw = actual[name].encode()
        if len(raw)!=row['bytes'] or sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('NONPAYABLE_NATIVE_PREDECESSOR_CHANGED:'+name)
    changes = {}
    changes[SNAPSHOT] = [
        ('  v_snapshot uuid;', '  v_snapshot uuid;\n  v_nonpayable_basis jsonb;\n  v_original_reimburse numeric(18,6);'),
        ('      v_reimburse_base:=r.reimbursement_unit_rate_base_snapshot;',
         '      v_reimburse_base:=r.reimbursement_unit_rate_base_snapshot;\n'
         '      v_original_reimburse:=v_reimburse_base;v_nonpayable_basis:=null;\n'
         '      if v_recipient is not null then\n'
         '        v_nonpayable_basis:=cp7_accessory_nonpayable.good_basis_v1(v_recipient,r.category_id,l.produced_at);\n'
         "        if (v_nonpayable_basis->>'nonpayable')::boolean then v_reimburse_base:=0;end if;\n"
         '      end if;'),
        ('\n      ) returning id into v_snapshot;',
         '\n      ) returning id into v_snapshot;\n'
         '      if v_nonpayable_basis is not null then\n'
         '        perform cp7_accessory_nonpayable.capture_basis_v1(v_snapshot,v_recipient,v_original_reimburse,v_nonpayable_basis);\n'
         '      end if;'),
        ('    v_reimburse_base:=r.reimbursement_rate/v_reimburse_factor;',
         '    v_reimburse_base:=r.reimbursement_rate/v_reimburse_factor;\n'
         '    v_original_reimburse:=v_reimburse_base;v_nonpayable_basis:=null;\n'
         '    if p.contractor_id is not null then\n'
         '      v_nonpayable_basis:=cp7_accessory_nonpayable.good_basis_v1(p.contractor_id,r.category_id,l.produced_at);\n'
         "      if (v_nonpayable_basis->>'nonpayable')::boolean then v_reimburse_base:=0;end if;\n"
         '    end if;'),
        ('\n    ) returning id into v_snapshot;',
         '\n    ) returning id into v_snapshot;\n'
         '    if v_nonpayable_basis is not null then\n'
         '      perform cp7_accessory_nonpayable.capture_basis_v1(v_snapshot,p.contractor_id,v_original_reimburse,v_nonpayable_basis);\n'
         '    end if;'),
    ]
    changes[ACCRUAL] = [
        ("  select count(distinct e.contractor_id),",
         '  if cp7_accessory_nonpayable.already_recosted_v1(l.id,v_hpp,v_reimburse) then return;end if;\n'
         '  select count(distinct e.contractor_id),'),
        ('  if v_hpp>0 then',
         '  if v_hpp>0 and v_reimburse=0 then\n'
         '    v_contractor:=cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(l.id);\n'
         '  end if;\n'
         '  if v_hpp>0 then'),
        ('  if v_reimburse=0 and v_hpp>0 then',
         '  if v_reimburse=0 and v_hpp>0 and v_contractor is null then'),
        ('  v_variance:=v_reimburse-v_hpp;',
         '  v_variance:=v_reimburse-v_hpp;\n'
         '  if v_reimburse=0 and v_contractor is not null then v_variance:=-round(v_hpp,2);end if;'),
    ]
    changes[RECOST] = [
        ('      v_d:=round(coalesce(v_newtot,0)-coalesce(v_old,0),2);',
         '      v_d:=coalesce(cp7_accessory_nonpayable.recost_delta_v1(v_lot),round(coalesce(v_newtot,0)-coalesce(v_old,0),2));'),
        ("      if abs(v_d)>0.005 and exists(select 1 from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL'\n"
         "                                     and source_id=v_lot and status='POSTED') then",
         "      if abs(v_d)>0.005 and (exists(select 1 from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL'\n"
         "                                     and source_id=v_lot and status='POSTED')\n"
         '          or cp7_accessory_nonpayable.zero_reimbursement_contractor_v1(v_lot) is not null) then'),
        ("v_date,'Accessory HPP recost of an accrued lot: WIP against the reimbursement variance',",
         "v_date,case when exists(select 1 from erp.journal_entries je where je.source_type='ACCESSORY_REIMBURSE_ACCRUAL' and je.source_id=v_lot and je.status='POSTED')\n"
         "          then 'Accessory HPP recost of an accrued lot: WIP against the reimbursement variance'\n"
         "          else 'Accessory HPP recost of frozen nonpayable GOOD: WIP against the reimbursement variance' end,"),
    ]
    anchor = ("    select id into v_journal from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=r.good_fg_lot_id and status='POSTED' order by posting_at desc,id desc limit 1;\n"
              '    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;')
    changes[REWORK] = [(anchor, anchor+'\n'
        '    for v_journal in select je.id from erp.journal_entries je\n'
        '      join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id\n'
        '      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id\n'
        "      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id=r.good_fg_lot_id\n"
        '        and exists(select 1 from cp7_accessory_nonpayable.good_bases_v1 np_basis where np_basis.lot_id=sn.lot_id and np_basis.nonpayable)\n'
        '      order by je.posting_at,je.id\n'
        '    loop perform erp.reverse_journal(v_journal,p_reason);end loop;')]
    changes[NOTE] = [("  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;", "  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;\n  -- A zero collectible is already settled; use the Native status projection\n  -- before committing the same note request, without a payment or new journal.\n  perform erp.refresh_contractor_issue_payroll_status(i.id)\n    from erp.contractor_material_issue_items i\n    where i.issue_id=v_id and erp.bc_note_item_collectible_v1(i.id)<=0\n      and i.payroll_status is distinct from 'SETTLED'\n    order by i.id;")]
    result, proofs = {}, {}
    for name,pairs in changes.items():
        text = actual[name]
        for before,after in pairs:
            if text.count(before)!=1:
                raise ValueError('NONPAYABLE_EXACT_NATIVE_ANCHOR_REQUIRED:'+name+':'+before[:70])
            text = text.replace(before,after,1)
        reversed_text = text
        for before,after in reversed(pairs):
            if reversed_text.count(after)!=1:
                raise ValueError('NONPAYABLE_EXACT_DERIVATION_REVERSE_REQUIRED:'+name)
            reversed_text = reversed_text.replace(after,before,1)
        if reversed_text!=actual[name]:
            raise ValueError('NONPAYABLE_ORIGINAL_NATIVE_BYTES_NOT_RECOVERED:'+name)
        result[name] = text
        proofs[name] = dict(original_sha256=origin['functions'][name]['sha256'],
            derived_sha256=sha256(text.encode()).hexdigest(),counted_changes=len(pairs),original_bytes_recovered=True)
    return result,proofs


if __name__=='__main__':
    if sys.argv[1:] not in ([],['--sql']):
        raise SystemExit('ONLY_LOCAL_SOURCE_DERIVATION_OR_SQL_OUTPUT_ALLOWED')
    result,proof = derive(originals())
    if sys.argv[1:]:
        # pg_get_functiondef returns no SQL statement separator. Keep those
        # captured bytes pinned, adding delimiters only to emitted SQL.
        print(';\n'.join(result.values())+';')
    else:
        print(json.dumps(dict(status='EXACT_COUNTED_NONPAYABLE_NATIVE_DERIVATIONS',proof=proof,
            actual_ERP_execution=0,production_go=False),sort_keys=True))

