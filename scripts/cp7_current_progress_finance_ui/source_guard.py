"""Verify unchanged B provenance and the exact locally compiled source graph."""
from pathlib import Path
from hashlib import sha256
import json, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def originals(head, files):
    queries = ''.join(head + ':' + f['path'] + '\n' for f in files).encode()
    output = subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '--batch'], input=queries)
    cursor = 0
    for f in files:
        end = output.index(b'\n', cursor)
        _, kind, size = output[cursor:end].split()
        assert kind == b'blob', f['path']
        start = end + 1
        cursor = start + int(size)
        assert output[cursor:cursor+1] == b'\n'
        yield output[start:cursor]
        cursor += 1
    assert cursor == len(output)

def verify():
    declaration = json.loads((HERE / 'B_SOURCE.json').read_bytes())
    files = declaration['files']
    assert len(files) == len({f['vendored_path'] for f in files}) == 90
    for f, original in zip(files, originals(declaration['B_source_head'], files), strict=True):
        raw = (HERE / f['vendored_path']).read_bytes()
        assert len(raw) == f['bytes'] and sha256(raw).hexdigest() == f['sha256'], f['path']
        assert raw == original, f['path']
    build = json.loads((HERE / 'LOCAL_BUILD.json').read_bytes())
    graph = json.loads((HERE / 'BUILD_SOURCE.json').read_bytes())
    assert graph['served_in_browser'] is False
    assert build['actual_runtime_executed'] is build['actual_Auth_HTTP_credit'] is build['default_application_adopted'] is False
    assert build['prepared_choice_gate'] and build['actual_AuthProvider'] and build['actual_AuthGate']
    assert len(graph['files']) == len(set(build['source_paths'])) == 79
    assert [x['path'] for x in graph['files']] == build['source_paths']
    for f in graph['files']:
        path = ROOT / f['path']
        assert path.is_relative_to(ROOT) and '..' not in Path(f['path']).parts
        raw = path.read_bytes()
        assert len(raw) == f['bytes'] and sha256(raw).hexdigest() == f['sha256'], f['path']
    tests = json.loads((HERE / 'LOCAL_TESTS.json').read_bytes())
    assert tests['success'] and tests['numPassedTests'] == tests['numTotalTests'] == 179
    assert tests['numFailedTests'] == tests['numPendingTests'] == 0
    assert len(tests['testResults']) == 16 and all(t['status'] == 'passed' for t in tests['testResults'])
    return dict(B_exact_files=len(files), compiled_source_files=len(graph['files']),
                local_tests=179, local_test_files=16, runtime_credit=False, production_go=False)

if __name__ == '__main__':
    print(json.dumps(verify()))
