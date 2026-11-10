"""Complete state with shared immutable strings; never project a census.

The large canonical JSON remains unchanged. The additional graph encoding
preserves original container identity: independent snapshots stay independent,
and intentional parent references remain shared. Complete canonical bytes must
equal the original before publication. Cold readers verify both file pins.
"""
from hashlib import file_digest, sha256
from io import TextIOWrapper
from itertools import islice
from pathlib import Path
import json
import math
import os
import tempfile

FORMAT = 'AFUI_COMPLETE_JSON_OBJECT_GRAPH_WITH_IMMUTABLE_STRINGS_V2'
CONTAINERS = (dict, list, tuple)
SCALARS = (type(None), bool, int, float)
STREAM_PREFIX = '{"strings":['


def require(value, reason):
    if not value:
        raise ValueError(reason)


class GraphIndex:
    """Hold references to the existing graph, rather than a second graph of edges."""
    def __init__(self, root):
        self.root = root
        self.strings, self.indices = [], {}
        self.nodes, self.identities = [], {}
        active = set()

        def string(text):
            if text not in self.indices:
                self.indices[text] = len(self.strings)
                self.strings.append(text)

        def visit(item):
            kind = type(item)
            if kind in CONTAINERS:
                identity = id(item)
                require(identity not in active, 'AFUI_LOSSLESS_STATE_CIRCULAR_CONTAINER')
                if identity in self.identities:
                    return
                active.add(identity)
                try:
                    if kind is dict:
                        for key, child in item.items():
                            require(type(key) is str, 'AFUI_LOSSLESS_STATE_EXACT_JSON_STRING_KEYS')
                            string(key)
                            visit(child)
                    else:
                        for child in item:
                            visit(child)
                    self.identities[identity] = len(self.nodes)
                    self.nodes.append(item)
                finally:
                    active.remove(identity)
            elif kind in SCALARS:
                require(kind is not float or math.isfinite(item), 'AFUI_LOSSLESS_STATE_FINITE_JSON_NUMBER')
            else:
                string(item if kind is str else str(item))

        visit(root)

    def reference(self, item):
        kind = type(item)
        if kind in CONTAINERS:
            return [2, self.identities[id(item)]]
        if kind in SCALARS:
            return [0, item]
        return [1, self.indices[item if kind is str else str(item)]]

    def payload(self, node):
        if type(node) is dict:
            return 3, ([self.indices[key], self.reference(value)] for key, value in node.items())
        return 2, (self.reference(value) for value in node)


def encode(value):
    graph = GraphIndex(value)
    nodes = [[tag, list(payload)] for tag, payload in map(graph.payload, graph.nodes)]
    return dict(format=FORMAT, strings=graph.strings, nodes=nodes, root=graph.reference(value))


def decode(document):
    require(document['format'] == FORMAT and type(document['strings']) is list,
            'AFUI_LOSSLESS_STATE_EXACT_ENCODING')
    strings = document['strings']
    require(all(type(v) is str for v in strings) and len(strings) == len(set(strings)),
            'AFUI_LOSSLESS_STATE_UNIQUE_IMMUTABLE_STRINGS')

    def string(index):
        require(type(index) is int and 0 <= index < len(strings), 'AFUI_LOSSLESS_STATE_STRING_REFERENCE')
        return strings[index]

    values = []

    def value(node):
        require(type(node) is list and len(node) == 2 and type(node[0]) is int,
                'AFUI_LOSSLESS_STATE_TYPED_COMPLETE_NODE')
        tag, payload = node
        if tag == 0:
            require(type(payload) in (type(None), bool, int, float)
                    and (type(payload) is not float or math.isfinite(payload)), 'AFUI_LOSSLESS_STATE_JSON_SCALAR')
            return payload
        if tag == 1:
            return string(payload)
        require(tag == 2 and type(payload) is int and 0 <= payload < len(values),
                'AFUI_LOSSLESS_STATE_PRIOR_CONTAINER_REFERENCE')
        return values[payload]

    require(type(document['nodes']) is list, 'AFUI_LOSSLESS_STATE_ALL_CONTAINER_NODES')
    for node in document['nodes']:
        require(type(node) is list and len(node) == 2 and type(node[0]) is int
                and type(node[1]) is list, 'AFUI_LOSSLESS_STATE_TYPED_CONTAINER_NODE')
        tag, payload = node
        if tag == 2:
            result = [value(v) for v in payload]
        else:
            require(tag == 3, 'AFUI_LOSSLESS_STATE_KNOWN_NODE_TYPE')
            result = {}
            for pair in payload:
                require(type(pair) is list and len(pair) == 2, 'AFUI_LOSSLESS_STATE_COMPLETE_DICTIONARY_PAIR')
                key = string(pair[0]);require(key not in result, 'AFUI_LOSSLESS_STATE_DUPLICATE_KEY')
                result[key] = value(pair[1])
        values.append(result)
    return value(document['root'])


def canonical_pin(value):
    from . import complete_original_io
    digest, count = sha256(), 0
    for chunk in complete_original_io.encoded(value):
        count += len(chunk);digest.update(chunk)
    return dict(bytes=count, sha256=digest.hexdigest())


def graph_pin(value):
    """Fingerprint every value and container alias without expanding a DAG.

    Ordinals describe traversal, never process addresses. Equal independent
    snapshots remain distinct; dictionary insertion order is not significant.
    This is an immutability guard, not a substitute for canonical byte proof.
    """
    digest, identities, active = sha256(), {}, set()
    references = 0

    def emit(tag, payload=''):
        raw = payload.encode('utf-8')
        digest.update(tag.encode('ascii') + str(len(raw)).encode('ascii') + b':' + raw)

    def visit(item):
        nonlocal references
        kind = type(item)
        if kind in (dict, list, tuple):
            identity = id(item)
            require(identity not in active, 'AFUI_LOSSLESS_STATE_CIRCULAR_CONTAINER')
            if identity in identities:
                references += 1
                emit('R', str(identities[identity]));return
            identities[identity] = len(identities)
            active.add(identity)
            try:
                emit('D' if kind is dict else 'L' if kind is list else 'T', str(len(item)))
                if kind is dict:
                    require(all(type(k) is str for k in item), 'AFUI_LOSSLESS_STATE_EXACT_JSON_STRING_KEYS')
                    for key in sorted(item):
                        emit('K', key);visit(item[key])
                else:
                    for child in item:visit(child)
                emit('E')
            finally:
                active.remove(identity)
        else:
            require(kind is not float or math.isfinite(item), 'AFUI_LOSSLESS_STATE_FINITE_JSON_NUMBER')
            emit('S', json.dumps(item, sort_keys=True, default=str))

    visit(value)
    return dict(format='AFUI_COMPLETE_STATE_IDENTITY_GRAPH_SHA256_V1', sha256=digest.hexdigest(),
                unique_containers=len(identities), repeated_container_references=references)


def cache_chunks(graph, reference):
    """Write the V2 JSON fields with the string table before dependent nodes."""
    encode_item = json.JSONEncoder(separators=(',', ':'), allow_nan=False).encode

    def items(values, block):
        values = iter(values)
        first = True
        while batch := list(islice(values, block)):
            if not first:
                yield ','
            yield encode_item(batch)[1:-1]
            first = False

    yield STREAM_PREFIX
    yield from items(graph.strings, 1)
    yield '],"nodes":['
    for index, node in enumerate(graph.nodes):
        if index:
            yield ','
        tag, payload = graph.payload(node)
        yield f'[{tag},['
        yield from items(payload, 1024)
        yield ']]'
    yield '],"root":' + encode_item(graph.reference(graph.root))
    yield ',"format":' + encode_item(FORMAT)
    yield ',"source_original":' + encode_item(reference) + '}\n'


def original_binding(actual, expected):
    require(type(actual) is dict and all(type(actual.get(k)) is type(v) and actual[k] == v
            for k, v in expected.items()), 'AFUI_LOSSLESS_STATE_EXACT_ORIGINAL_BINDING')


def match_value(decoded, hot):
    """Independently check decoded types, values, aliases and canonical scalars."""
    kind = type(hot)
    if kind in CONTAINERS:
        require(decoded is hot, 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_CONTAINER_IDENTITY')
        return
    if kind in SCALARS or kind is str:
        same = type(decoded) is kind and (decoded.hex() == hot.hex() if kind is float else decoded == hot)
    else:
        same = type(decoded) is str and decoded == str(hot) and json.dumps(decoded) == json.dumps(hot, sort_keys=True, default=str)
    require(same, 'AFUI_LOSSLESS_STATE_EVERY_CANONICAL_ORIGINAL_BYTE_REQUIRED')


def read_stream_cache(stream, reference, expected=None):
    reader = CompleteStream(stream)

    def field(name):
        require(reader.scalar() == name, 'AFUI_LOSSLESS_STATE_STREAM_FIELD:' + name)
        reader.take(':')

    reader.take('{')
    field('strings')
    strings = expected.strings if expected is not None else []
    seen = set()
    string_count = 0
    for text in reader.array(reader.json_item):
        require(type(text) is str, 'AFUI_LOSSLESS_STATE_UNIQUE_IMMUTABLE_STRINGS')
        if expected is None:
            require(text not in seen, 'AFUI_LOSSLESS_STATE_UNIQUE_IMMUTABLE_STRINGS')
            seen.add(text)
            strings.append(text)
        else:
            require(string_count < len(strings) and text == strings[string_count], 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_STRING')
        string_count += 1
    require(string_count == len(strings), 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_STRING_COUNT')
    seen.clear()
    reader.take(',')
    field('nodes')
    values = expected.nodes if expected is not None else []
    index = 0

    def string(number):
        require(type(number) is int and 0 <= number < len(strings), 'AFUI_LOSSLESS_STATE_STRING_REFERENCE')
        return strings[number]

    def value(token):
        require(type(token) is list and len(token) == 2 and type(token[0]) is int, 'AFUI_LOSSLESS_STATE_TYPED_COMPLETE_NODE')
        tag, data = token
        if tag == 0:
            require(type(data) in SCALARS and (type(data) is not float or math.isfinite(data)), 'AFUI_LOSSLESS_STATE_JSON_SCALAR')
            return data
        if tag == 1:
            return string(data)
        require(tag == 2 and type(data) is int and 0 <= data < index, 'AFUI_LOSSLESS_STATE_PRIOR_CONTAINER_REFERENCE')
        return values[data]

    def pair(row):
        require(type(row) is list and len(row) == 2, 'AFUI_LOSSLESS_STATE_COMPLETE_DICTIONARY_PAIR')
        return string(row[0]), value(row[1])

    def node():
        nonlocal index
        reader.take('[')
        tag = reader.json_item()
        require(type(tag) is int and tag in (2, 3), 'AFUI_LOSSLESS_STATE_KNOWN_NODE_TYPE')
        reader.take(',')
        payload = reader.array(reader.json_item)
        if expected is not None:
            require(index < len(values), 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_NODE_COUNT')
            hot = values[index]
            require((tag == 3) is (type(hot) is dict), 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_NODE_TYPE')
            if tag == 3:
                for row, (key, item) in zip(payload, hot.items(), strict=True):
                    read_key, decoded = pair(row)
                    require(read_key == key, 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_KEY')
                    match_value(decoded, item)
            else:
                for token, item in zip(payload, hot, strict=True):
                    match_value(value(token), item)
        elif tag == 3:
            result = {}
            for row in payload:
                key, item = pair(row)
                require(key not in result, 'AFUI_LOSSLESS_STATE_DUPLICATE_KEY')
                result[key] = item
            values.append(result)
        else:
            values.append([value(token) for token in payload])
        reader.take(']')
        index += 1

    for _ in reader.array(node):
        pass
    require(index == len(values), 'AFUI_LOSSLESS_STATE_CACHE_CHANGED_NODE_COUNT')
    reader.take(',')
    field('root')
    root = value(reader.json_item())
    reader.take(',')
    field('format')
    require(reader.scalar() == FORMAT, 'AFUI_LOSSLESS_STATE_EXACT_ENCODING')
    reader.take(',')
    field('source_original')
    original_binding(reader.value(), reference)
    reader.take('}')
    require(reader.peek() == '' and reader.ended, 'AFUI_COMPLETE_JSON_TRAILING_BYTES')
    if expected is not None:
        match_value(root, expected.root)
    return root


def save(target, value, original_reference):
    from . import complete_original_io
    target = complete_original_io.regular(Path(target))
    graph = GraphIndex(value)
    with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent,
            prefix='.' + target.name + '.', suffix='.partial', delete=False) as stream:
        partial = Path(stream.name)
        for chunk in cache_chunks(graph, original_reference):
            stream.write(chunk.encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())
    with partial.open('r', encoding='utf-8') as stream:
        read_stream_cache(stream, original_reference, graph)
    # The streamed read matched every decoded edge against the hot graph,
    # including canonical scalar bytes. Re-hash that exact graph without a clone.
    require(canonical_pin(value) == {k: original_reference[k] for k in ('bytes', 'sha256')},
            'AFUI_LOSSLESS_STATE_EVERY_CANONICAL_ORIGINAL_BYTE_REQUIRED')
    pin = complete_original_io.pin(partial)
    complete_original_io.finish(partial, target, 'AFUI_LOSSLESS_STATE_FIRST_CACHE_CONFLICT')
    return dict(name=target.name, **pin)


def read(target, expected, original, expected_original):
    from . import complete_original_io
    original = Path(original)
    original_pin = complete_original_io.pin(original)
    require(original_pin['sha256'] == expected_original,
            'AFUI_LOSSLESS_STATE_COMPLETE_ORIGINAL_CHANGED')
    reference = dict(name=original.name, **original_pin)
    target = complete_original_io.regular(Path(target))
    with target.open('rb') as stream:
        require(file_digest(stream, 'sha256').hexdigest() == expected, 'AFUI_LOSSLESS_STATE_CACHE_CHANGED')
        stream.seek(0)
        with TextIOWrapper(stream, encoding='utf-8') as text:
            prefix = text.read(len(STREAM_PREFIX))
            text.seek(0)
            if prefix == STREAM_PREFIX:
                return read_stream_cache(text, reference)
            document = json.load(text)
    original_binding(document['source_original'], reference)
    return decode(document)


class CompleteStream:
    """Read every original JSON token while interning immutable strings only."""
    def __init__(self, stream, block=1024 * 1024, deduplicate_equal_containers=False):
        self.stream, self.block, self.buffer, self.position, self.ended = stream, block, '', 0, False
        self.strings = {}
        # Optional read-only reconstruction of an old expanded JSON Original.
        # Production caches are encoded from the actual hot object graph, not
        # from this reconstruction; their original identity is preserved.
        self.deduplicate_equal_containers = deduplicate_equal_containers
        self.containers, self.container_ids = {}, {}
        self.decoder = json.JSONDecoder(parse_constant=lambda _: require(False, 'AFUI_COMPLETE_JSON_NONFINITE'))

    def more(self):
        self.buffer = self.buffer[self.position:];self.position = 0
        value = self.stream.read(self.block);self.ended = not value;self.buffer += value

    def peek(self):
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position] in ' \t\r\n':
                self.position += 1
            if self.position < len(self.buffer) or self.ended:
                return self.buffer[self.position:self.position + 1]
            self.more()

    def take(self, token):
        require(self.peek() == token, 'AFUI_COMPLETE_JSON_DELIMITER:' + token);self.position += 1

    def json_item(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
                if not self.ended and (end == len(self.buffer) or self.buffer[end] not in ' \t\r\n,:]}'):
                    require(len(self.buffer) - self.position < 128 * 1024 * 1024, 'AFUI_COMPLETE_JSON_SCALAR_MEMORY_BOUND')
                    self.more();continue
                require(end == len(self.buffer) or self.buffer[end] in ' \t\r\n,:]}', 'AFUI_COMPLETE_JSON_SCALAR_DELIMITER')
                self.position = end
                return value
            except json.JSONDecodeError:
                if self.ended:
                    raise
                require(len(self.buffer) - self.position < 128 * 1024 * 1024, 'AFUI_COMPLETE_JSON_SCALAR_MEMORY_BOUND')
                self.more()

    def scalar(self):
        value = self.json_item()
        require(type(value) is str or type(value) in SCALARS
                and (type(value) is not float or math.isfinite(value)), 'AFUI_COMPLETE_JSON_SCALAR')
        return self.strings.setdefault(value, value) if type(value) is str else value

    def array(self, item):
        self.take('[')
        if self.peek() != ']':
            yield item()
            while self.peek() == ',':
                self.take(',')
                yield item()
        self.take(']')

    def value(self):
        token = self.peek()
        if token == '{':
            self.take('{');result = {}
            if self.peek() != '}':
                while True:
                    key = self.scalar();require(type(key) is str and key not in result, 'AFUI_COMPLETE_JSON_UNIQUE_STRING_KEY')
                    self.take(':');result[key] = self.value()
                    if self.peek() == '}':
                        break
                    self.take(',')
            self.take('}');return self.container(result)
        if token == '[':
            self.take('[');result = []
            if self.peek() != ']':
                while True:
                    result.append(self.value())
                    if self.peek() == ']':
                        break
                    self.take(',')
            self.take(']');return self.container(result)
        return self.scalar()

    def container(self, result):
        if not self.deduplicate_equal_containers:
            return result
        def token(value):
            if type(value) in (dict,list):return ('container',self.container_ids[id(value)])
            return (type(value).__name__,value.hex()if type(value)is float else value)
        signature = ('dict',tuple((k,token(v))for k,v in result.items())) if type(result)is dict else ('list',tuple(token(v)for v in result))
        if signature in self.containers:
            return self.containers[signature]
        self.containers[signature]=result;self.container_ids[id(result)]=len(self.container_ids)
        return result


def read_complete_original(target, *, deduplicate_equal_containers=False):
    with Path(target).open('r', encoding='utf-8') as stream:
        reader = CompleteStream(stream,deduplicate_equal_containers=deduplicate_equal_containers);value = reader.value()
        require(reader.peek() == '' and reader.ended, 'AFUI_COMPLETE_JSON_TRAILING_BYTES')
        return value
