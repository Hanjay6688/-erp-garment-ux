"""Retained client/business bodies; only full composer, Native admission and label change."""
from hashlib import sha256
from pathlib import Path
import ast,json
IMMUTABLE=('cases.py', 'target_cases.py')
CHANGES=[('import cp7_current_versioned_performance_installation as quote_capability', 'import cp7_current_frozen_public_installation as quote_capability'), ("REPO/'scripts/current-versioned-performance-native-qualification/probe.py'", "REPO/'scripts/current-frozen-public-native-qualification/probe.py'"), ('CP7_CURRENT_VERSIONED_PERFORMANCE_TRANSPORT28', 'CP7_CURRENT_FROZEN_PUBLIC_TRANSPORT28')]
KIND='transport'
def check(repo,here,probe_text=None):
    old=repo/('scripts/current-versioned-performance-'+KIND+'-qualification');files={}
    for name in IMMUTABLE:
        raw=(here/name).read_bytes();assert raw==(old/name).read_bytes(),name;files[name]=sha256(raw).hexdigest()
    expected=(old/'probe.py').read_text()
    for a,b in CHANGES:assert expected.count(a)==1,a;expected=expected.replace(a,b)
    actual=(here/'probe.py').read_text()if probe_text is None else probe_text
    assert actual==expected,'RETAINED_BROWSER_TRANSPORT_PROBE_CHANGED'
    ast.parse(actual)
    return dict(unchanged_business_files=files,only_product_native_admission_label_changed=True,
        no_new_UI_or_default_adoption_claim=True,actual_Auth_HTTP_credit=False,production_go=False)
