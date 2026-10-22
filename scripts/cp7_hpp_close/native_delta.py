"""Counted substitutions of three installed Native functions (OW-07).

erp.period_blockers_v1 gets one more `return query` (cp7_hpp_close.blockers_v1) before
its last, never-blocking GRNI row; every earlier family and row stays byte-for-byte.
Attendance pool activation and cancellation close the leftover WIP of a FINISHED PO
right after its HPP is synced to the GL, exactly as the pocket period writer does
(erp.sync_pocket_period_v1 in 20be), with the pool journal's own booking date.
"""
BLOCKERS='erp.period_blockers_v1(date,date)'
ACTIVATE='erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)'
CANCEL='erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)'
SIGNATURES=(BLOCKERS,ACTIVATE,CANCEL)
CODES=('POCKET_USAGE_UNALLOCATED','ATTENDANCE_POOL_NOT_ACTIVE','ATTENDANCE_POOL_POLICY_MISSING',
       'ATTENDANCE_POOL_SOURCE_UNCLEAR','ATTENDANCE_POOL_ZERO_OUTPUT')
GRNI="  -- GRNI: owner allows close with an estimate; reported, never blocking.\n"
HPP=("  -- OW-07 (cp7_hpp_close): pocket fabric and attendance cost not yet divided into PO HPP.\n"
     "  return query select * from cp7_hpp_close.blockers_v1(p_through);\n\n")


def residual(po,reason):
    return ("    if exists(select 1 from erp.production_orders where id="+po+" and status='FINISHED') then\n"
            "      perform erp.sync_finished_po_wip_residual("+po+",v_effective_date,'"+reason+" '||v_pool.id::text);\n"
            "    end if;\n")


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW07_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW07_NATIVE_DELTA_SET_CHANGED')
    result=dict(originals)
    if 'cp7_hpp_close' in result[BLOCKERS]or 'HPP_POOL' in result[BLOCKERS]:raise ValueError('OW07_BLOCKERS_ALREADY_PATCHED')
    result[BLOCKERS]=once(result[BLOCKERS],GRNI,HPP+GRNI,BLOCKERS+':hpp-pool')
    for sig,po,reason in((ACTIVATE,'v_line.po_id','Attendance HPP pool activation'),
                         (CANCEL,'v_po_id','Attendance HPP pool cancellation')):
        if 'sync_finished_po_wip_residual' in result[sig]:raise ValueError('OW07_POOL_ALREADY_PATCHED: '+sig)
        sync="    perform erp.sync_po_hpp_to_gl("+po+",v_effective_date);\n  end loop;"
        result[sig]=once(result[sig],sync,
            "    perform erp.sync_po_hpp_to_gl("+po+",v_effective_date);\n"+residual(po,reason)+"  end loop;",sig+':residual')
    return result
