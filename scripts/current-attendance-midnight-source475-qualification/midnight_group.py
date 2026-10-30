"""Exactly one attempt; original per-case day guard remains authoritative."""
from hashlib import sha256
from midnight_common import HERE, ROOT, ID, GROUP
import midnight_admission as admission
import midnight_factory as factory


def retain(native, report):
    path = native.r1.OUT / (GROUP + '.json')
    if not path.is_file():
        return
    raw = path.read_bytes()
    destination = ROOT / 'cp6-proof/t3' / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != raw:
        raise ValueError('MIDNIGHT_FIRST_RAW_ORIGINAL_CANNOT_BE_OVERWRITTEN')
    if not destination.exists():
        with destination.open('xb') as stream:
            stream.write(raw)
    report['midnight_strict_original'] = dict(name=path.name, bytes=len(raw), sha256=sha256(raw).hexdigest())


def run(native, control, state, report, verify, parent, product, cfg):
    gate = __import__('midnight_gate')
    gate.selected(cfg)

    def cases(cursor, today):
        with control.product_catalog(cursor):
            planned = factory.cases(cursor, today, state=state, evidence=report,
                accepted_parent14=parent, product=product, cfg=cfg)
        if len(planned) != 1 or planned[0][0] != ID:
            raise ValueError('MIDNIGHT_EXACT_ONE_CALLBACK_REQUIRED')
        return planned

    from cp7_catalog_state import exact_public_catalog
    try:
        with exact_public_catalog(native, retain_raw=True) as public:
            # Deliberately do not call strict_group or business_day.with_retry.
            # _strict_group_once includes the unchanged guard at original191.
            group = native._strict_group_once(GROUP, cases, verify)
    finally:
        retain(native, report)
    report.update(midnight_native1=group, public_catalog_observation=public,
        single_attempt=True, day_rollover_retry=False,
        fresh_original11_or14_reexecuted=False, retained_parent14_reexecuted=False)
    if group.get('business_day_retried') or group.get('business_day_attempts'):
        raise ValueError('MIDNIGHT_DAY_RETRY_FORBIDDEN')
    admission.exact_group(group, [ID])
    return group
