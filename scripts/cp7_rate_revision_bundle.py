"""R3-09 (owner D16-2, D16-3, D16-4): the declared Native deltas the CP7 rate choice (scripts/cp7-src/cutting-correction/sewing.sql)
needs so a PO's work-rate snapshot can hold rate revisions: extra erp.po_work_component_snapshots rows of the same PO and
component, written only by the CP7 sewing command and registered in cp7_cutting_correction.rate_revisions.

All forward and restored exactly on uninstall:
- unique index erp.bf_work_snapshot_scope: (po_id, work_component_id, bf_sku_version_id) becomes
  (po_id, work_component_id, bf_sku_version_id, committed_at), nulls not distinct. The original definition is captured and
  put back; that restore refuses while rate revisions exist (they would be dropped silently otherwise).
- erp.bf_ensure_work_v1(uuid,timestamptz): a SKU pinned later takes the PO's original base rows only, not their revisions.
- erp.prepare_rework_component_line(): the SKU branch takes the latest snapshot row of the SKU and component, like the
  non-SKU branch of the same function already does (order by committed_at desc, id desc).
- erp.seed_bs_case_component_baseline(): the baseline row of a component names its latest snapshot row, in the same order;
  the quantity it records is per component and SKU and does not change.
Every Native guard that ties a wage line to its snapshot (erp.validate_work_completion, erp.guard_work_completion_posting_
consistency, erp.run_v268_financial_report_checks) stays the accepted definition: a revision is an ordinary snapshot row.
"""
ENSURE = 'erp.bf_ensure_work_v1(uuid,timestamp with time zone)'
REWORK = 'erp.prepare_rework_component_line()'
BASELINE = 'erp.seed_bs_case_component_baseline()'
INDEX = 'erp.bf_work_snapshot_scope'
INDEX_KEY = 'erp.po_work_component_snapshots#bf_work_snapshot_scope'
ORIGINAL_INDEX = ('CREATE UNIQUE INDEX bf_work_snapshot_scope ON erp.po_work_component_snapshots USING btree '
                  '(po_id, work_component_id, bf_sku_version_id) NULLS NOT DISTINCT')
NEW_INDEX = ('CREATE UNIQUE INDEX bf_work_snapshot_scope ON erp.po_work_component_snapshots USING btree '
             '(po_id, work_component_id, bf_sku_version_id, committed_at) NULLS NOT DISTINCT')
PATCHES = {
    ENSURE: ("   for base in select * from erp.po_work_component_snapshots where po_id=p_po and bf_sku_version_id is null order by sequence_no,id loop\n",
             "   -- R3-09 (cp7_rate_revision_bundle.py): the PO's original base rows; rate revisions are not bases.\n"
             "   for base in select * from erp.po_work_component_snapshots where po_id=p_po and bf_sku_version_id is null\n"
             "     and not exists(select 1 from cp7_cutting_correction.rate_revisions rr where rr.snapshot_id=po_work_component_snapshots.id)\n"
             "     order by sequence_no,id loop\n"),
    REWORK: ("        where s.po_id=v_case.po_id and v.sku_id=bf_sku and s.work_component_id=v_component.work_component_id;\n",
             "        where s.po_id=v_case.po_id and v.sku_id=bf_sku and s.work_component_id=v_component.work_component_id\n"
             "        -- R3-09 (cp7_rate_revision_bundle.py): the latest row, as the PO branch below.\n"
             "        order by s.committed_at desc,s.id desc limit 1;\n"),
    BASELINE: ("  where s.po_id=new.po_id and erp.bf_snapshot_matches_v1(s.id,new.cutting_group_id,new.product_id)\n"
               "  on conflict(bs_case_id,work_component_id) do nothing;\n",
               "  where s.po_id=new.po_id and erp.bf_snapshot_matches_v1(s.id,new.cutting_group_id,new.product_id)\n"
               "  -- R3-09 (cp7_rate_revision_bundle.py): one row per component names its latest snapshot row.\n"
               "  order by s.committed_at desc,s.id desc\n"
               "  on conflict(bs_case_id,work_component_id) do nothing;\n"),
}


def patched(signature, definition):
    anchor, change = PATCHES[signature]
    assert definition.count(anchor) == 1, ('RATE_REVISION_NATIVE_SOURCE_CHANGED', signature)
    return definition.replace(anchor, change, 1)


def index_definition(cur):
    return cur.execute("select pg_get_indexdef(%s::regclass)", (INDEX,)).fetchone()[0]


def restore_index():
    # Put the accepted index back; refused while revisions (two rows of one PO, component and SKU version) exist.
    return ("do $rate_index_restore$\nbegin\n"
            " if exists(select 1 from erp.po_work_component_snapshots group by po_id,work_component_id,bf_sku_version_id having count(*)>1) then\n"
            "  raise exception 'CP7_RATE_REVISIONS_IN_USE: restore the database backup taken before the CP7 install';end if;\n"
            " drop index " + INDEX + ";\n " + ORIGINAL_INDEX + ";\nend $rate_index_restore$;\n")


def capture(cur, originals):
    for signature in PATCHES:
        assert signature not in originals, ('RATE_REVISION_NATIVE_ALREADY_CAPTURED', signature)
        originals[signature] = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        patched(signature, originals[signature])
    assert index_definition(cur) == ORIGINAL_INDEX, ('RATE_REVISION_NATIVE_INDEX_CHANGED', index_definition(cur))
    originals[INDEX_KEY] = restore_index()


def expected_definitions(originals):
    return {signature: patched(signature, originals[signature]) for signature in PATCHES}


def extension():
    index = ("do $rate_index$\nbegin\n"
             " if pg_get_indexdef('" + INDEX + "'::regclass) is distinct from $i$" + ORIGINAL_INDEX + "$i$ then\n"
             "  raise exception 'CP7_RATE_REVISION_NATIVE_INDEX_CHANGED';end if;\n"
             " drop index " + INDEX + ";\n " + NEW_INDEX + ";\nend $rate_index$;\n")
    blocks = []
    for n, (signature, (anchor, change)) in enumerate(PATCHES.items()):
        blocks.append("do $rate" + str(n) + "$\ndeclare definition text;\nbegin\n definition:=pg_get_functiondef('" + signature + "'::regprocedure);\n"
                      " if (length(definition)-length(replace(definition,$anchor$" + anchor + "$anchor$,'')))<>length($anchor$" + anchor + "$anchor$) then\n"
                      "  raise exception 'CP7_RATE_REVISION_NATIVE_SOURCE_CHANGED: %','" + signature + "';end if;\n"
                      " execute replace(definition,$anchor$" + anchor + "$anchor$,$changed$" + change + "$changed$);\nend $rate" + str(n) + "$;\n")
    return '-- R3-09 declared Native deltas (cp7_rate_revision_bundle.py).\n' + index + ''.join(blocks)


def verify(cur):
    for signature, (anchor, change) in PATCHES.items():
        definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert change in definition, ('RATE_REVISION_NATIVE_NOT_PATCHED', signature)
    assert index_definition(cur) == NEW_INDEX, ('RATE_REVISION_INDEX_NOT_PATCHED', index_definition(cur))
    for signature in PATCHES:
        assert cur.execute('select pg_get_userbyid(proowner) from pg_proc where oid=%s::regprocedure', (signature,)).fetchone()[0] == 'postgres', signature
    return dict(rate_revision_native_deltas=sorted(PATCHES) + [INDEX_KEY],
                wage_guards_unchanged=['erp.validate_work_completion()', 'erp.guard_work_completion_posting_consistency()',
                                       'erp.run_v268_financial_report_checks()'])
