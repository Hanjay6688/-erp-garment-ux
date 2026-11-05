"""Complete state with shared immutable strings; never project a census.

The large canonical JSON remains unchanged. The additional graph encoding
preserves original container identity: independent snapshots stay independent,
and intentional parent references remain shared. Complete canonical bytes must
equal the original before publication. Cold readers verify both file pins.
"""
from hashlib import sha256
from pathlib import Path
import json
import math

FORMAT = 'AFUI_COMPLETE_JSON_OBJECT_GRAPH_WITH_IMMUTABLE_STRINGS_V2'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def encode(value):
    strings, indices, active, nodes, identities = [], {}, set(), [], {}

    def string(text):
        if text not in indices:
            indices[text] = len(strings);strings.append(text)
        return indices[text]

    def visit(item):
        kind = type(item)
        if kind is str:
            return [1, string(item)]
        if kind in (dict, list, tuple):
            require(id(item) not in active, 'AFUI_LOSSLESS_STATE_CIRCULAR_CONTAINER')
            if id(item) in identities:
                return [2, identities[id(item)]]
            active.add(id(item))
            try:
                if kind is dict:
                    require(all(type(k) is str for k in item), 'AFUI_LOSSLESS_STATE_EXACT_JSON_STRING_KEYS')
                    node = [3, [[string(k), visit(v)] for k, v in item.items()]]
                else:
                    node = [2, [visit(v) for v in item]]
                index = len(nodes);nodes.append(node);identities[id(item)] = index
                return [2, index]
            finally:
                active.remove(id(item))
        if kind in (type(None), bool, int, float):
            require(kind is not float or math.isfinite(item), 'AFUI_LOSSLESS_STATE_FINITE_JSON_NUMBER')
            return [0, item]
        # Exactly the existing canonical JSONEncoder(default=str) behavior.
        return [1, string(str(item))]

    root = visit(value)
    return dict(format=FORMAT, strings=strings, nodes=nodes, root=root)


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


def save(target, value, original_reference):
    from . import complete_original_io
    document = encode(value)
    document['source_original'] = original_reference
    require(canonical_pin(decode(document)) == {k: original_reference[k] for k in ('bytes', 'sha256')},
            'AFUI_LOSSLESS_STATE_EVERY_CANONICAL_ORIGINAL_BYTE_REQUIRED')
    return complete_original_io.save_sorted(Path(target), document, 'AFUI_LOSSLESS_STATE_FIRST_CACHE_CONFLICT')


def read(target, expected, original, expected_original):
    from . import complete_original_io
    require(complete_original_io.pin(Path(original))['sha256'] == expected_original,
            'AFUI_LOSSLESS_STATE_COMPLETE_ORIGINAL_CHANGED')
    document = complete_original_io.read_verified_json(Path(target), expected, 'AFUI_LOSSLESS_STATE_CACHE_CHANGED')
    reference = document['source_original']
    require(reference['name'] == Path(original).name and reference['sha256'] == expected_original
            and reference['bytes'] == Path(original).stat().st_size, 'AFUI_LOSSLESS_STATE_EXACT_ORIGINAL_BINDING')
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

    def scalar(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
                if not self.ended and (end == len(self.buffer) or self.buffer[end] not in ' \t\r\n,:]}'):
                    require(len(self.buffer) - self.position < 128 * 1024 * 1024, 'AFUI_COMPLETE_JSON_SCALAR_MEMORY_BOUND')
                    self.more();continue
                require(end == len(self.buffer) or self.buffer[end] in ' \t\r\n,:]}', 'AFUI_COMPLETE_JSON_SCALAR_DELIMITER')
                self.position = end
                require(type(value) in (str, type(None), bool, int, float)
                        and (type(value) is not float or math.isfinite(value)), 'AFUI_COMPLETE_JSON_SCALAR')
                if type(value) is str:
                    value = self.strings.setdefault(value, value)
                return value
            except json.JSONDecodeError:
                if self.ended:
                    raise
                require(len(self.buffer) - self.position < 128 * 1024 * 1024, 'AFUI_COMPLETE_JSON_SCALAR_MEMORY_BOUND')
                self.more()

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
