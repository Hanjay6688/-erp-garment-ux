create function cp7_identity.workspace_data(p_skus uuid[],p_at timestamptz) returns jsonb
language sql stable security invoker set search_path='' as $$
 with scope as materialized (
  select id,cp7_identity.membership(id,p_at) member from unnest(p_skus) id
 ), facts as (
  select s.id scope_id,s.member,p.*,
   coalesce(p.reviewed_members=(select array_agg(value::uuid order by value::uuid)
     from jsonb_array_elements_text(s.member->'members')),false) members_current
  from scope s left join lateral (
   select x.* from cp7_identity.production_policy x where x.sku_id=s.id order by x.revision desc limit 1
  ) p on true
 )
 select jsonb_build_object('contract_version','cp7.production-policy.v1','knowledge_mode','CURRENT',
  'generated_at',p_at,'rows',coalesce(jsonb_agg(case when member is null then
   jsonb_build_object('sku_id',scope_id,'status','UNAVAILABLE') else member||jsonb_build_object(
    'status','AVAILABLE','policy_revision',coalesce(revision,0)::text,
    'policy',jsonb_build_object('quality',case when revision is null then 'UNREVIEWED'
      when not members_current then 'MEMBERSHIP_CHANGED' else 'KNOWN' end,
     'state',case when members_current then state else null end,
     'last_reviewed_state',state,'reason',reason,'review_at',review_at,
     'review_due',coalesce(review_at<=p_at,false),'recorded_at',recorded_at)) end order by scope_id),'[]'))
 from facts
$$;

create function cp7_identity.workspace(p_skus uuid[]) returns jsonb
language plpgsql volatile security invoker set search_path='' set timezone='Asia/Jakarta' as $$
declare a jsonb; result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then
  raise exception using errcode='25001',message='CP7_FRESH_ACCESS_TRANSACTION_REQUIRED';
 end if;
 a:=cp7_identity.access_now(false);
 if p_skus is null or array_ndims(p_skus)<>1 or cardinality(p_skus) not between 1 and 200
    or (select count(distinct id) from unnest(p_skus) id)<>cardinality(p_skus) then
  raise exception using errcode='22023',message='CP7_POLICY_SCOPE_INVALID';
 end if;
 select cp7_identity.workspace_data(p_skus,clock_timestamp()) into result;
 if cp7_identity.access_now(false)<>a then
  raise exception using errcode='42501',message='CP7_POLICY_ACCESS_CHANGED';
 end if;
 return result;
end $$;
