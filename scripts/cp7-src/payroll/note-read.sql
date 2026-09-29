create function cp7_payroll.note_project_card(p_card jsonb,p_financial boolean) returns jsonb
language sql immutable security invoker set search_path='' as $$
 select case when p_financial then p_card else jsonb_set(p_card-'remaining_amount','{lines}',(select coalesce(jsonb_agg(l-'rate'-'amount' order by ord),'[]') from jsonb_array_elements(p_card->'lines') with ordinality a(l,ord))) end
$$;

create function cp7_payroll.note_document(p_note cp7_payroll.notes,p_financial boolean) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',p_note.id,'note_number',p_note.note_number,'contractor_id',p_note.contractor_id,'contractor_name',c.contractor_name,
  'note_date',p_note.note_date,'period_start',p_note.period_start,'period_end',p_note.period_end,'notes',p_note.notes,'status',p_note.status,'row_version',p_note.row_version::text,
  'target_payroll_id',p_note.target_payroll_id,'target_version',p_note.target_version,'posted_payroll_id',p_note.posted_payroll_id,
  'payroll_number',p.payroll_number,'payroll_status',p.status,'posted_at',p_note.posted_at,'void_reason',p_note.void_reason,
  'created_at',p_note.created_at,'updated_at',p_note.updated_at,
  'cards',(select jsonb_agg(cp7_payroll.note_project_card(x,p_financial) order by ord) from jsonb_array_elements(p_note.cards) with ordinality a(x,ord)))
  ||case when p_financial then jsonb_build_object('amount',(select sum((x->>'remaining_amount')::numeric)::text from jsonb_array_elements(p_note.cards) x)) else '{}'::jsonb end
 from erp.contractors c left join erp.payroll_settlements p on p.id=coalesce(p_note.posted_payroll_id,p_note.target_payroll_id) where c.id=p_note.contractor_id
$$;

create function cp7_payroll.note_workspace(p_section text,p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;w jsonb;rows jsonb;total bigint;n integer;off integer;contractor uuid;ident uuid;q text;
begin
 a:=cp7_payroll.access_now('NOTA');
 if p_section is null or p_section not in('SOURCES','NOTES','PAYROLLS') or jsonb_typeof(p_query) is distinct from 'object'
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','contractor_id','id','limit','offset'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','contractor_id','id') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query?'limit' and (jsonb_typeof(p_query->'limit')<>'number' or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset' and (jsonb_typeof(p_query->'offset')<>'number' or(p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_NOTA_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));contractor:=(p_query->>'contractor_id')::uuid;ident:=(p_query->>'id')::uuid;n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 or (ident is not null and p_section<>'NOTES') or(p_section='PAYROLLS' and contractor is null) then raise exception 'CP7_NOTA_QUERY';end if;
 if p_section='SOURCES' then
  w:=cp7_payroll.source_workspace(p_query-'id');
  select coalesce(jsonb_agg(x||jsonb_build_object('claimed_by_note',c.note_id) order by ord),'[]') into rows from jsonb_array_elements(w->'page'->'rows') with ordinality a(x,ord) left join cp7_payroll.card_claims c on c.card_key=x->>'card_key';
  w:=jsonb_set(w,'{page,rows}',rows);
 else
  if p_section='NOTES' then
   with filtered as materialized(select h.* from cp7_payroll.notes h join erp.contractors c on c.id=h.contractor_id
    where (contractor is null or h.contractor_id=contractor) and(ident is null or h.id=ident) and(q='' or strpos(lower(concat_ws(' ',h.note_number,c.contractor_name,h.notes)),lower(q))>0)),
   page as(select * from filtered order by created_at desc,id limit n offset off)
   select(select count(*) from filtered),coalesce(jsonb_agg(cp7_payroll.note_document(page::cp7_payroll.notes,(a->>'financial')::boolean) order by created_at desc,id),'[]') into total,rows from page;
  else
   with filtered as materialized(select p.* from erp.payroll_settlements p where p.contractor_id=contractor and p.status in('DRAFT','CALCULATED','REVIEW') and(q='' or strpos(lower(p.payroll_number),lower(q))>0)),
   page as(select * from filtered order by period_end desc,id limit n offset off)
   select(select count(*) from filtered),coalesce(jsonb_agg(jsonb_build_object('id',id,'payroll_number',payroll_number,'contractor_id',contractor_id,'period_start',period_start,'period_end',period_end,'status',status,'row_version',row_version::text) order by period_end desc,id),'[]') into total,rows from page;
  end if;
  w:=jsonb_build_object('page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
 end if;
 return w||jsonb_build_object('contract_version','cp7.nota-workspace.v1','section',p_section,'read_at',statement_timestamp(),'financial_captured',a->'financial','can_post',a->'can_post_nota');
end $$;
create function public.erp_cp7_get_nota_workspace_v1(p_section text,p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_payroll.note_workspace(p_section,p_query)$$;
