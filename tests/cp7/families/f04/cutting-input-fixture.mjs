import {readFileSync}from'node:fs'
import {openRuntime,jsonArg}from'./runtime.mjs'
// Explicitly synthetic source/Auth fixture, with zero real Native proof credit.
export const actor='00000000-0000-4000-8000-000000000001',group='00000000-0000-4000-8000-000000000002',pattern='00000000-0000-4000-8000-000000000003',roll='00000000-0000-4000-8000-000000000004',size='00000000-0000-4000-8000-000000000005'
export async function syntheticCuttingInputs(){
 const db=await openRuntime()
 try{await db.execute(`create schema erp;create schema cp7_private;create schema cp7_planning;create schema cp7_cutting_yield;
    create function cp7_private.immutable_run()returns trigger language plpgsql as $$begin raise exception 'CONTROL_IMMUTABLE';end$$;
    create function cp7_planning.utc(t timestamptz)returns text language sql immutable as $$select to_char(t at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;
    create table public.control_cutting_access(actor uuid not null,allowed boolean not null,write_allowed boolean not null);
    insert into public.control_cutting_access values('${actor}',true,true);
    grant select on public.control_cutting_access to cp7_capture;
    grant usage on schema erp,cp7_private,cp7_planning,cp7_cutting_yield to cp7_capture;
    create function cp7_cutting_yield.access_now()returns jsonb language plpgsql as $$
      declare r public.control_cutting_access%rowtype;
      begin select *into r from public.control_cutting_access;if not r.allowed then raise exception 'CONTROL_CURRENT_ACCESS_DENIED';end if;
       return jsonb_build_object('actor',r.actor,'allowed',r.allowed);end$$;
    create function erp.has_permission(p text)returns boolean language sql as $$select write_allowed and p='production.cutting.edit_draft' from public.control_cutting_access$$;
    create table erp.cutting_groups(id uuid,po_id uuid,row_version bigint,cut_at timestamptz,material_issue_posted boolean,pattern_id uuid,pattern_revision_snapshot text);
    create table erp.sizes(id uuid,size_code text);
    insert into erp.sizes values('${size}','SIZE-REAL');
    create table erp.cutting_group_size_slots(cutting_group_id uuid,size_id uuid);
    insert into erp.cutting_group_size_slots values('${group}','${size}');
    grant select on erp.cutting_group_size_slots to cp7_capture;
    insert into erp.cutting_groups values('${group}','${group}',1,clock_timestamp()-interval '1 year',false,'${pattern}','r1');
    grant select on erp.cutting_groups to cp7_capture;
    create table public.control_cutting_slices(group_id uuid,slices jsonb);
    insert into public.control_cutting_slices values('${group}',${jsonArg([{ slice_id: roll, group_id: group, roll_id: roll, material_id: roll, material_sku: 'MATERIAL-REAL', unit_code: 'YARD', outputs: [{ yield_id: size, size_id: size, qty_pcs: '60' }], consumed_native: '60' }])});
    grant select on public.control_cutting_slices to cp7_capture;
    create function cp7_cutting_yield.source(q jsonb)returns jsonb language sql stable as $$
      select jsonb_build_object('requested_group_count',1,'found_group_count',1,'slices',
        (select coalesce(jsonb_agg(x||jsonb_build_object('cut_at',cp7_planning.utc(g.cut_at),'material_issue_posted',g.material_issue_posted,'revision',g.row_version::text)),'[]')from jsonb_array_elements(c.slices)x))
      from public.control_cutting_slices c join erp.cutting_groups g on g.id=c.group_id where c.group_id=(q->'group_ids'->>0)::uuid$$;
    ${readFileSync('scripts/cp7-src/cutting-yield/learning-kernel.sql', 'utf8')}
    ${readFileSync('scripts/cp7-src/cutting-yield/inputs.sql', 'utf8')}`);return db}catch(e){await db.close();throw e}
}
