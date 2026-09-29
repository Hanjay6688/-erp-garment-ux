-- Frozen identity is read from the captured run. Current regrouping is separate.
create function cp7_identity.source_identity(p_run uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' set timezone='Asia/Jakarta' as $$
declare a jsonb; r cp7_private.analysis_runs%rowtype; at timestamptz; current_members jsonb; result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then
  raise exception using errcode='25001',message='CP7_FRESH_ACCESS_TRANSACTION_REQUIRED';
 end if;
 a:=cp7_private.access_now();
 select * into r from cp7_private.analysis_runs where id=p_run and actor=auth.uid();
 if not found then raise exception using errcode='42501',message='CP7_RUN_UNAVAILABLE';end if;
 at:=clock_timestamp();
 select coalesce(jsonb_agg(jsonb_build_object('sku_id',s.id,'sku',s.sku,'version_id',v.id,'revision',v.revision::text) order by v.id),'[]')
 into current_members
 from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
 join erp.bf_skus_v1 s on s.id=v.sku_id
 where m.product_root=r.root_id and v.effective_from<=at and (v.effective_to is null or v.effective_to>at);
 if jsonb_array_length(current_members)>1 then
  raise exception using errcode='22023',message='CP7_IDENTITY_CONFLICT';
 end if;
 result:=jsonb_build_object('contract_version','cp7.source-identity.v1','run_id',r.id,'root_id',r.root_id,
  'physical_at_capture',r.payload->'sources'->'physical',
  'original',jsonb_build_object('basis','AT_CAPTURE','effective_as_of',r.payload->'snapshot'->'effective_as_of',
    'known_as_of',r.payload->'snapshot'->'known_as_of','commercial',r.payload->'sources'->'commercial'),
  'current_restatement',jsonb_build_object('basis','CURRENT_RESTATED','generated_at',at,'commercial',current_members),
  'membership_changed',current_members is distinct from r.payload->'sources'->'commercial');
 if cp7_private.access_now()<>a then raise exception using errcode='42501',message='CP7_ACCESS_CHANGED';end if;
 return result;
end $$;
