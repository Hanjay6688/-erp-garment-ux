-- Owner D15-4 ("Tombol buka ulang PO dibuat, dengan penghalang seperti fitur koreksi lain"; Fable FABLE-014): a FINISHED
-- Production Order is reopened from the connected HPP screen through the accepted Native writer only,
-- erp.reopen_production_order(po,reason), which reverses the PO's posted residual-WIP close journals (Native
-- erp.reverse_journal) and puts the PO back on the stage its own rows show, with a Native audit row. HPP rows and the HPP
-- already moved to finished goods stay; finishing again (finish.sql) rebuilds the same HPP when nothing new was posted.
-- Blockers, shown before the click and enforced again under the PO lock:
--  * NOT_FINISHED: only a FINISHED PO can be reopened (the Native rule).
--  * FG_USED: pieces of the PO's production lots already left them (sold, reserved by a sales draft, adjusted or moved);
--    like the other corrections, a document whose output is already used downstream is not reopened.
--  * PERIOD_CLOSED: today (WIB) is inside the closed period, or a close journal to reverse has its economic or book date
--    there; the reversal would reach into closed books (owner D15-1: closed periods are never reopened automatically).
-- One transaction, a reviewed token, a reason, idempotent per (actor, request) and immutable history, like finish.sql.
-- Post-conditions: the PO is no longer FINISHED, none of its residual-close journals is still POSTED, and its WIP balance
-- rose by exactly the residual that the reversed journals had closed.
create table cp7_cutting_correction.po_reopen_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.po_reopen_history(
 actor uuid not null,request_id uuid not null,po_id uuid not null references erp.production_orders,
 source jsonb not null,result jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.po_reopen_requests owner to postgres;
alter table cp7_cutting_correction.po_reopen_history owner to postgres;
alter table cp7_cutting_correction.po_reopen_requests enable row level security;
alter table cp7_cutting_correction.po_reopen_history enable row level security;
create policy private_po_reopen_requests on cp7_cutting_correction.po_reopen_requests for all using(false)with check(false);
create policy private_po_reopen_history on cp7_cutting_correction.po_reopen_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.po_reopen_requests,cp7_cutting_correction.po_reopen_history
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_po_reopen_history before update or delete on cp7_cutting_correction.po_reopen_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_po_reopen_history_truncate before truncate on cp7_cutting_correction.po_reopen_history
 for each statement execute function cp7_cutting_correction.immutable();

-- Everything the reopen reads, for the review token; the blockers are computed from the same rows.
create function cp7_cutting_correction.reopen_po_snapshot(p_po uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare po erp.production_orders;c erp.contractors;fg bigint;lots bigint;used bigint;wip numeric;closes jsonb;v_returning numeric;
 earliest date;closed date;today date;h jsonb;b jsonb:='[]';
begin
 select *into po from erp.production_orders where id=p_po;
 if po.id is null then return null;end if;
 select *into c from erp.contractors where id=po.contractor_id;
 select coalesce(sum(initial_qty_pcs),0),count(*)into fg,lots from erp.fg_lots where po_id=po.id and lot_origin='PRODUCTION';
 select coalesce(sum(-m.qty_signed),0)into used from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id
  where l.po_id=po.id and l.lot_origin='PRODUCTION'and m.qty_signed<0;
 select coalesce(sum(jl.debit-jl.credit),0)into wip from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
  where je.status in('POSTED','REVERSED')and jl.po_id=po.id and jl.account_id=erp.account_id('WIP');
 -- The journals Native reopen reverses: the PO's POSTED PO_WIP_RESIDUAL_CLOSE entries of its close events.
 select coalesce(jsonb_agg(jsonb_build_object('journal_id',je.id,'economic_date',je.economic_date,'book_date',je.transaction_date,
   'residual',e.residual_amount)order by je.posting_at,je.id),'[]'),coalesce(sum(e.residual_amount),0),
   min(least(je.economic_date,coalesce(je.transaction_date,je.economic_date)))
  into closes,v_returning,earliest
  from erp.po_wip_close_events e join erp.journal_entries je on je.id=e.journal_entry_id
  where e.po_id=po.id and je.source_type='PO_WIP_RESIDUAL_CLOSE'and je.status='POSTED';
 select p.closed_through into closed from erp.accounting_period_control p where p.singleton_id=1;
 today:=(statement_timestamp()at time zone 'Asia/Jakarta')::date;
 select to_jsonb(x)into h from erp.get_hpp_completeness(po.id)x;
 if po.status is distinct from'FINISHED'then b:=b||jsonb_build_object('kind','NOT_FINISHED','qty',null);end if;
 if used>0 then b:=b||jsonb_build_object('kind','FG_USED','qty',used);end if;
 if closed is not null and(today<=closed or earliest<=closed)then b:=b||jsonb_build_object('kind','PERIOD_CLOSED','qty',null);end if;
 return jsonb_build_object('po',jsonb_build_object('id',po.id,'number',po.po_number,'status',po.status,'stage',po.current_stage,
   'contractor_id',po.contractor_id,'contractor_name',c.contractor_name,'updated_at',po.updated_at),
  'fg_pcs',fg,'fg_lots',lots,'fg_used_pcs',used,'wip_balance',round(wip,2),'close_journals',closes,'returning',round(v_returning,2),
  'closed_through',closed,'today',today,'hpp',h,'blockers',b);
end $$;

create function cp7_cutting_correction.reopen_po_workspace(p_po uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;
begin
 a:=cp7_cutting_correction.finish_access_now();s:=cp7_cutting_correction.reopen_po_snapshot(p_po);
 if s is null or s->'hpp'is null or s->'hpp'='null'::jsonb then raise exception 'CP7_PO_REOPEN_NOT_FOUND';end if;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_REOPEN_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.po-reopen-workspace.v1','po_id',p_po,'po_number',s->'po'->>'number',
  'po_status',s->'po'->>'status','stage',s->'po'->>'stage','contractor_name',s->'po'->>'contractor_name',
  'fg_pcs',(s->>'fg_pcs')::bigint,'fg_lots',(s->>'fg_lots')::bigint,'fg_used_pcs',(s->>'fg_used_pcs')::bigint,
  'wip_balance',to_char((s->>'wip_balance')::numeric,'FM999999999999999990.00'),
  'returning_to_wip',to_char((s->>'returning')::numeric,'FM999999999999999990.00'),
  'close_journals',jsonb_array_length(s->'close_journals'),'closed_through',s->>'closed_through',
  'hpp',cp7_cutting_correction.finish_hpp(s->'hpp'),'reopen_date',s->>'today',
  'review_token',md5(s::text),'eligible',jsonb_array_length(s->'blockers')=0,'blockers',s->'blockers','business_DML',false);
end $$;

create function cp7_cutting_correction.reopen_po_command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.po_reopen_requests;po erp.production_orders;s jsonb;s2 jsonb;r jsonb;answer jsonb;
 v_reason text;v_actor uuid;v_group uuid;rose numeric;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_correction.finish_access_now();
 if p_request is null or jsonb_typeof(p)is distinct from'object'
  or not(p?&array['action','po_id','review_token','change_reason'])or(select count(*)from jsonb_object_keys(p))<>4
  or p->'action'is distinct from'"REOPEN"'::jsonb
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~uuid_re
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_PO_REOPEN_FIELDS';end if;
 v_reason:=btrim(p->>'change_reason');
 insert into cp7_cutting_correction.po_reopen_requests values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.po_reopen_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p then raise exception 'CP7_PO_REOPEN_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_REOPEN_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 -- Same lock order as finish.sql and the cutting writers: each Potongan's flow lock by id, then the PO row.
 for v_group in select id from erp.cutting_groups where po_id=(p->>'po_id')::uuid order by id loop
  perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
 end loop;
 select *into po from erp.production_orders where id=(p->>'po_id')::uuid for update;
 if po.id is null then raise exception 'CP7_PO_REOPEN_NOT_FOUND';end if;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_REOPEN_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.reopen_po_snapshot(po.id);
 if md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_PO_REOPEN_STALE_REVIEW';end if;
 if jsonb_array_length(s->'blockers')<>0 then raise exception 'CP7_PO_REOPEN_BLOCKED: %',s->'blockers';end if;
 v_actor:=erp.current_app_user_id();
 if v_actor is null then raise exception using errcode='42501',message='CP7_PO_REOPEN_DENIED';end if;
 perform set_config('app.change_reason',v_reason,true);
 perform erp.reopen_production_order(po.id,v_reason);
 s2:=cp7_cutting_correction.reopen_po_snapshot(po.id);
 rose:=(s2->>'wip_balance')::numeric-(s->>'wip_balance')::numeric;
 if s2->'po'->>'status'='FINISHED'or jsonb_array_length(s2->'close_journals')<>0 or abs(rose-(s->>'returning')::numeric)>0.005 then
  raise exception 'CP7_PO_REOPEN_INCOMPLETE';end if;
 r:=jsonb_build_object('status',s2->'po'->>'status','stage',s2->'po'->>'stage','reversed_journals',jsonb_array_length(s->'close_journals'),
  'returned_to_wip',to_char(round(rose,2),'FM999999999999999990.00'),'wip_after',to_char((s2->>'wip_balance')::numeric,'FM999999999999999990.00'),
  'hpp',cp7_cutting_correction.finish_hpp(s2->'hpp'),'reopened_on',s->>'today');
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_REOPEN_ACCESS_CHANGED';end if;
 insert into cp7_cutting_correction.po_reopen_history values(auth.uid(),p_request,po.id,s,r,v_reason,clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.po-reopen-outcome.v1','kind','COMMITTED_OUTCOME','action','REOPEN',
  'request_id',p_request,'po_id',po.id,'po_number',po.po_number,'result',r);
 update cp7_cutting_correction.po_reopen_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_po_reopen_v1(p_po uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.reopen_po_workspace(p_po)$$;
create function public.erp_cp7_reopen_po_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.reopen_po_command(p_payload,p_request)$$;
alter function cp7_cutting_correction.reopen_po_snapshot(uuid)owner to postgres;
alter function cp7_cutting_correction.reopen_po_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.reopen_po_command(jsonb,uuid)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_po_reopen_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_reopen_po_v1(jsonb,uuid)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.reopen_po_snapshot(uuid),cp7_cutting_correction.reopen_po_workspace(uuid),
 cp7_cutting_correction.reopen_po_command(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.reopen_po_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.reopen_po_command(jsonb,uuid)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_po_reopen_v1(uuid),public.erp_cp7_reopen_po_v1(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_po_reopen_v1(uuid),public.erp_cp7_reopen_po_v1(jsonb,uuid)to authenticated;
