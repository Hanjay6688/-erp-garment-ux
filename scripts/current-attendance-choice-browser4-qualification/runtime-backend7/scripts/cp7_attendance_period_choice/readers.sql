-- Additive S03 reader compatibility. No money, authority, roles or business DML.
-- Existing postgres SECURITY DEFINER HPP readers supply the same checked
-- Owner/Admin+HPP-view authority. These helpers are PRIVATE SECURITY INVOKER;
-- app roles receive neither schema usage nor execution rights.

create function cp7_attendance_choice.period_hold_json_v1(p_start date,p_end date)returns jsonb
language sql stable security invoker set search_path=''as $$
 select jsonb_build_object('domain','ATTENDANCE_PERIOD_CHOICE','decision_id',d.id,
  'source_period_start',d.period_start,'source_period_end',d.period_end)
 from cp7_attendance_choice.decisions_v1 d
 where d.id=cp7_attendance_choice.current_v1(p_start,p_end)
$$;

create function cp7_attendance_choice.decorate_pool_json_v1(p_pool erp.attendance_hpp_pools,p_closed date,p_native jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set timezone='UTC'as $$
declare snap record;owned jsonb;hold jsonb;source_start date;source_end date;output_start date;output_end date;
begin
 -- One SQL snapshot binds the CURRENT Native composite, immutable ownership,
 -- original decision and its exact allocation inverse. Do not decide ownership
 -- from ACTIVE/current-choice filters: a cancelled/reversed choice is history,
 -- while its carried pool remains permanently owned by that workflow.
 select to_jsonb(p)native,to_jsonb(a)allocation,to_jsonb(d)decision,to_jsonb(r)inverse,
  cp7_attendance_choice.period_hold_json_v1(p.period_start,p.period_end)period_hold
 into snap
 from erp.attendance_hpp_pools p
 left join cp7_attendance_choice.allocations_v1 a on a.pool_id=p.id
 left join cp7_attendance_choice.decisions_v1 d on d.id=a.decision_id
 left join cp7_attendance_choice.allocation_reversals_v1 r on r.allocation_id=a.id
 where p.id=p_pool.id;
 if not found or snap.native is distinct from to_jsonb(p_pool)
  or p_native->>'id'is distinct from p_pool.id::text
  or p_native->>'status'is distinct from p_pool.status
  or p_native->>'period_start'is distinct from erp._cp3_canonical_date(p_pool.period_start)
  or p_native->>'period_end'is distinct from erp._cp3_canonical_date(p_pool.period_end)then
  raise exception 'CP7_S03_HPP_READ_CHANGED: data pool berubah saat dibaca. Muat ulang daftar pool dan pilihan biaya absensi.';
 end if;
 if snap.allocation is not null then
  source_start:=(snap.decision->>'period_start')::date;source_end:=(snap.decision->>'period_end')::date;
  output_start:=(snap.allocation->>'output_start')::date;output_end:=(snap.allocation->>'output_end')::date;
  if snap.decision is null or snap.decision->>'choice'is distinct from'CARRY'
   or source_start is distinct from p_pool.period_start or source_end is distinct from p_pool.period_end
   or output_start is null or output_end is null or output_start<=source_end or output_end<output_start
   or output_end-output_start>366 or p_pool.status not in('ACTIVE','CANCELLED')
   or(p_pool.status='ACTIVE'and(snap.inverse is not null or p_pool.cancellation_journal_entry_id is not null))
   or(p_pool.status='CANCELLED'and(snap.inverse is null
      or(snap.inverse->>'journal_id')::uuid is distinct from p_pool.cancellation_journal_entry_id))then
   raise exception 'CP7_S03_HPP_READ_CHANGED: hubungan pool dan pilihan biaya absensi berubah. Muat ulang sebelum melanjutkan.';
  end if;
  owned:=jsonb_build_object('domain','ATTENDANCE_PERIOD_CHOICE',
   'decision_id',(snap.decision->>'id')::uuid,'allocation_id',(snap.allocation->>'id')::uuid,
   'source_period_start',source_start,'source_period_end',source_end,
   'output_period_start',output_start,'output_period_end',output_end,
   'output_period_closed',p_closed is not null and output_end<=p_closed);
  -- Preserve Native header P1, original period_closed P1 and all money/history.
  -- Legacy CANCEL/REPLACE never owns this pool, even after its decision reverses.
  return p_native||jsonb_build_object('attendance_choice',owned,'actions','[]'::jsonb);
 end if;
 hold:=snap.period_hold;
 if hold is not null then
  -- A normal DRAFT/ACTIVE pool and a current S03 source-period choice cannot
  -- lawfully coexist. A historical ordinary pool is held, not S03-owned.
  if p_pool.status not in('CANCELLED','VOIDED')then
   raise exception 'CP7_S03_HPP_READ_CHANGED: keadaan periode dan pool berubah. Muat ulang daftar pool.';
  end if;
  return p_native||jsonb_build_object('period_hold',hold,'actions','[]'::jsonb);
 end if;
 -- Unaffected ordinary rows are returned exactly as the original reader made.
 return p_native;
end $$;

create function cp7_attendance_choice.decorate_pool_preview_v1(p_start date,p_end date,p_native jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare hold jsonb;
begin
 hold:=cp7_attendance_choice.period_hold_json_v1(p_start,p_end);
 if hold is null then return p_native;end if;
 if p_native->>'period_start'is distinct from erp._cp3_canonical_date(p_start)
  or p_native->>'period_end'is distinct from erp._cp3_canonical_date(p_end)then
  raise exception 'CP7_S03_HPP_READ_CHANGED: periode pratinjau berubah saat dibaca. Muat ulang pilihan periode.';
 end if;
 -- Keep the existing closed BLOCKED contract. No fake Native pool, invented
 -- zero, READY-with-can_create=false exception or reusable review token.
 return p_native||jsonb_build_object('period_hold',hold,'status','BLOCKED','can_create',false,
  'numerator_amount',null,'denominator_qty',null,'unit_cost_per_sewn_pcs',null,
  'source_count',null,'destination_count',null,'po_count',null,'pos','[]'::jsonb,
  'manifest_sha256',null,'review_token',null,
  'blocker',jsonb_build_object('code','CP7_S03_PERIOD_HELD',
   'message','Periode sumber ini masih memiliki pilihan biaya absensi Owner. Periksa atau betulkan pilihan itu melalui Pilihan biaya absensi sebelum membuat pool biasa.'));
end $$;
