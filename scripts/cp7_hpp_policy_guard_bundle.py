"""HPP01 (Astra ASTRA-CP17-HPP-01, Fable R1-02): a contractor HPP policy change may not leave an ACTIVE attendance
HPP pool on a stale basis.

The Native erp.set_contractor_hpp_policy_v1 refuses a policy slice only for contractors already recorded in an ACTIVE
pool's child rows. A contractor who was excluded before (no policy) is not a member, so adding his policy was accepted,
and the pool's own validator then answered STALE_POOL_INPUT while the pool stayed ACTIVE (1000/10/100). Forward delta on
that one Native function: after the new version is written, every ACTIVE pool from the start of the touched policy
slice onward is rebuilt with the Native manifest builder; if a pool's basis changes and the change involves this
contractor (in the stored or the rebuilt manifest), the whole write is refused. Cancelling the pool first and building
a replacement stays the lawful path. Pool activation takes the same contractor advisory lock for every contractor
with facts in its period (erp._cp3_lock_manifest_contractors), so an activation and a policy write serialize.
"""
SIGNATURE='erp.set_contractor_hpp_policy_v1(jsonb,uuid,uuid)'
ANCHOR="  ) returning * into v_new;\n"
CHANGE=ANCHOR+"""
  -- HPP01 (CP1-CP7 audit fix, cp7_hpp_policy_guard_bundle.py): a policy write that changes the basis of an ACTIVE
  -- attendance HPP pool, by this contractor, is refused; cancel that pool first, then write the policy.
  perform 1 from erp.attendance_hpp_pools hp
   where hp.status='ACTIVE'
     and hp.period_end>=least(v_current.effective_from,v_effective_from)
     and erp._build_attendance_hpp_manifest_v1(hp.period_start,hp.period_end) is distinct from hp.source_manifest
     and (jsonb_path_exists(hp.source_manifest,'$.**.contractor_id ? (@ == $c)',jsonb_build_object('c',v_contractor_id))
      or jsonb_path_exists(erp._build_attendance_hpp_manifest_v1(hp.period_start,hp.period_end),'$.**.contractor_id ? (@ == $c)',jsonb_build_object('c',v_contractor_id)));
  if found then
    raise exception 'CP7_HPP_POLICY_CHANGES_ACTIVE_POOL: kebijakan HPP mandor ini mengubah dasar pool HPP absensi yang sudah AKTIF. Batalkan pool itu dulu, lalu simpan kebijakan dan buat pool pengganti.';
  end if;
"""


def patched(definition):
    assert definition.count(ANCHOR)==1,('HPP01_NATIVE_POLICY_SOURCE_CHANGED',ANCHOR)
    return definition.replace(ANCHOR,CHANGE,1)


def capture(cur,originals):
    assert SIGNATURE not in originals,'HPP01_NATIVE_ALREADY_CAPTURED'
    originals[SIGNATURE]=cur.execute('select pg_get_functiondef(%s::regprocedure)',(SIGNATURE,)).fetchone()[0]
    patched(originals[SIGNATURE])


def expected_definitions(originals):
    return {SIGNATURE:patched(originals[SIGNATURE])}


def extension():
    return """-- HPP01: a policy write may not leave an ACTIVE attendance HPP pool stale (cp7_hpp_policy_guard_bundle.py).
do $hpp01$
declare definition text;
begin
 definition:=pg_get_functiondef('"""+SIGNATURE+"""'::regprocedure);
 if (length(definition)-length(replace(definition,$anchor$"""+ANCHOR+"""$anchor$,'')))<>length($anchor$"""+ANCHOR+"""$anchor$) then
  raise exception 'CP7_HPP01_NATIVE_POLICY_SOURCE_CHANGED';end if;
 execute replace(definition,$anchor$"""+ANCHOR+"""$anchor$,$changed$"""+CHANGE+"""$changed$);
end $hpp01$;
"""


def verify(cur):
    definition=cur.execute('select pg_get_functiondef(%s::regprocedure)',(SIGNATURE,)).fetchone()[0]
    assert 'CP7_HPP_POLICY_CHANGES_ACTIVE_POOL' in definition and definition.count('erp._build_attendance_hpp_manifest_v1')==2,'HPP01_POLICY_NOT_PATCHED'
    return dict(policy_write_cannot_leave_active_pool_stale=True)
