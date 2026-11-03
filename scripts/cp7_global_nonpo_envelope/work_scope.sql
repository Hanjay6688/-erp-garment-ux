-- Closed preparation. No installer, seed, owning-function adaptation or public
-- access is supplied here. The final-parent admission gate remains closed.
create table cp7_global_nonpo_envelope.work_scopes_v1(
 backend_pid integer not null,transaction_id bigint not null,
 actor uuid not null,request_id uuid not null,operation_id uuid not null,
 operation text not null check(operation in('D1','E','SOURCE')),
 profile_id text not null references cp7_global_nonpo_envelope.profiles(id),
 native_binding jsonb not null,root_sales uuid[] not null,
 basis_sha256 text not null check(basis_sha256~'^[0-9a-f]{64}$'),
 authority jsonb not null,lock_proof jsonb not null,outside_before jsonb not null,
 primary key(backend_pid,transaction_id),unique(operation_id)
);
create table cp7_global_nonpo_envelope.scope_completions_v1(
 operation_id uuid primary key,operation text not null,
 actor uuid not null,request_id uuid not null,profile_id text not null,
 native_binding jsonb not null,basis_sha256 text not null,
 outside_before jsonb not null,outside_after jsonb not null,
 proof jsonb not null,recorded_at timestamptz not null default statement_timestamp(),
 check(outside_before=outside_after)
);
alter table cp7_global_nonpo_envelope.work_scopes_v1 owner to postgres;
alter table cp7_global_nonpo_envelope.scope_completions_v1 owner to postgres;
alter table cp7_global_nonpo_envelope.work_scopes_v1 enable row level security;
alter table cp7_global_nonpo_envelope.scope_completions_v1 enable row level security;
revoke all on cp7_global_nonpo_envelope.work_scopes_v1,
 cp7_global_nonpo_envelope.scope_completions_v1 from public,anon,authenticated,service_role;

-- Read the actual existing owning work row. No caller-supplied actor, request,
-- payload or operation root can substitute for that row.
create function cp7_global_nonpo_envelope.native_work_v1(p_operation text,p_id uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare native_ jsonb;authority_ jsonb;root_ text;stored_authority_ jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'or auth.uid()is null
  or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_GLOBAL_CURRENT_ACTOR_REQUIRED';end if;
 if p_operation='D1'then
  select to_jsonb(n)into native_ from cp7_credit_correction_de.work_v1 n
   where n.backend_pid=pg_backend_pid()and n.transaction_id=txid_current_if_assigned()and n.actor=auth.uid();
  authority_:=cp7_sales_return_correction.access_now();root_:=native_->>'sale_id';
 elsif p_operation='E'then
  select to_jsonb(n)into native_ from cp7_credit_note_carry_de.work_v1 n
   where n.backend_pid=pg_backend_pid()and n.transaction_id=txid_current_if_assigned()and n.actor=auth.uid();
  authority_:=cp7_note.access_now();root_:=native_->>'source_sale_id';
 elsif p_operation='SOURCE'then
  select to_jsonb(n)into native_ from cp7_credit.source_operation_work_v1 n
   where n.backend_pid=pg_backend_pid()and n.transaction_id=txid_current_if_assigned()and n.actor=auth.uid();
  authority_:=cp7_sales.command_access(native_->>'action');root_:=native_->>'sale_id';
 else raise exception 'CP7_GLOBAL_OPERATION_REQUIRED';end if;
 if native_ is null or p_id is null or native_->>'operation_id'is distinct from p_id::text
  or native_->>'actor'is distinct from auth.uid()::text
  or coalesce(native_->>'request_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(root_,'')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(native_->'payload')is distinct from'object'then
  raise exception 'CP7_GLOBAL_EXACT_NATIVE_WORK_REQUIRED';end if;
 stored_authority_:=case when p_operation='SOURCE'then native_->'authority_snapshot'else native_->'authority'end;
 if stored_authority_ is distinct from authority_ then
  raise exception using errcode='42501',message='CP7_GLOBAL_NATIVE_AUTHORITY_CHANGED';end if;
 return jsonb_build_object('binding',jsonb_build_object('operation',p_operation,'operation_id',p_id,
   'actor',auth.uid(),'request_id',native_->'request_id','root_sale_id',root_,
   'payload',native_->'payload','expected_version',native_->'expected_version'),
  'authority',authority_,'phase',native_->'phase','root_sale_id',root_);
end $$;

-- Call only at the end of the original prepare, after its real work row exists
-- and before the first Native stock/money effect. The owning adapter must add
-- the same global basis to the original quote/review token. SOURCE has no new
-- UI review claim: it takes an explicitly fresh basis at its owned prepare.
create function cp7_global_nonpo_envelope.bind_v1(p_operation text,p_id uuid,
 p_profile text,p_reviewed_basis text)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare owner_ jsonb;fresh_ jsonb;locked_ jsonb;inspected_ jsonb;roots_ uuid[];
begin
 owner_:=cp7_global_nonpo_envelope.native_work_v1(p_operation,p_id);
 if owner_->>'phase'is distinct from'PREPARED'then raise exception 'CP7_GLOBAL_PREPARED_NATIVE_WORK_REQUIRED';end if;
 if exists(select 1 from cp7_global_nonpo_envelope.work_scopes_v1
   where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_GLOBAL_NESTED_SCOPE_REFUSED';end if;
 locked_:=cp7_global_nonpo_envelope.lock_v1(p_profile);
 fresh_:=cp7_global_nonpo_envelope.native_work_v1(p_operation,p_id);
 if fresh_ is distinct from owner_ then raise exception 'CP7_GLOBAL_NATIVE_WORK_CHANGED_DURING_LOCKS';end if;
 roots_:=array[(owner_->>'root_sale_id')::uuid];
 inspected_:=cp7_global_nonpo_native_graph.inspect_v1(roots_);
 if inspected_->>'contract'is distinct from'cp7.global-nonpo-native-graph.readonly-inspector.v1'
  or inspected_->>'status'is distinct from'OBSERVED_QUIESCENT_SOURCE_ONLY'
  or inspected_->'issues'is distinct from'[]'::jsonb
  or coalesce(inspected_->>'basis_sha256','')!~'^[0-9a-f]{64}$'
  or jsonb_typeof(inspected_->'outside_source')is distinct from'object'
  or inspected_#>'{outside_source,facts,BE_context_rows}'is distinct from'[]'::jsonb then
  raise exception 'CP7_GLOBAL_CURRENT_NOOP_PROOF_REQUIRED';end if;
 if p_operation in('D1','E')and(p_reviewed_basis is null
   or p_reviewed_basis is distinct from inspected_->>'basis_sha256')then
  raise exception 'CP7_GLOBAL_REVIEWED_BASIS_CHANGED';end if;
 if p_operation='SOURCE'and p_reviewed_basis is not null then
  raise exception 'CP7_GLOBAL_SOURCE_HAS_NO_NEW_UI_REVIEW_TOKEN';end if;
 insert into cp7_global_nonpo_envelope.work_scopes_v1(backend_pid,transaction_id,
  actor,request_id,operation_id,operation,profile_id,native_binding,root_sales,
  basis_sha256,authority,lock_proof,outside_before)
 values(pg_backend_pid(),txid_current(),auth.uid(),(owner_#>>'{binding,request_id}')::uuid,
  p_id,p_operation,p_profile,owner_->'binding',roots_,inspected_->>'basis_sha256',
  owner_->'authority',locked_,inspected_->'outside_source');
end $$;

-- Call before the original owning finish writes its immutable operation receipt
-- and removes its work row. Existing Native finish/receipt checks remain intact.
create function cp7_global_nonpo_envelope.finish_v1(p_operation text,p_id uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare work_ cp7_global_nonpo_envelope.work_scopes_v1;owner_ jsonb;after_ jsonb;
begin
 select *into work_ from cp7_global_nonpo_envelope.work_scopes_v1
  where backend_pid=pg_backend_pid()and transaction_id=txid_current_if_assigned()and actor=auth.uid();
 if work_.operation_id is null or work_.operation_id is distinct from p_id
  or work_.operation is distinct from p_operation then raise exception 'CP7_GLOBAL_OWN_SCOPE_REQUIRED';end if;
 owner_:=cp7_global_nonpo_envelope.native_work_v1(p_operation,p_id);
 if owner_->'binding'is distinct from work_.native_binding
  or owner_->'authority'is distinct from work_.authority
  or owner_->>'phase'is distinct from(case when p_operation='SOURCE'then'NATIVE_COMPLETE'else'MATERIALIZED'end)then
  raise exception 'CP7_GLOBAL_SAME_NATIVE_COMPLETION_REQUIRED';end if;
 after_:=cp7_global_nonpo_native_graph.inspect_v1(work_.root_sales);
 if after_->>'contract'is distinct from'cp7.global-nonpo-native-graph.readonly-inspector.v1'
  or after_->>'status'is distinct from'OBSERVED_QUIESCENT_SOURCE_ONLY'
  or after_->'issues'is distinct from'[]'::jsonb
  or after_->'outside_source'is distinct from work_.outside_before then
  raise exception 'CP7_GLOBAL_OUTSIDE_CHANGED_OR_NOT_QUIESCENT';end if;
 insert into cp7_global_nonpo_envelope.scope_completions_v1(operation_id,operation,
  actor,request_id,profile_id,native_binding,basis_sha256,outside_before,outside_after,proof)
 values(p_id,p_operation,work_.actor,work_.request_id,work_.profile_id,work_.native_binding,
  work_.basis_sha256,work_.outside_before,after_->'outside_source',jsonb_build_object(
   'contract','cp7.global-nonpo-envelope-completion.v1','backend_pid',work_.backend_pid,
   'transaction_id',work_.transaction_id::text,'lock',work_.lock_proof,
   'same_actual_Native_owner_and_request',true,'outside_full_identity_and_facts_equal',true,
   'Native_owning_receipt_and_final_parent_qualification_still_required',true));
 delete from cp7_global_nonpo_envelope.work_scopes_v1
  where backend_pid=work_.backend_pid and transaction_id=work_.transaction_id and operation_id=p_id;
end $$;

create function cp7_global_nonpo_envelope.immutable_completion_v1()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin raise exception 'CP7_GLOBAL_COMPLETION_HISTORY_IMMUTABLE';end $$;
create trigger immutable_completion before update or delete on cp7_global_nonpo_envelope.scope_completions_v1
 for each row execute function cp7_global_nonpo_envelope.immutable_completion_v1();
create trigger no_truncate_completion before truncate on cp7_global_nonpo_envelope.scope_completions_v1
 for each statement execute function cp7_global_nonpo_envelope.immutable_completion_v1();
alter function cp7_global_nonpo_envelope.native_work_v1(text,uuid)owner to postgres;
alter function cp7_global_nonpo_envelope.bind_v1(text,uuid,text,text)owner to postgres;
alter function cp7_global_nonpo_envelope.finish_v1(text,uuid)owner to postgres;
alter function cp7_global_nonpo_envelope.immutable_completion_v1()owner to postgres;
revoke all on function cp7_global_nonpo_envelope.native_work_v1(text,uuid),
 cp7_global_nonpo_envelope.bind_v1(text,uuid,text,text),
 cp7_global_nonpo_envelope.finish_v1(text,uuid),
 cp7_global_nonpo_envelope.immutable_completion_v1()from public,anon,authenticated,service_role;
