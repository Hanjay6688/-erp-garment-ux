"""Scope input-keyed parsing to exact unchanged, read-only source consumers.

The original accepted() code, file reads, selection and definition hash
assertions execute on every call. Only gzip/JSON decoding of identical input
bytes is reused, in memory for one scope. No admission or source result is
cached; changing bytes is a cache miss. Parsed values cannot be mutated.
Three SQL consumers also reuse regex parsing for identical pattern/text/flags.
They still read every input, enforce match counts and derive the original SQL.
"""
from contextlib import contextmanager
from functools import lru_cache
from hashlib import sha256
from importlib.abc import MetaPathFinder
from importlib.machinery import PathFinder, SourceFileLoader
from pathlib import Path
from types import CodeType, MappingProxyType, ModuleType
import gzip
import json
import re
import sys

PINS = {
    'cp7_supplier_credit_guard': (2705, '4fc6c79efd56b3ea922badb1456b6389e70f44b63ebe323519e4e72d1b1d9341'),
    'cp7_settlement_bundle': (5158, 'ef2817a5d9759802ccd8b19c4bf88fc92909389118b1d88d9870a56ac99a9ba9'),
}
REGEX_PINS = {
    'cp7_production_stage': ('cp7_production_stage/__init__.py', '_body', 11058,
                             '2c2e09873f7c427bf92aca5e409eb698ab2b65289866afabf80426257e34e572'),
    'cp7_bounded_analysis_stage.source': ('cp7_bounded_analysis_stage/source.py', 'block', 9267,
                             'b31a2dc0e4dc36b304617a757123250d32ef079433710321ede147809bed5715'),
    'cp7_product_analog_consumer_stage.render': ('cp7_product_analog_consumer_stage/render.py', 'block', 10022,
                             '26862dbf1edf23eee73e9056485f2dc82a6749b6f9d868bc3b0c4e884d3c363d'),
}
_active = []


def require(value, message):
    if not value:
        raise ValueError(message)


def immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({key: immutable(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(immutable(item) for item in value)
    return value


class Decoder:
    def __init__(self):
        self.compressed = self.expanded = self.json_bytes = self.parsed = None
        self.decompressions = self.decodes = self.gzip_hits = self.json_hits = 0
        self.regex_search = lru_cache(maxsize=256)(re.search)
        self.regex_findall = lru_cache(maxsize=256)(lambda pattern, text, flags=0: tuple(re.findall(pattern, text, flags)))

    def decompress(self, raw):
        require(type(raw) is bytes, 'SKU_CATALOGUE_EXACT_COMPRESSED_BYTES_REQUIRED')
        if raw == self.compressed:
            self.gzip_hits += 1
            return self.expanded
        # Failures never update the cache. The retained caller reads the file
        # again even on a hit; mtime, filename and previous acceptance are not keys.
        expanded = gzip.decompress(raw)
        self.compressed, self.expanded = raw, expanded
        self.decompressions += 1
        return expanded

    def loads(self, raw):
        require(type(raw) is bytes, 'SKU_CATALOGUE_EXACT_JSON_BYTES_REQUIRED')
        if raw == self.json_bytes:
            self.json_hits += 1
            return self.parsed
        parsed = immutable(json.loads(raw))
        self.json_bytes, self.parsed = raw, parsed
        self.decodes += 1
        return parsed

    def clear(self):
        self.compressed = self.expanded = self.json_bytes = self.parsed = None
        self.regex_search.cache_clear()
        self.regex_findall.cache_clear()

    def findall(self, pattern, text, flags=0):
        # re.findall returns a fresh mutable list; cache only its immutable
        # content and preserve that original API for each caller.
        return list(self.regex_findall(pattern, text, flags))


def bind(module, path, decoder, restorations):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'SKU_CATALOGUE_REGULAR_SOURCE_REQUIRED')
    raw = path.read_bytes()
    require((len(raw), sha256(raw).hexdigest()) == PINS[path.stem], 'SKU_CATALOGUE_EXACT_CONSUMER_BYTES_REQUIRED')
    require(Path(module.__file__).resolve() == path.resolve() and Path(module.ROOT).resolve() == path.parents[1].resolve(),
            'SKU_CATALOGUE_EXACT_CONSUMER_ORIGIN_REQUIRED')
    codes = [code for code in compile(raw, str(path.resolve()), 'exec', dont_inherit=True).co_consts
             if isinstance(code, CodeType) and code.co_name == 'accepted']
    require(len(codes) == 1 and module.accepted.__code__ == codes[0]
            and module.accepted.__globals__ is module.__dict__, 'SKU_CATALOGUE_UNCHANGED_ACCEPTED_FUNCTION_REQUIRED')
    require(module.gzip is gzip and module.json is json, 'SKU_CATALOGUE_UNCHANGED_DECODER_BINDINGS_REQUIRED')
    if path.stem == 'cp7_settlement_bundle':
        require(module.CATALOGUE == module.ROOT / 'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz',
                'SKU_CATALOGUE_EXACT_CATALOGUE_PATH_REQUIRED')
    restorations.extend(((module, 'gzip', module.gzip), (module, 'json', module.json)))
    for name, original, function in (('gzip', gzip, decoder.decompress), ('json', json, decoder.loads)):
        private = ModuleType('sku_private_' + name)
        private.__dict__.update(original.__dict__)
        setattr(private, 'decompress' if name == 'gzip' else 'loads', function)
        module.__dict__[name] = private


def bind_regex(module, path, decoder, restorations):
    relative, function, size, digest = REGEX_PINS[module.__name__]
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'SKU_SOURCE_REGEX_REGULAR_CONSUMER_REQUIRED')
    raw = path.read_bytes()
    require((len(raw), sha256(raw).hexdigest()) == (size, digest)
            and Path(module.__file__).resolve() == path.resolve(), 'SKU_SOURCE_REGEX_EXACT_CONSUMER_REQUIRED')
    original = getattr(module, function)
    codes = [code for code in compile(raw, str(path.resolve()), 'exec', dont_inherit=True).co_consts
             if isinstance(code, CodeType) and code.co_name == function]
    require(len(codes) == 1 and original.__code__ == codes[0] and original.__globals__ is module.__dict__,
            'SKU_SOURCE_REGEX_UNCHANGED_FUNCTION_REQUIRED')
    require(module.re is re, 'SKU_SOURCE_REGEX_UNCHANGED_BINDING_REQUIRED')
    restorations.append((module, 're', module.re))
    private = ModuleType('sku_private_source_re')
    private.__dict__.update(re.__dict__)
    private.search, private.findall = decoder.regex_search, decoder.findall
    module.re = private


@contextmanager
def scope(root):
    """Retain ordinary import resolution; refuse any different source origin."""
    root = Path(root).resolve()
    if _active:
        require(_active[-1][0] == root, 'SKU_CATALOGUE_NESTED_ORIGIN_CHANGED')
        yield _active[-1][1]
        return
    decoder, restorations = Decoder(), []
    paths = {name: root / 'scripts' / (name + '.py') for name in PINS}
    paths.update({name: root / 'scripts' / row[0] for name, row in REGEX_PINS.items()})

    def select(module, path):
        (bind if module.__name__ in PINS else bind_regex)(module, path, decoder, restorations)

    class Loader(SourceFileLoader):
        def exec_module(self, module):
            super().exec_module(module)
            select(module, paths[module.__name__])

    class Finder(MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname not in paths:
                return None
            spec = PathFinder.find_spec(fullname, path, target)
            require(spec is not None and Path(spec.origin).resolve() == paths[fullname],
                    'SKU_CATALOGUE_FROZEN_IMPORT_COLLISION:' + fullname)
            spec.loader = Loader(fullname, str(paths[fullname]))
            return spec

    finder = Finder()
    _active.append((root, decoder))
    try:
        for name, path in paths.items():
            if name in sys.modules:
                select(sys.modules[name], path)
        sys.meta_path.insert(0, finder)
        yield decoder
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        for module, name, original in reversed(restorations):
            setattr(module, name, original)
        _active.pop()
        decoder.clear()
