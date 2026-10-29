"""Select five existing callable objects; never execute the other 137 cases."""

ZONES = ("Asia/Jakarta", "UTC", "Asia/Tokyo", "Pacific/Kiritimati", "Etc/GMT+12")
IDS = tuple("DAY:ATTENDANCE:DIRECT:" + zone for zone in ZONES)
LABEL = "CP7_CURRENT_CP6_ATTENDANCE_DAY5"


def select_retained(found):
    found = tuple(found)
    names = tuple(name for name, _ in found)
    if len(found) != 142 or len(set(names)) != 142:
        raise ValueError("DAY5_REQUIRES_EXACT_142_UNIQUE_FACTORY_DECLARATIONS")
    selected = tuple((name, operation) for name, operation in found if name in IDS)
    if tuple(name for name, _ in selected) != IDS:
        raise ValueError("DAY5_ORIGINAL_ZONE_ORDER_OR_CASE_SET_CHANGED")
    return selected
