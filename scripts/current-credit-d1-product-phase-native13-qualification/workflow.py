"""Counted routing-only derivation; all old package/setup/restore steps exact."""
from hashlib import sha256

OLD_PATH = '.github/workflows/cp7-credit-de-native.yml'
NEW_PATH = '.github/workflows/cp7-credit-d1-product-phase-native13.yml'
OLD = 'scripts/current-credit-de-native-qualification'
NEW = 'scripts/current-credit-d1-product-phase-native13-qualification'
CONTROL_STEP = ("    - name: Check joined quote phase closure and private adapter before database\n"
                "      working-directory: auditor\n"
                "      run: |\n"
                "        python -B -m unittest discover -s " + NEW + " -p 'test_*.py'\n"
                "        python -B -m unittest discover -s scripts/current-credit-d1-product-cap-native-augmentation -p 'test_*.py'\n"
                "        python -B scripts/current-credit-d1-product-cap-native-augmentation/import_check.py\n"
                "        python -B " + NEW + "/import_check.py\n")
REPLACEMENTS = (
    ('name: CP7 A credit correction D1 Native13\n', 'name: CP7 A D1 product cap and materialize phase Native13\n'),
    ('astra-a/credit-d1-cap-native13-20261029', 'astra-a/credit-d1-product-phase-native13-20261030'),
    ('    - ' + OLD_PATH + '\n', '    - ' + NEW_PATH + '\n'),
    ('    - ' + OLD + '/**\n', '    - ' + NEW + '/**\n    - scripts/current-credit-d1-product-cap-native-augmentation/**\n'),
    ('group: cp7-credit-de-native-${{ github.run_id }}', 'group: cp7-credit-d1-product-phase-native-${{ github.run_id }}'),
    ('    name: D1 Native13 and complete restore\n', '    name: D1 joined Native13 and complete restore\n'),
    ('      run: python -B ' + OLD + '/check.py\n', '      run: python -B ' + NEW + '/check.py --runtime\n'),
    ("      run: python '../auditor/" + OLD + "/probe.py'\n", "      run: python '../auditor/" + NEW + "/probe.py'\n"),
    ('name: cp7-a-credit-de-native13-${{ github.run_attempt }}', 'name: cp7-a-credit-d1-product-phase-native13-${{ github.run_attempt }}'),
)


def derive(raw):
    text = raw.decode()
    counts = []
    for before, after in REPLACEMENTS:
        count = text.count(before)
        expected = 2 if before.startswith('astra-a/') else 1
        if count != expected:
            raise ValueError('D1_WORKFLOW_EXACT_ROUTING_ANCHOR_REQUIRED:' + before)
        text = text.replace(before, after)
        counts.append(count)
    anchor = '    - name: Admit exact vendor parent and declared D1 child before database\n'
    if text.count(anchor) != 1:
        raise ValueError('D1_WORKFLOW_SINGLE_PRE_DATABASE_ADMISSION_REQUIRED')
    text = text.replace(anchor, CONTROL_STEP + anchor, 1)
    return text.encode(), dict(original_path=OLD_PATH, original_sha256=sha256(raw).hexdigest(),
        derived_path=NEW_PATH, derived_sha256=sha256(text.encode()).hexdigest(),
        routing_anchor_counts=counts, added_source_control_steps=1,
        old_steps_other_than_declared_routing_byte_exact=True,
        all_five_package_gates_and_cleanup_unchanged=True)
