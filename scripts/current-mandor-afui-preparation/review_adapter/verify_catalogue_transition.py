"""Source-only candidate guard for the isolated Mandor correction adapter."""

from hashlib import md5, sha256
import json


ROUTINES = (
    "cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)",
    "cp7_credit.assert_initial_return_closed_v1(uuid)",
    "cp7_note.command(jsonb,uuid,text)",
)


def group_digest(rows):
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256(raw).hexdigest()


def verify_transition(before, after, raw_before, raw_after, footprint, installer_receipt):
    """Require the verified Mandor baseline and the exact additive footprint."""
    if len(before) != 22 or before.keys() != after.keys():
        raise ValueError("MANDOR_ADAPTER_ALL22_GROUPS_CHANGED")
    if set(raw_before) != set(ROUTINES) or raw_before != raw_after:
        raise ValueError("MANDOR_ADAPTER_NATIVE_RAW_AUTHORITY_CHANGED")
    old_pins = installer_receipt["predecessor_pg_get_functiondef_md5"]
    new_pins = installer_receipt["installed_pg_get_functiondef_md5"]
    private_groups = footprint["private_group_sha256"]
    if not private_groups.keys() <= before.keys():
        raise ValueError("MANDOR_ADAPTER_UNEXPECTED_PRIVATE_GROUP")
    for group, old in before.items():
        new = after[group]
        if old.keys() - new.keys():
            raise ValueError("MANDOR_ADAPTER_EXISTING_OBJECT_REMOVED:" + group)
        additions = {key: new[key] for key in new.keys() - old.keys()}
        if group_digest(additions) != private_groups.get(group, group_digest({})):
            raise ValueError("MANDOR_ADAPTER_PRIVATE_CATALOGUE_CHANGED:" + group)
        changed = {key for key in old if old[key] != new[key]}
        expected = set(ROUTINES) if group == "functions" else set()
        if changed != expected:
            raise ValueError("MANDOR_ADAPTER_EXISTING_CATALOGUE_CHANGED:" + group)
        for key in changed:
            if (old[key][1:] != new[key][1:]
                    or md5(old[key][0].encode()).hexdigest() != old_pins[key]
                    or md5(new[key][0].encode()).hexdigest() != new_pins[key]):
                raise ValueError("MANDOR_ADAPTER_ROUTINE_BODY_OR_METADATA_CHANGED:" + key)

