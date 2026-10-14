"""SG-01 pickup reversal: the two declared Native deltas the CP7 command (scripts/cp7-src/cutting-correction/pickup.sql) needs.

Both are forward, admit only writes made inside the command's own transaction for its own pickup/group
(cp7_cutting_correction.pickup_context), and are restored exactly on uninstall:
- erp.guard_cutting_pickup_lifecycle(): a POSTED pickup may become REVERSED, changing nothing but its reversal fields.
  Every other update or delete of a non-DRAFT pickup is still refused as before.
- erp.normalize_cutting_group_pickup(): the group's pickup time may be cleared although its fabric is posted (always true
  after a pickup). Laundry, posted work and finished-goods lots still refuse the clear exactly as before.
The Native pickup writer, its batches/allocations guard and every PO guard stay the accepted definitions.
"""
GUARD = 'erp.guard_cutting_pickup_lifecycle()'
NORMALIZE = 'erp.normalize_cutting_group_pickup()'
REVERSAL_FIELDS = "array['status','reversed_by','reversed_at','reversal_reason','row_version','updated_at']"
PATCHES = {
    GUARD: ("  if tg_op='DELETE' then\n",
            "  -- SG-01 (cp7_pickup_reversal_bundle.py): only the CP7 pickup reversal turns a POSTED pickup into REVERSED,\n"
            "  -- changing nothing but its reversal fields.\n"
            "  if tg_op='UPDATE' and old.status='POSTED' and new.status='REVERSED'\n"
            "     and cp7_cutting_correction.pickup_reversal_admitted(old.id) then\n"
            "    if (to_jsonb(new)-" + REVERSAL_FIELDS + ") is distinct from (to_jsonb(old)-" + REVERSAL_FIELDS + ") then\n"
            "      raise exception using errcode='42501',message='POSTED_CUTTING_PICKUP_IS_IMMUTABLE';\n"
            "    end if;\n"
            "    return new;\n"
            "  end if;\n"
            "  if tg_op='DELETE' then\n"),
    NORMALIZE: ("    if old.material_issue_posted\n",
                "    -- SG-01 (cp7_pickup_reversal_bundle.py): the CP7 pickup reversal clears the pickup time of a group\n"
                "    -- without downstream use; its fabric stays posted.\n"
                "    if (old.material_issue_posted and not cp7_cutting_correction.pickup_group_admitted(old.id))\n"),
}


def patched(signature, definition):
    anchor, change = PATCHES[signature]
    assert definition.count(anchor) == 1, ('PICKUP_REVERSAL_NATIVE_SOURCE_CHANGED', signature)
    return definition.replace(anchor, change, 1)


def capture(cur, originals):
    for signature in PATCHES:
        assert signature not in originals, ('PICKUP_REVERSAL_NATIVE_ALREADY_CAPTURED', signature)
        originals[signature] = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        patched(signature, originals[signature])


def expected_definitions(originals):
    return {signature: patched(signature, originals[signature]) for signature in PATCHES}


def extension():
    blocks = []
    for n, (signature, (anchor, change)) in enumerate(PATCHES.items()):
        blocks.append("do $pickup" + str(n) + "$\ndeclare definition text;\nbegin\n definition:=pg_get_functiondef('" + signature + "'::regprocedure);\n"
                      " if (length(definition)-length(replace(definition,$anchor$" + anchor + "$anchor$,'')))<>length($anchor$" + anchor + "$anchor$) then\n"
                      "  raise exception 'CP7_PICKUP_REVERSAL_NATIVE_SOURCE_CHANGED: %','" + signature + "';end if;\n"
                      " execute replace(definition,$anchor$" + anchor + "$anchor$,$changed$" + change + "$changed$);\nend $pickup" + str(n) + "$;\n")
    return '-- SG-01 declared Native deltas (cp7_pickup_reversal_bundle.py).\n' + ''.join(blocks)


def verify(cur):
    for signature, (anchor, change) in PATCHES.items():
        definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert change in definition, ('PICKUP_REVERSAL_NATIVE_NOT_PATCHED', signature)
    for signature, owner, secdef in ((GUARD, 'postgres', True), (NORMALIZE, 'postgres', False)):
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef from pg_proc where oid=%s::regprocedure', (signature,)).fetchone() == (owner, secdef), signature
    for name in ('pickup_reversal_admitted(uuid)', 'pickup_group_admitted(uuid)'):
        sig = 'cp7_cutting_correction.' + name
        for who in ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_cutting_read', 'cp7_cutting_write'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
    return dict(pickup_reversal_native_deltas=sorted(PATCHES), pickup_writer_unchanged='erp.save_cutting_pickup_v1(jsonb,uuid,bigint)')
