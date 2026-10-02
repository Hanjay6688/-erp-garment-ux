-- Immutable revision actor UUID; current profile label is presentation only.
-- Do not claim a renamed profile is the name captured at correction time.
create function cp7_note.workspace_with_actors(p_sale uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;w jsonb;history jsonb;
begin
 a:=cp7_note.access_now();w:=cp7_note.workspace(p_sale);
 select coalesce(jsonb_agg(h.value||jsonb_build_object('actor_id',r.actor,
  'actor_display_name',(select nullif(btrim(u.full_name),'')from erp.app_users u where u.auth_user_id=r.actor),
  'actor_name_basis','CURRENT_PROFILE')order by r.revision),'[]')into history
 from jsonb_array_elements(w->'history')h(value)join cp7_note.revisions r on r.id=(h.value->>'revision_id')::uuid;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 return w||jsonb_build_object('contract_version','cp7.note-correction-workspace.v2','history',history);
end $$;
alter function cp7_note.workspace_with_actors(uuid)owner to postgres;
revoke all on function cp7_note.workspace_with_actors(uuid)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
grant execute on function cp7_note.workspace_with_actors(uuid)to cp7_sales_write;
create function public.erp_cp7_get_note_correction_v2(p_sale uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_note.workspace_with_actors(p_sale)$$;
grant create on schema public to cp7_sales_write;
alter function public.erp_cp7_get_note_correction_v2(uuid)owner to cp7_sales_write;
revoke create on schema public from cp7_sales_write;
revoke all on function public.erp_cp7_get_note_correction_v2(uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_note_correction_v2(uuid)to authenticated;
