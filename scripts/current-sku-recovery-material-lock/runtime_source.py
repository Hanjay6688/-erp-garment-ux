"""Actual product.sources, with DB/network/non-Git commands forbidden."""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys
import transition as t


@contextmanager
def database_guard(attempts, controls):
    # libpq C calls need not emit Python socket audit events. Block the
    # actual psycopg entrypoints before retained reader imports can alias them.
    psycopg=importlib.import_module('psycopg')
    targets=[('psycopg.connect',psycopg),
             ('psycopg.Connection.connect',psycopg.Connection),
             ('psycopg.AsyncConnection.connect',psycopg.AsyncConnection)]
    saved=[];phase='self_control'
    try:
        for label,target in targets:
            original=vars(target)['connect']
            def blocked(*args,_label=label,**kwargs):
                if phase=='source_read':attempts.append(_label)
                else:controls.append(dict(api=_label,result='DENIED_BEFORE_LIBPQ'))
                raise RuntimeError('SKU_MATERIAL_SOURCE_DATABASE_FORBIDDEN:'+_label)
            saved.append((target,original))
            setattr(target,'connect',staticmethod(blocked) if isinstance(target,type) else blocked)
        for label,target in targets:
            try:getattr(target,'connect')()
            except RuntimeError as e:
                if str(e)!='SKU_MATERIAL_SOURCE_DATABASE_FORBIDDEN:'+label:raise
            else:raise RuntimeError('SKU_MATERIAL_SOURCE_DATABASE_CONTROL_DID_NOT_REFUSE:'+label)
        phase='source_read'
        yield
    finally:
        for target,original in reversed(saved):setattr(target,'connect',original)
        if any(vars(target)['connect'] is not original for target,original in saved):
            raise RuntimeError('SKU_MATERIAL_SOURCE_DATABASE_GUARDS_NOT_RESTORED')
        controls.append(dict(original_connect_descriptors_restored=True))


def run(output):
    t.admitted()
    attempts = [];controls=[]

    def deny(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'urllib.Request', 'http.client.connect'):
            attempts.append(event)
            raise RuntimeError('SKU_MATERIAL_SOURCE_NETWORK_FORBIDDEN:' + event)
        if event == 'subprocess.Popen':
            executable, argv = args[0], args[1]
            if Path(str(executable)).name != 'git' or not argv or Path(str(argv[0])).name != 'git':
                attempts.append('non_git_subprocess')
                raise RuntimeError('SKU_MATERIAL_SOURCE_NON_GIT_SUBPROCESS_FORBIDDEN')

    sys.addaudithook(deny)
    old_argv = sys.argv[:]
    try:
        # Retained readers parse argv and adjust sys.path during imports. Load
        # the actual current vendor before that adjustment, then the current
        # SKU module; never assign module ROOT or return a projected source.
        sys.argv = ['sku-material-current-source']
        with database_guard(attempts,controls):
            scripts = str(t.ROOT/'scripts')
            sys.path.insert(0,scripts)
            vendor = importlib.import_module('cp7_vendor_receivable.composition')
            if Path(vendor.__file__).resolve() != t.ROOT/'scripts/cp7_vendor_receivable/composition.py':
                raise ValueError('SKU_MATERIAL_SOURCE_CURRENT_VENDOR_REQUIRED')
            sys.path.insert(0,scripts)
            product = importlib.import_module('cp7_sku_pair_conversion.composition')
            if Path(product.__file__).resolve() != t.ROOT/'scripts/cp7_sku_pair_conversion/composition.py':
                raise ValueError('SKU_MATERIAL_SOURCE_CURRENT_SKU_REQUIRED')
            actual = product.sources()
        for name,digest in actual['files'].items():
            if sha256(t.read(t.ROOT,name)).hexdigest() != digest:
                raise ValueError('SKU_MATERIAL_SOURCE_ACTUAL_LEAF_CHANGED:'+name)
        if len(actual['files']) != 10 or len(product.CAPTURE_SIGNATURES) != 8 or len(product.FUNCTIONS) != 19 or len(product.TABLES) != 5:
            raise ValueError('SKU_MATERIAL_SOURCE_CURRENT_PROFILE_REQUIRED')
        raw=json.dumps(actual,sort_keys=True,separators=(',',':')).encode()
        report=dict(status='PASS',kind='ACTUAL_UNPROJECTED_CURRENT_PRODUCT_SOURCES',
                    sources_bytes=len(raw),sources_sha256=sha256(raw).hexdigest(),
                    sku_business_leaves=actual['files'],current_captures=8,
                    current_private_functions=19,private_tables=5,
                    forbidden_DB_network_attempts=attempts,DB_entrypoint_self_controls=controls,
                    projected_sources=False,ROOT_reassigned=False,
                    Native_financial=0,real_two_session=0,
                    production_go=False,independent_acceptance=False)
        output.write_text(json.dumps(report,indent=2)+'\n')
        return dict(status=report['status'],sources_bytes=len(raw),
                    sources_sha256=report['sources_sha256'],Native_financial=0)
    finally:
        sys.argv = old_argv


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.output),sort_keys=True))
