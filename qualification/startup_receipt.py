"""Print only the allowed startup result fields from a disposable test job."""

import json
from pathlib import Path
import re
import shutil
import sys


CLASSIFICATIONS = {
    'disk-space': r'no space left on device|disk quota exceeded',
    'registry-limit': r'toomanyrequests|rate limit|data limit exceeded|http status.*429',
    'image-unavailable': r'manifest unknown|manifest.*not found|no matching manifest',
    'registry-access': r'pull access denied|unauthorized:|authentication required',
    'network-timeout': r'net/http:|i/o timeout|tls handshake timeout|context deadline exceeded|unexpected eof',
    'port-in-use': r'address already in use|port is already allocated',
    'container-health': r'unhealthy|is not healthy|failed to become ready|failed to start docker container',
}
REGISTRIES = {'default_ghcr', 'public.ecr.aws'}


def report(directory, workspace):
    print('ERP_TEST_DISK_AVAILABLE_MIB', shutil.disk_usage(workspace).free // (1024 * 1024), flush=True)
    path = directory / 'STARTUP_ATTEMPTS.json'
    if not path.is_file():
        print('ERP_TEST_STARTUP_RECEIPT_UNAVAILABLE', flush=True)
        return
    attempts = json.loads(path.read_bytes())['attempts']
    for number, attempt in enumerate(attempts, 1):
        if attempt['number'] != number or attempt['registry'] not in REGISTRIES:
            raise ValueError('ERP_TEST_STARTUP_EXACT_ATTEMPT_REQUIRED')
        status = attempt['status']
        if status not in ('RUNNING', 'PASS', 'FAILED'):
            raise ValueError('ERP_TEST_STARTUP_EXACT_STATUS_REQUIRED')
        logfile = directory / f'attempt-{number}-start.log'
        detail = logfile.read_text(errors='replace') if logfile.is_file() else ''
        reasons = [name for name, pattern in CLASSIFICATIONS.items() if re.search(pattern, detail, re.I)]
        if status == 'FAILED' and not reasons:
            reasons = ['unclassified']
        print(json.dumps(dict(event='ERP_TEST_STARTUP', attempt=number, status=status,
                              registry=attempt['registry'], failure_categories=reasons)), flush=True)


if __name__ == '__main__':
    report(Path(sys.argv[1]), Path(sys.argv[2]))
