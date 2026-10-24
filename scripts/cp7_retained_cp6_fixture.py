"""Complete labelled seed prerequisites before unchanged retained CP6 scenarios.

Only disposable Native fixtures call this helper. It never changes an original
case, a reporting result, a SQL definition, a posted source, or a business oracle.
"""
from datetime import date, timedelta
import cp6_aw_probe as aw


def prepare(cur, today, *, current, closed_through, evidence):
    evidence.update(fixture_only=True,owner_figures_used=False,
        original_case_bodies_changed=False,report_oracles_changed=False,
        before_original_scenario=True,current_AB=current)
    aw.api.admin(cur)
    if current:
        # This already-qualified preparation completes old seed payroll before
        # freezing its costs, and uses the OW07 CREATE/ACTIVATE Native facade.
        # Missing policy refuses; it never invents a contractor's policy.
        import cp7_p21_current_chain_rehearsal_probe as chain
        evidence['attendance_pools']=chain.prepare_attendance_pools(cur,today)
    # Some retained scenarios legitimately restore the original 31-Aug cutoff.
    # Fill its entire later attendance window, including today's reference read,
    # rather than rewriting that cutoff or shortening a report's window.
    start=min(date(2026,9,1),today-timedelta(days=8))
    aw.api.admin(cur)
    aw.boundary.historical.prior.set_open_period(cur,closed_through)
    evidence['attendance_window']=dict(start=str(start),end=str(today))
    evidence['seed_completion']=aw.quiet_seed(cur,start,today)
    aw.api.admin(cur)
    assert not evidence['seed_completion']['refused'],('RETAINED_CP6_SEED_COMPLETION_REFUSED',evidence)
    evidence['readiness_before_original_case']=cur.execute(
        'select erp.period_readiness_v1(%s,erp.period_completeness_from_v1())',(today,)).fetchone()[0]
    evidence['closed_through_before_original_case']=str(cur.execute(
        'select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0])
    assert evidence['closed_through_before_original_case']==str(closed_through)
    return evidence
