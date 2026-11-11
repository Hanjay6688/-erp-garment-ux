"""Compare equivalent encoding costs on the retained complete Mandor census."""
from hashlib import sha256
from pathlib import Path
from time import perf_counter
import gzip
import importlib.util
import json
import resource
import sys
import zipfile

p = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('exact_owning_package', p)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
archive = Path(sys.argv[2])
with zipfile.ZipFile(archive) as z:
    [member] = [name for name in z.namelist() if name.endswith('01_BEFORE_SELECTION_FULL_CENSUS.json.gz')]
    original = gzip.decompress(z.read(member))
value = json.loads(original)
start = perf_counter()
encoded_tree = ['cp7.complete-postgres-parent-state.v1', package.state_value(value)]
converted = perf_counter()
encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'), allow_nan=False)
digest = sha256()
for chunk in encoder.iterencode(encoded_tree):
    digest.update(chunk.encode())
streamed = perf_counter()
encoded = encoder.encode(encoded_tree).encode()
assert sha256(encoded).hexdigest() == digest.hexdigest()
batch = perf_counter()
assert digest.hexdigest() == package.state_digest(value)
end = perf_counter()
print(json.dumps(dict(source_file_sha256=sha256(p.read_bytes()).hexdigest(),archive_member=member,
    original_json_bytes=len(original), original_json_sha256=sha256(original).hexdigest(),
    typed_json_bytes=len(encoded), same_digest=digest.hexdigest(), typed_conversion_seconds=round(converted-start,3),
    streamed_encoding_seconds=round(streamed-converted,3), batch_encoding_seconds=round(batch-streamed,3),
    exact_state_digest_seconds=round(end-batch,3), process_max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    actual_SKU_case_credit=0, source='historical complete Mandor census, not the killed SKU process state'),indent=2))
