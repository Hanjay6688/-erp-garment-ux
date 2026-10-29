"""One private import binding; all retained Native assertions remain exact."""
from hashlib import sha256

BEFORE = 'from cp7_credit_correction_de import cases as business, composition as product'
AFTER = ('from cp7_credit_correction_de import cases as __D1_RETAINED_BUSINESS__, composition as product\n'
         'business = __D1_BUSINESS_FACTORY__(__D1_RETAINED_BUSINESS__)')


def native_runner(raw):
    source = raw.decode()
    if source.count(BEFORE) != 1:
        raise ValueError('D1_ONE_EXACT_NATIVE_BUSINESS_BINDING_REQUIRED')
    derived = source.replace(BEFORE, AFTER, 1)
    return derived, dict(original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(derived.encode()).hexdigest(), counted_changes=1,
        private_module_globals=True, original_file_preserved=True,
        all_original_function_bodies_and_assertions_byte_exact=True)
