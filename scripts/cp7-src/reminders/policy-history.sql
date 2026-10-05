-- Stable, paged immutable policy history, scoped by current Original and rights.
create function cp7_reminder_native.policy_history(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;workspace jsonb;rows jsonb;before_rev bigint;through_rev bigint;latest bigint;total bigint;next_rev text;
begin
 if jsonb_typeof(p)is distinct from'object'
  or not(p?&array['run_id','rule_id','scope_kind','scope_key','before_revision','through_revision','limit'])
  or(select count(*)from jsonb_object_keys(p))<>7 or p->'limit'is distinct from'25'::jsonb
  or exists(select 1 from jsonb_each(p)e where e.key not in('before_revision','through_revision','limit')and jsonb_typeof(e.value)<>'string')
  or p->>'rule_id'not in('PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED','AR_DUE','AP_DUE')
  or jsonb_typeof(p->'before_revision')not in('string','null')or jsonb_typeof(p->'through_revision')not in('string','null')
  or p->>'before_revision'is not null and(p->>'before_revision'!~'^[1-9][0-9]{0,18}$'or(p->>'before_revision')::numeric>9223372036854775807)
  or p->>'through_revision'is not null and(p->>'through_revision'!~'^[1-9][0-9]{0,18}$'or(p->>'through_revision')::numeric>9223372036854775807)
 then raise exception 'CP7_POLICY_HISTORY_PAYLOAD';end if;
 a:=cp7_reminder_native.access_now((p->>'run_id')::uuid);
 perform cp7_reminder_native.recheck(a,case p->>'rule_id'when'AR_DUE'then'AR'when'AP_DUE'then'MATERIAL_AP'else null end);
 if p->>'scope_kind'='GLOBAL'then
  if p->>'scope_key'<>'*'then raise exception 'CP7_RULE_POLICY_SCOPE';end if;
 elsif p->>'scope_kind'='TARGET'and p->>'rule_id'in('PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED')then
  if not exists(select 1 from jsonb_array_elements(a->'analysis'->'analysis'->'recommendations')x where x->'target'->>'key'=p->>'scope_key')then
   raise exception using errcode='42501',message='CP7_RULE_POLICY_TARGET_UNAVAILABLE';end if;
 else raise exception 'CP7_RULE_POLICY_SCOPE';end if;
 select max(q.revision)into latest from cp7_reminder_native.rule_policies q
  where q.rule_id=p->>'rule_id'and q.scope_kind=p->>'scope_kind'and q.scope_key=p->>'scope_key';
 before_rev:=(p->>'before_revision')::bigint;through_rev:=coalesce((p->>'through_revision')::bigint,latest);
 if p->>'through_revision'is not null and(through_rev>coalesce(latest,0)or not exists(select 1 from cp7_reminder_native.rule_policies q
  where q.rule_id=p->>'rule_id'and q.scope_kind=p->>'scope_kind'and q.scope_key=p->>'scope_key'and q.revision=through_rev))then
  raise exception 'CP7_POLICY_HISTORY_BOUNDARY';end if;
 if before_rev is not null and(through_rev is null or before_rev>through_rev)then raise exception 'CP7_POLICY_HISTORY_BOUNDARY';end if;
 select count(*)into total from cp7_reminder_native.rule_policies q where q.rule_id=p->>'rule_id'and q.scope_kind=p->>'scope_kind'
  and q.scope_key=p->>'scope_key'and q.revision<=through_rev;
 select coalesce(jsonb_agg(jsonb_build_object('policy_id',id,'rule_id',rule_id,'scope_kind',scope_kind,'scope_key',scope_key,
  'revision',revision::text,'previous_id',previous_id,'config',config,'reason',reason,'created_at',created_at,'created_by',created_by)order by revision desc),'[]')into rows
  from(select *from cp7_reminder_native.rule_policies q where q.rule_id=p->>'rule_id'and q.scope_kind=p->>'scope_kind'
   and q.scope_key=p->>'scope_key'and q.revision<=through_rev and(before_rev is null or q.revision<before_rev)order by q.revision desc limit 25)page;
 if jsonb_array_length(rows)>0 and(rows->-1->>'revision')::bigint>1 then next_rev:=rows->-1->>'revision';end if;
 workspace:=cp7_reminder_native.policy_workspace((p->>'run_id')::uuid);perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('contract_version','cp7.native-policy-history.v1','actor_scope_id',auth.uid(),'workspace',workspace,
  'rule_id',p->'rule_id','scope_kind',p->'scope_kind','scope_key',p->'scope_key','through_revision',through_rev::text,
  'before_revision',before_rev::text,'rows',rows,'total',total::text,'limit',25,'next_before_revision',next_rev,
  'page_complete',true,'history_immutable',true,'external_delivery_enabled',false);
end $$;
alter function cp7_reminder_native.policy_history(jsonb)owner to cp7_reminder;
revoke all on function cp7_reminder_native.policy_history(jsonb)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_reminder_policy_history_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.policy_history(p_query)$$;
alter function public.erp_cp7_get_reminder_policy_history_v1(jsonb)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_reminder_policy_history_v1(jsonb)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_reminder_policy_history_v1(jsonb)to authenticated;
