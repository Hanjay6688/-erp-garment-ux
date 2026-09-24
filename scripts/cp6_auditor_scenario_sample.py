"""Sample auditor scenario for scripts/cp6_auditor_scenario.py (smoke test of the runner on push; auditors replace it with
their own file through the workflow input). It only replays the writer's control case for reversed write-offs, so a green
run shows the runtime works; it is not independent evidence by itself."""
import cp6_az_probe as azp


def cases(cur,today):
    return [('SAMPLE:WRITE_OFF_REVERSED_THEN_LATE_INVOICE_LOWER',lambda:azp.writeoff_reversal(cur,today,'8.25'))]
