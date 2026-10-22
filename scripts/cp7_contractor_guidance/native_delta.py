"""Counted substitutions of two installed OW05 readers (OW-05b).

cp7_contractor_correction.blockers_v1 passes each blocker row through
cp7_contractor_guidance.guide_v1, which replaces only its step text and adds the real
menu and an openable source reference. The rows, their order, ids and statuses stay.
cp7_contractor_correction.workspace_v1 returns the same keys plus the full after
steps and the stored correction history. The command, its review token rule, its
history row and every business writer stay byte-for-byte.
"""
BLOCKERS='cp7_contractor_correction.blockers_v1(uuid)'
WORKSPACE='cp7_contractor_correction.workspace_v1(uuid)'
SIGNATURES=(BLOCKERS,WORKSPACE)
KINDS=('PO_STATE','PICKUP_SOURCE','PAYROLL','ATTENDANCE_POOL','POCKET_POOL','QC','FG_LOT','LAUNDRY','SEWING','WORK',
       'WORK_JOURNAL','ACCESSORY_NOTE','MATERIAL_ISSUE','REWORK','BS','SCRAP','PICKUP_DRAFT','GROUP_STATE','WIP_HISTORY')
AGG=" select coalesce(jsonb_agg(d.item order by(d.item->>'order')::integer,d.item->>'id'),'[]')from(\n"
GUIDED=" select coalesce(jsonb_agg(cp7_contractor_guidance.guide_v1(d.item)order by(d.item->>'order')::integer,d.item->>'id'),'[]')from(\n"
AFTER=("  'after_step','Catat ulang hasil jahit untuk mandor yang benar dari WIP & Jahit. Periksa pilihan tarif PO lama atau tarif"
       " mandor baru pada waktu jahit asli; buat ulang nota hanya sesudah hasilnya benar.',\n")
AFTER_GUIDED=("  'after_step',cp7_contractor_guidance.after_step_v1(),'after_steps',cp7_contractor_guidance.after_steps_v1(),\n"
              "  'history',cp7_contractor_guidance.history_v1(p_po),\n")


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW05B_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def kinds(blockers):
    """Every kind literal the predecessor reader can return, in source order."""
    import re
    return tuple(dict.fromkeys(re.findall(r"'kind','([A-Z_]+)'",blockers)))


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW05B_NATIVE_DELTA_SET_CHANGED')
    result=dict(originals)
    for sig in SIGNATURES:
        if 'cp7_contractor_guidance' in result[sig]:raise ValueError('OW05B_ALREADY_PATCHED: '+sig)
    if kinds(result[BLOCKERS])!=KINDS:raise ValueError('OW05B_BLOCKER_KINDS_CHANGED: '+repr(kinds(result[BLOCKERS])))
    result[BLOCKERS]=once(result[BLOCKERS],AGG,GUIDED,BLOCKERS)
    result[WORKSPACE]=once(result[WORKSPACE],AFTER,AFTER_GUIDED,WORKSPACE)
    return result
