"""Transfer integrity successor definitions; generated only from pinned AL.

No pricing/date policy selection, historical ledger mutation, new authority or
new facade. Installation and pre-use rollback are generated separately.
"""

from cp6_v2620al_build_sql import replace


IDENTITIES = (
    'erp.post_material_transfer_v2(uuid,uuid,bigint,text)',
    'erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)',
    'erp.guard_material_negative_stock()',
    'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)',
    'erp.refresh_material_cost_checkpoint(uuid,date)',
    'erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)',
)

MATERIAL_LOCKS = """  -- Serialize the complete material set before reading prices or stock.
  -- Item writes use the same locked DRAFT header through the existing API.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials m
  where exists(select 1 from erp.material_transfer_items i
    where i.transfer_id=v_header.id and i.material_id=m.id)
  order by m.id for update;
"""

POST_PREFLIGHT = MATERIAL_LOCKS + """
  -- Re-read after every lock wait. Never filter an invalid line out of a POST.
  if exists(select 1 from erp.material_transfer_items i
    left join erp.materials m on m.id=i.material_id
    where i.transfer_id=v_header.id and (m.id is null or not m.is_active)) then
    raise exception 'AM_TRANSFER_REQUIRES_EVERY_MATERIAL_ACTIVE';
  end if;
  if exists(select 1 from erp.material_transfer_items i join erp.materials m on m.id=i.material_id
    where i.transfer_id=v_header.id and
      (i.qty<=0 or i.qty::text in('NaN','Infinity','-Infinity')
       or (m.material_type='FABRIC')<>(i.roll_id is not null)
       or (i.roll_id is not null and not exists(select 1 from erp.material_rolls mr
          where mr.id=i.roll_id and mr.material_id=i.material_id)))) then
    raise exception 'AM_TRANSFER_INVALID_QUANTITY_OR_ROLL_LINEAGE';
  end if;
"""

# Every legacy writer emits OUT/IN pairs in line order. Duplicate quantities
# have an explicit ordinal within their source/material/roll/time group. Never
# select an arbitrary first OUT, use the latest material average for an IN, or
# rewrite input/original snapshots during subsequent recost.
PAIR_MAP = """
  with active as (
    select m.*,row_number() over(partition by m.source_id,m.roll_id,m.physical_at,
        abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
    from erp.material_stock_movements m
    where m.material_id=p_material_id and m.source_type='MATERIAL_TRANSFER'
      and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ), pairs as (
    select i.id incoming,o.id outgoing
    from active i join active o on o.source_id=i.source_id
      and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
      and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
      and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
    where i.movement_type='TRANSFER_IN' and i.qty_signed>0
      and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
      and o.location_id<>i.location_id
  )
  select coalesce((select jsonb_object_agg(incoming::text,outgoing::text) from pairs),'{}'::jsonb),
    (select count(*) from active),(select count(*) from pairs)
  into v_transfer_pairs,v_transfer_rows,v_transfer_pair_count;
  if v_transfer_rows<>2*v_transfer_pair_count then
    raise exception 'AM_TRANSFER_PAIR_LINEAGE_UNPROVEN for material %',p_material_id;
  end if;

  -- The cost engine excludes a source and its linked inverse together. Apply
  -- the identical effective-history rule at each physical location/roll too;
  -- this preserves atomic receipt replacement and existing cancellation rules.
  select min(prefix) into v_location_minimum from (
    select sum(m.qty_signed) over(partition by m.location_id,m.roll_id
      order by m.physical_at,coalesce(o.system_created_at,m.system_created_at),
        coalesce(o.id,m.id),(o.id is not null) rows unbounded preceding) prefix
    from erp.material_stock_movements m
    left join erp.material_stock_movements o on o.id=(v_transfer_pairs->>m.id::text)::uuid
    where m.material_id=p_material_id and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ) effective_history;
  if v_location_minimum<0 then
    raise exception 'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY for material %',p_material_id;
  end if;
"""

PAIR_VARIABLES = """  v_transfer_pairs jsonb;
  v_transfer_rows bigint;
  v_transfer_pair_count bigint;
  v_location_minimum numeric;"""

PAIR_JOIN = """  left join erp.material_stock_movements paired_out
    on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
"""

PAIR_ORDER = """msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
      coalesce(paired_out.id,msm.id),(paired_out.id is not null)"""

# A pre-existing checkpoint can carry the old transfer error. Refuse that
# history instead of treating installation of AM as proof of corrected values.
# This validates the stored recurrence; it does not post an adjustment or choose
# a financial date policy. A full authorized recost uses the engine above.
CHECKPOINT_HISTORY = """
  if exists(
    with history as (
      select msm.id,msm.qty_signed,msm.unit_cost_snapshot,msm.movement_type,msm.source_type,
        h.movement_id,h.stock_before,h.stock_after,h.average_before,h.average_after,
        h.movement_qty,h.movement_unit_cost,paired_out.unit_cost_snapshot paired_cost,
        sum(msm.qty_signed) over w expected_stock,
        lag(h.average_after,1,0::numeric) over w previous_average
      from erp.material_stock_movements msm
      left join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=msm.material_id
      left join erp.material_stock_movements paired_out on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
      where msm.material_id=p_material_id and msm.physical_at<v_cutoff
        and msm.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      window w as(order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
        coalesce(paired_out.id,msm.id),(paired_out.id is not null) rows unbounded preceding)
    )
    select 1 from history where movement_id is null
      or movement_qty is distinct from qty_signed
      or movement_unit_cost is distinct from unit_cost_snapshot
      or stock_before is distinct from expected_stock-qty_signed
      or stock_after is distinct from expected_stock
      or average_before is distinct from previous_average
      or (qty_signed<0 and movement_unit_cost is distinct from average_before)
      or (movement_type='TRANSFER_IN' and source_type='MATERIAL_TRANSFER'
          and movement_unit_cost is distinct from paired_cost)
      or average_after is distinct from case
        when stock_after=0 then 0
        when qty_signed<0 then average_before
        else round((stock_before*average_before+qty_signed*movement_unit_cost)/nullif(stock_after,0),6)
      end
  ) then
    raise exception 'AM_LEGACY_COST_CHECKPOINT_REQUIRES_HISTORY_REVIEW for material %',p_material_id;
  end if;
"""

TRANSFER_IN_COST = """      if r.movement_type='TRANSFER_IN' and r.source_type='MATERIAL_TRANSFER' then
        -- The paired OUT must already have been replayed (or retained by the
        -- closed-period checkpoint). Its historical cost is the incoming cost,
        -- including a transfer of the entire balance that temporarily hits 0.
        select o.unit_cost_snapshot into v_cost
        from erp.material_stock_movements o
        join erp.material_cost_history h on h.movement_id=o.id and h.material_id=o.material_id
        where o.id=(v_transfer_pairs->>r.id::text)::uuid and o.material_id=p_material_id
          and o.is_cost_recalculated;
        if not found or v_cost is null then
          raise exception 'AM_TRANSFER_OUT_COST_NOT_REPLAYED for movement %',r.id;
        end if;
      elsif r.movement_type='REVERSAL' and r.reversal_of_id is not null then
"""


def definitions(src):
    post = src[IDENTITIES[0]][1]
    post = replace(post, '  v_cost numeric(24,6);',
        '  v_cost numeric(24,6);\n  v_move_at timestamptz;')
    post = replace(post, '  if not exists (\n    select 1 from erp.locations l',
        "  perform 1 from erp.locations where id in(v_header.from_location_id,v_header.to_location_id)\n"
        "    order by id for share;\n  if not exists (\n    select 1 from erp.locations l")
    post = replace(post, '  for r in\n    select i.*, m.moving_average_cost',
        POST_PREFLIGHT+'\n  for r in\n    select i.*, m.moving_average_cost')
    post = replace(post, 'join erp.materials m on m.id = i.material_id and m.is_active',
        'join erp.materials m on m.id = i.material_id')
    post = replace(post, '    v_cost := coalesce(r.moving_average_cost, 0);',
        "    -- Transfers have no independent acquisition price. The chronological\n"
        "    -- replay derives both original snapshots from the actual OUT cost.\n"
        "    v_cost := null;\n"
        "    v_move_at := greatest(clock_timestamp(),v_move_at+interval '1 microsecond');")
    column = '      input_unit_cost, source_type, source_id, physical_at, created_by, note'
    assert post.count(column) == 2
    post = post.replace(column, '      input_unit_cost, source_type, source_id, physical_at, system_created_at, created_by, note')
    values = "      v_cost, 'MATERIAL_TRANSFER', v_header.id, v_header.physical_at,"
    assert post.count(values) == 2
    post = post.replace(values, values+' v_move_at,')
    post = replace(post, "    insert into erp.material_stock_movements(\n      material_id, roll_id, location_id, movement_type, qty_signed,\n      input_unit_cost, source_type, source_id, physical_at, system_created_at, created_by, note\n    ) values (\n      r.material_id, r.roll_id, v_header.to_location_id",
        "    v_move_at := greatest(clock_timestamp(),v_move_at+interval '1 microsecond');\n"
        "    insert into erp.material_stock_movements(\n      material_id, roll_id, location_id, movement_type, qty_signed,\n      input_unit_cost, source_type, source_id, physical_at, system_created_at, created_by, note\n    ) values (\n      r.material_id, r.roll_id, v_header.to_location_id")
    post = replace(post, '  update erp.material_transfers\n  set status',
        "  if (select count(*) from erp.material_stock_movements\n"
        "      where source_type='MATERIAL_TRANSFER' and source_id=v_header.id)\n"
        "     <>2*(select count(*) from erp.material_transfer_items where transfer_id=v_header.id) then\n"
        "    raise exception 'AM_TRANSFER_INCOMPLETE_MOVEMENT_SET';\n  end if;\n\n"
        '  update erp.material_transfers\n  set status')
    reverse = replace(src[IDENTITIES[1]][1],
        '  -- Reverse destination IN first',MATERIAL_LOCKS+'\n  -- Reverse destination IN first')
    reverse = replace(reverse,
        '      input_unit_cost, source_type, source_id, physical_at, created_by,',
        '      input_unit_cost, unit_cost_snapshot, source_type, source_id, physical_at, created_by,')
    reverse = replace(reverse,
        "      r.unit_cost_snapshot, 'MATERIAL_TRANSFER_REVERSAL', v_header.id,",
        "      r.unit_cost_snapshot, r.unit_cost_snapshot, 'MATERIAL_TRANSFER_REVERSAL', v_header.id,")
    guard = replace(src[IDENTITIES[2]][1], 'begin\n  if new.qty_signed>=0',
        "begin\n  -- All legs acquire the material row before location/roll locks and FK\n"
        "  -- checks, in the same order as chronological recost. The next SQL\n"
        "  -- statement observes the latest committed stock after any wait.\n"
        "  perform 1 from erp.accounting_period_control where singleton_id=1 for share;\n"
        "  perform 1 from erp.materials where id=new.material_id for update;\n"
        "  if not found then raise exception 'Material not found'; end if;\n"
        '  if new.qty_signed>=0')
    core = replace(src[IDENTITIES[3]][1], '  v_use_checkpoint boolean:=false;',
        '  v_use_checkpoint boolean:=false;\n  v_cutoff timestamptz;\n'+PAIR_VARIABLES)
    core = replace(core, "  if not found then raise exception 'Material not found'; end if;\n",
        "  if not found then raise exception 'Material not found'; end if;\n"+PAIR_MAP)
    core = replace(core, "      if r.movement_type='REVERSAL' and r.reversal_of_id is not null then\n",TRANSFER_IN_COST)
    core = replace(core, '    select * from erp.material_stock_movements msm\n',
        '    select msm.* from erp.material_stock_movements msm\n'+PAIR_JOIN)
    core = replace(core, '    order by msm.physical_at,msm.system_created_at,msm.id\n    for update',
        '    order by '+PAIR_ORDER+'\n    for update of msm')
    old_cutoff='(msm.physical_at,msm.system_created_at,msm.id)>(v_cp.last_physical_at,v_cp.last_system_created_at,v_cp.last_movement_id)'
    assert core.count(old_cutoff)==2
    # A checkpoint is a complete closed business date, never half a relocation.
    core=core.replace(old_cutoff,'erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date')
    core = replace(core, '      v_use_checkpoint:=true;',
        "      v_cutoff:=((v_cp.checkpoint_date+1)::timestamp at time zone 'Asia/Jakarta');\n"
        +CHECKPOINT_HISTORY+"\n      v_use_checkpoint:=true;")
    checkpoint = replace(src[IDENTITIES[4]][1], '  v_cutoff timestamptz;',
        '  v_cutoff timestamptz;\n'+PAIR_VARIABLES)
    checkpoint = replace(checkpoint, "  if not found then raise exception 'Material not found'; end if;\n",
        "  if not found then raise exception 'Material not found'; end if;\n"+PAIR_MAP+CHECKPOINT_HISTORY)
    checkpoint = replace(checkpoint,
        '  join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=p_material_id\n',
        '  join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=p_material_id\n'+PAIR_JOIN)
    checkpoint = replace(checkpoint,
        '  order by msm.physical_at desc,msm.system_created_at desc,msm.id desc',
        '  order by msm.physical_at desc,coalesce(paired_out.system_created_at,msm.system_created_at) desc,\n'
        '    coalesce(paired_out.id,msm.id) desc,(paired_out.id is not null) desc')
    save = replace(src[IDENTITIES[5]][1],
        "    if v_action = 'DELETE' then\n      delete from erp.material_transfers where id = v_id;",
        "    if v_action = 'DELETE' then\n"
        "      -- Remove DRAFT children while their locked parent still exists;\n"
        "      -- the original parent trigger must continue validating every row.\n"
        "      delete from erp.material_transfer_items where transfer_id=v_id;\n"
        "      delete from erp.material_transfers where id = v_id;")
    return [post, reverse, guard, core, checkpoint, save]
