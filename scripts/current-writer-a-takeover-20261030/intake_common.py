"""Read-only Original/Git intake primitives; never import an ERP runtime."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import os
import re
import subprocess
import zipfile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exact(actual, expected, message):
    """JSON equality that also rejects bool/int and int/float substitutions."""
    if type(actual) is not type(expected):
        raise ValueError(message + ':TYPE')
    if type(expected) is dict:
        require(set(actual) == set(expected), message + ':KEYS')
        for key, value in expected.items():
            exact(actual[key], value, message + '/' + key)
    elif type(expected) is list:
        require(len(actual) == len(expected), message + ':LENGTH')
        for index, value in enumerate(expected):
            exact(actual[index], value, message + '/' + str(index))
    else:
        require(actual == expected, message + ':VALUE')


def fields(actual, expected, message):
    require(type(actual) is dict, message + ':OBJECT')
    for key, value in expected.items():
        require(key in actual, message + ':MISSING:' + key)
        exact(actual[key], value, message + '/' + key)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def json_bytes(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'ROOT_DUPLICATE_JSON_KEY')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('ROOT_NONFINITE_JSON_REFUSED')

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def safe_path(name):
    path = PurePosixPath(name)
    require(type(name) is str and name and not path.is_absolute()
            and '..' not in path.parts and str(path) == name,
            'ROOT_UNSAFE_RELATIVE_PATH')
    return name


class GitBytes:
    """All comparisons read immutable blobs, independent of worktree contents."""
    def __init__(self, root, head, tree):
        self.root = Path(root).resolve()
        self.head = head
        self.env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
        require(self.git('rev-parse', head + '^{commit}').decode().strip() == head,
                'ROOT_EXACT_PUBLIC_COMMIT_REQUIRED')
        require(self.git('rev-parse', head + '^{tree}').decode().strip() == tree,
                'ROOT_EXACT_PUBLIC_TREE_REQUIRED')
        self.tree = self.entries(head)
        self.cache = {}
        self.process = subprocess.Popen(
            ['/usr/bin/git', '-C', str(self.root), 'cat-file', '--batch'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=self.env)

    def git(self, *args):
        return subprocess.check_output(['/usr/bin/git', '-C', str(self.root), *args], env=self.env)

    def entries(self, ref):
        result = {}
        for row in self.git('ls-tree', '-rz', ref).split(b'\0'):
            if row:
                metadata, name = row.split(b'\t', 1)
                mode, kind, oid = metadata.decode().split()
                name = safe_path(name.decode())
                require(kind == 'blob' and mode in ('100644', '100755'),
                        'ROOT_REGULAR_GIT_SOURCE_REQUIRED:' + name)
                result[name] = dict(mode=mode, blob=oid)
        return result

    def read(self, name, ref=None):
        safe_path(name)
        ref = ref or self.head
        key = (ref, name)
        if key not in self.cache:
            self.process.stdin.write((ref + ':' + name + '\n').encode())
            self.process.stdin.flush()
            header = self.process.stdout.readline().decode().strip().split()
            require(len(header) == 3 and header[1] == 'blob', 'ROOT_EXACT_GIT_BLOB_REQUIRED:' + name)
            raw = self.process.stdout.read(int(header[2]))
            require(self.process.stdout.read(1) == b'\n', 'ROOT_GIT_STREAM_BOUNDARY')
            self.cache[key] = raw
        return self.cache[key]

    def verify_pin(self, name, expected):
        require(name in self.tree, 'ROOT_SOURCE_PATH_NOT_IN_PUBLIC_HEAD:' + name)
        raw = self.read(name)
        if type(expected) is str:
            require(re.fullmatch('[0-9a-f]{64}', expected) is not None,
                    'ROOT_SHA256_SOURCE_PIN_REQUIRED:' + name)
            require(sha256(raw).hexdigest() == expected, 'ROOT_SOURCE_DIGEST_CHANGED:' + name)
        else:
            require(type(expected) is dict and set(expected) in (
                {'bytes', 'sha256'}, {'bytes', 'sha256', 'mode'}), 'ROOT_SOURCE_PIN_SHAPE_CHANGED:' + name)
            exact(pin(raw), {key: expected[key] for key in ('bytes', 'sha256')},
                  'ROOT_SOURCE_PIN_CHANGED:' + name)
            if 'mode' in expected:
                exact(self.tree[name]['mode'], expected['mode'], 'ROOT_SOURCE_MODE_CHANGED:' + name)
        return raw

    def close(self):
        self.process.stdin.close()
        require(self.process.wait() == 0, 'ROOT_GIT_READER_FAILED')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def original_zip(path, expected, members):
    raw = Path(path).read_bytes()
    exact(pin(raw), expected, 'ROOT_EXACT_ORIGINAL_ZIP_REQUIRED')
    archive = zipfile.ZipFile(path)
    try:
        require(len(archive.infolist()) == members and len(set(archive.namelist())) == members,
                'ROOT_ORIGINAL_MEMBER_COUNT_OR_DUPLICATE_CHANGED')
        for name in archive.namelist():
            safe_path(name)
        require(archive.testzip() is None, 'ROOT_ORIGINAL_ZIP_CRC_FAILURE')
        return archive
    except BaseException:
        archive.close()
        raise


def originals(archive, pins):
    raw = {name: archive.read(name) for name in pins}
    for name, expected in pins.items():
        exact(pin(raw[name]), expected, 'ROOT_RAW_ORIGINAL_CHANGED:' + name)
    return raw, {name: json_bytes(value) for name, value in raw.items()}


def script_pins(*names):
    here = Path(__file__).resolve().parent
    return {name: pin((here / name).read_bytes()) for name in ('intake_common.py', *names)}


def save(value, output):
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(dict(status=value['status'], output=str(target))))
