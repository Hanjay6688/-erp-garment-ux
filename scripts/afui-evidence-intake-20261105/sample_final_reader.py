"""Measure the final reader on a success-sized envelope of exact retained bytes."""
from hashlib import file_digest
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from zipfile import ZipFile
import json
import resource
import shutil
import sys

from retain import api, copy_stream, metadata, require
from verify_terminal import strict

REPO = 'Hanjay6688/-erp-garment-ux'
SOURCE_RUN = 42178605233
SOURCE_HEAD = '8e5a0511c0f5a68ea5fcc1cf2649d36703d119ac'
ARTIFACT = 13500698792
ARCHIVE = dict(bytes=2502519333, sha256='8967a4e3bfa0004c3f993d0d5ed2d6dcd57f8e1c251c122321840553dbbb3e14')
PINS = {"CP7_AFUI_GOOD_NONPAYABLE_FULL15.json":{"bytes":965851862,"sha256":"835dd2cc39e7b4ac72369d5eecd2e5a9c64dc258bd96b29864eae4ec838ac506"},"CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json":{"bytes":733090126,"sha256":"39fe3ee25a913df6a18607265132c957e6301664ad0661592baf156e95d0b8a5"},"AFUI_BROWSER_SETTINGS_STATE.json":{"bytes":7995578905,"sha256":"2eb2784e5eef62cf86ee1ab5935cab3acf609b21fcc9493e1638727005c97178"},"AFUI_BROWSER_SETTINGS_STATE_CACHE.json":{"bytes":1107841090,"sha256":"899de04951f2c7f9424c5706a2a168156765b6a4807a31edf9ea3bdb3c24880c"},"AFUI_BROWSER_NATIVE_PREREQUISITE.json":{"bytes":14977905,"sha256":"81a9a1d228b36ac08c8571f0c1c33f380c59c2466853ac047b22d31618b5ee09"}}
MAIN = 'CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'
NATIVE = 'CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json'
STATE = 'AFUI_BROWSER_SETTINGS_STATE.json'
CACHE = 'AFUI_BROWSER_SETTINGS_STATE_CACHE.json'
FIXTURE = 'AFUI_BROWSER_NATIVE_PREREQUISITE.json'


def sample(phase, started):
    value = dict(phase=phase, elapsed_seconds=round(monotonic()-started, 3),
                 peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    print('AFUI_FINAL_READER_SAMPLE ' + json.dumps(value, separators=(',', ':')), flush=True)


def materialize(archive, name, destination):
    with archive.open(name) as source, destination.open('xb') as target:
        received = copy_stream(source, target, PINS[name]['bytes'])
    require(received == PINS[name], 'AFUI_EXACT_RESOURCE_SAMPLE_MEMBER_CHANGED:' + name)


def main():
    candidate = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(candidate/'scripts'))
    from cp7_accessory_nonpayable import lossless_state
    started = monotonic()
    with TemporaryDirectory(prefix='afui-final-reader-') as directory:
        work = Path(directory)
        route = f'/repos/{REPO}/actions/artifacts/{ARTIFACT}'
        meta = metadata(route, work/'metadata.json')
        require(meta['id'] == ARTIFACT and meta['workflow_run']['id'] == SOURCE_RUN
                and meta['workflow_run']['head_sha'] == SOURCE_HEAD and meta['expired'] is False
                and meta['digest'] == 'sha256:' + ARCHIVE['sha256']
                and meta['size_in_bytes'] == ARCHIVE['bytes'], 'AFUI_EXACT_RESOURCE_SAMPLE_ARTIFACT_CHANGED')
        needed = ARCHIVE['bytes'] + sum(value['bytes'] for value in PINS.values())
        require(shutil.disk_usage(work).free > needed + 1024**3, 'AFUI_FINAL_READER_SAMPLE_DISK_BUDGET_REQUIRED')
        with api(route+'/zip') as inp, (work/'archive.zip').open('xb') as out:
            require(copy_stream(inp,out,ARCHIVE['bytes']) == ARCHIVE, 'AFUI_EXACT_RESOURCE_SAMPLE_ZIP_CHANGED')
        sample('verified_download',started)
        with ZipFile(work/'archive.zip') as z:
            for name in PINS:
                materialize(z,name,work/name)
        sample('verified_all_sample_members',started)
        total_KiB = int(next(row.split()[1] for row in Path('/proc/meminfo').read_text().splitlines()
                             if row.startswith('MemTotal:')))
        cap = total_KiB * 1024 - 2*1024**3
        require(cap > 8*1024**3, 'AFUI_SAME_RUNNER_CLASS_MEMORY_REQUIRED')
        resource.setrlimit(resource.RLIMIT_AS, (cap,resource.getrlimit(resource.RLIMIT_AS)[1]))
        # The failure main lacks a committed browser packet and an embedded
        # Native9 result. Hold an additional independent Native9 parse and
        # three copies of the actual fixture to model the successful envelope.
        terminal_main = strict((work/MAIN).read_bytes())
        require(terminal_main['qualification_commit'] == SOURCE_HEAD and terminal_main['status'] != 'PASS',
                'AFUI_SAMPLE_MUST_REMAIN_ACTUAL_FAILED_SOURCE')
        native = strict((work/NATIVE).read_bytes())
        embedded = strict((work/NATIVE).read_bytes())
        fixtures = [strict((work/FIXTURE).read_bytes()) for _ in range(3)]
        require(len(native['cases']) == len(embedded['cases']) == 9, 'AFUI_SAMPLE_EXPECTS_NINE_REAL_CASE_RECORDS')
        sample('both_native_copies_and_main_retained',started)
        state = lossless_state.read(work/CACHE,PINS[CACHE]['sha256'],work/STATE,PINS[STATE]['sha256'])
        sample('full_lossless_state_decoded',started)
        require(len(state['after'])==22 and fixtures[0]['observer_catalogue']['after']==state['after'],
                'AFUI_FULL22_OBSERVER_INPUT_CHANGED')
        require(lossless_state.canonical_pin(state)==PINS[STATE], 'AFUI_FINAL_READER_RAW_REENCODING_CHANGED')
        sample('full_exact_raw_reencoded',started)
        print('AFUI_FINAL_READER_RESOURCE_PASS ' + json.dumps(dict(source_run=SOURCE_RUN,artifact=ARTIFACT,
            same_source_bytes=True,modeled_success_envelope=True,all22_equal=True,
            exact_raw_bytes=PINS[STATE]['bytes'],elapsed_seconds=round(monotonic()-started,3),
            peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,process_address_space_cap_bytes=cap,
            actual_ERP_cases=0,production_go=False),separators=(',', ':')),flush=True)


if __name__ == '__main__':
    main()
