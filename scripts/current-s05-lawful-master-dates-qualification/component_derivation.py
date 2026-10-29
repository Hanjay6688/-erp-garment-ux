"""One reversible assignment to the exact old component's business factory."""
from hashlib import sha256

OLD = "    business = importlib.import_module('cp7_accessory_standard_report.cases')\n"
NEW = "    business = __S05_BUSINESS_FACTORY__(importlib.import_module('cp7_accessory_standard_report.cases'))\n"
EXPECTED = 'c699ad2f5c7a7dbdad40ad7803ceaec066945c56a3ca125ad0d6aabe5574207a'


def derive(raw):
    if sha256(raw).hexdigest() != EXPECTED or raw.count(OLD.encode()) != 1:
        raise ValueError('S05_EXACT_UNCHANGED_COMPONENT_IMPORT_REQUIRED')
    result = raw.replace(OLD.encode(), NEW.encode(), 1)
    if result.replace(NEW.encode(), OLD.encode(), 1) != raw:
        raise ValueError('S05_COMPONENT_IMPORT_NOT_REVERSIBLE')
    return result, dict(original_sha256=EXPECTED, derived_sha256=sha256(result).hexdigest(),
                        counted_business_import_bindings=1,
                        unchanged_Native10_reader_intervals_witness_used_guard_and_full_restore=True)
