"""Closed generated outputs only. Never source, Original or business authority."""
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import ast
import gzip
import importlib.util
import io
import json
import re
import struct

HERE = Path(__file__).resolve().parent
VALIDATORS = HERE / 'inherited-output-validation'
PROOF = 'cp6-proof/t3/'
IDS = (
    'S03_BROWSER_OWNER_EXPENSE_CORRECT_REVERSE_DESKTOP',
    'S03_BROWSER_OWNER_CARRY_ALLOCATE_CANCEL_MOBILE390',
    'S03_BROWSER_ACTUAL_STALE_AND_LOST_REPLY_SAME_UUID',
    'S03_BROWSER_CURRENT_AUTH_RIGHTS_AND_DELAYED_CONTEXT',
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:raise ValueError('S03_BROWSER4_GENERATED_DUPLICATE_KEY:' + key)
        result[key] = value
    return result


def document(raw):
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('S03_BROWSER4_GENERATED_NONFINITE:' + value)))


def file(root, name, maximum=256 * 1024 * 1024):
    root = Path(root).resolve();relative = PurePosixPath(name)
    if relative.is_absolute() or str(relative) != name or '..' in relative.parts or '\\' in name:
        raise ValueError('S03_BROWSER4_GENERATED_UNSAFE_PATH:' + name)
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():raise ValueError('S03_BROWSER4_GENERATED_SYMLINK:' + name)
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('S03_BROWSER4_GENERATED_REGULAR_BOUNDED_FILE_REQUIRED:' + name)
    return path.read_bytes()


def checked_pin(root, name, expected):
    raw = file(root, name)
    if len(raw) != expected['bytes'] or sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError('S03_BROWSER4_GENERATED_PRODUCER_CHANGED:' + name)
    return raw


def png(raw):
    if (len(raw) < 45 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[8:16] != b'\x00\x00\x00\rIHDR'
            or raw[-12:] != b'\x00\x00\x00\x00IEND\xaeB`\x82'):
        raise ValueError('S03_BROWSER4_GENERATED_PNG_SHAPE')
    width, height = struct.unpack('>II', raw[16:24])
    if not 1 <= width <= 4096 or not 1 <= height <= 65535:
        raise ValueError('S03_BROWSER4_GENERATED_PNG_DIMENSIONS')


def unpack(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:value = stream.read(256 * 1024 * 1024 + 1)
    if len(value) > 256 * 1024 * 1024:raise ValueError('S03_BROWSER4_GENERATED_GZIP_SIZE_BOUND')
    return document(value)


def evidence(root, here, name):
    if not name.startswith(PROOF):return False
    leaf = name[len(PROOF):]
    scenarios = r'(?:DESKTOP|MOBILE390|STALE|ACCESS)'
    snapshot = re.fullmatch(r'S03_B4_' + scenarios + r'_[A-F0-9]{32}_[0-9]{3}_([A-Z0-9_]+)_FULL_STATE\.json\.gz', leaf)
    if snapshot:
        source=(here / 'cases.mjs').read_text()
        labels = set(re.findall(r"\bstate\(['\"]([A-Z0-9_]+)['\"]\)", source))
        roles=set(re.findall(r"currentRole\(x,backupOwner,'(ADMIN|OWNER)'\)",source))
        if roles!={'ADMIN','OWNER'}:raise ValueError('S03_BROWSER4_EXACT_CURRENT_ROLE_PRODUCERS_REQUIRED')
        for prefix in ('AFTER_AUTHORIZED_ROLE_','AFTER_ACCESS_ROLE_REPLAY_'):
            if source.count("state('"+prefix+"'+role)")!=1:
                raise ValueError('S03_BROWSER4_EXACT_ROLE_SNAPSHOT_PRODUCER_REQUIRED')
            labels.update(prefix+role for role in roles)
        if snapshot[1] not in labels:raise ValueError('S03_BROWSER4_GENERATED_UNKNOWN_SNAPSHOT_LABEL')
        value = unpack(file(root, name))
        if (set(value) != {'all22', 'all_rows', 'data_and_all_sequences'}
                or not isinstance(value['all22'], dict) or len(value['all22']) != 22
                or not isinstance(value['all_rows'], dict) or not value['all_rows']
                or not all(isinstance(rows, list) for rows in value['all_rows'].values())
                or not isinstance(value['data_and_all_sequences'], dict)
                or not any(key.startswith('sequence:') for key in value['data_and_all_sequences'])):
            raise ValueError('S03_BROWSER4_GENERATED_FULL_CENSUS_SHAPE')
        return True
    shot = re.fullmatch(r'S03_B4_' + scenarios + r'_[a-f0-9]{32}_(.+)\.png', leaf)
    if shot:
        labels = {'FINAL', 'EXPENSE_REVIEW_AND_AUDIT', 'OWNED_P1_CLOSED_P2_OPEN', 'CURRENT_RIGHTS_REFUSED',
            'DELAYED_PERIOD_REVIEW_RETIRED', 'FRESH_OWNER'}
        if shot[1] != 'FIRST_FAILURE' and not any(shot[1] == label + suffix for label in labels for suffix in ('_PAGE', '_FOCUS')):
            raise ValueError('S03_BROWSER4_GENERATED_UNKNOWN_SCREENSHOT_LABEL')
        png(file(root, name, 32 * 1024 * 1024));return True
    if re.fullmatch(r'S03_B4_' + scenarios + r'_[a-f0-9]{32}_FIRST_FAILURE\.json', leaf):
        value = document(file(root, name, 32 * 1024 * 1024))
        if (set(value) != {'error', 'progress', 'calls', 'observed', 'fixture', 'pool_history'} or not isinstance(value['error'], str)
                or not isinstance(value['progress'], dict) or not isinstance(value['calls'], list)
                or not isinstance(value['observed'], list) or not isinstance(value['pool_history'], dict)
                or value['fixture'] is not None and not isinstance(value['fixture'], dict)):
            raise ValueError('S03_BROWSER4_GENERATED_FIRST_FAILURE_SHAPE')
        return True
    if re.fullmatch(r'S03_BROWSER4_HOST_ORIGINAL_cp6-auditor-browser-[A-Za-z0-9_-]+\.json\.gz', leaf):
        value = unpack(file(root, name))
        required = {'status','label','mode','ui_mode','phase','planned','cases','console_errors','real_auth',
            'product_responses_mocked','production_go','release_evidence','auth_cleanup_failures',
            'enteng_requests_answered_by_loopback','enteng_route_errors','blocked_requests'}
        optional = {'stage','error','duplicates','timed_out_case','missing','failed_stage','users_created',
            'disposable_entry_bootstrap','disposable_entry_text','loopback_api_origin'}
        if (not required <= set(value) or not set(value) <= required | optional
                or value['label'] != 'AUDITOR_SCENARIO' or value['mode'] != 'BROWSER'
                or value['phase'] != 'S03_CHOICE_MOUNTED4' or value['ui_mode'] != 'DISPOSABLE'
                or value['status'] not in ('INCOMPLETE','RUN_COMPLETE') or value['real_auth'] is not True
                or value['product_responses_mocked'] is not False or value['production_go'] is not False
                or value['release_evidence'] is not False or not isinstance(value['cases'], dict)
                or not set(value['cases']) <= set(IDS) or not isinstance(value['planned'], list)
                or not set(value['planned']) <= set(IDS)):
            raise ValueError('S03_BROWSER4_GENERATED_HOST_ORIGINAL_SHAPE')
        if 'loopback_api_origin' in value:
            if not isinstance(value['loopback_api_origin'], str):
                raise ValueError('S03_BROWSER4_GENERATED_HOST_LOOPBACK_ORIGIN')
            match = re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})', value['loopback_api_origin'])
            if match is None or int(match[1]) > 65535:
                raise ValueError('S03_BROWSER4_GENERATED_HOST_LOOPBACK_ORIGIN')
        return True
    return False


class Index(HTMLParser):
    def __init__(self):super().__init__();self.tokens=[];self.assets=[];self.module_depth=0;self.modules=0
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if len(values) != len(attrs):raise ValueError('S03_BROWSER4_GENERATED_DUPLICATE_HTML_ATTRIBUTE')
        if tag == 'script' and values.get('type') == 'module':
            if (set(values) not in ({'type','src'}, {'type','crossorigin','src'})
                    or values.get('crossorigin') not in (None,'')):
                raise ValueError('S03_BROWSER4_GENERATED_UNKNOWN_MODULE_ATTRIBUTE')
            src = values.get('src','')
            if src != '/src/main.tsx':self.assets.append(src)
            self.modules += 1;self.module_depth += 1;return
        if tag == 'link' and values.get('rel') in ('stylesheet','modulepreload'):
            if (set(values) not in ({'rel','href'}, {'rel','crossorigin','href'})
                    or values.get('crossorigin') not in (None,'')):
                raise ValueError('S03_BROWSER4_GENERATED_UNKNOWN_BUILD_LINK_ATTRIBUTE')
            self.assets.append(values.get('href',''));return
        self.tokens.append(('start',tag,tuple(sorted(attrs))))
    def handle_startendtag(self, tag, attrs):self.handle_starttag(tag,attrs)
    def handle_endtag(self, tag):
        if tag == 'script' and self.module_depth:self.module_depth -= 1;return
        self.tokens.append(('end',tag))
    def handle_data(self, data):
        if data.strip():self.tokens.append(('data',data.strip()))
    def handle_decl(self, value):self.tokens.append(('decl',value))


def build(root, here, names):
    names = {name for name in names if name.startswith('cp6-ui-build/')}
    if not names:return set()
    contract = document((here / 'BUILD_OUTPUT_CONTRACT.json').read_bytes())
    if (contract['contract'] != 'cp7.s03.normal-app-generated-build-output.v1'
            or contract['output_directory'] != 'cp6-ui-build' or contract['source_authority'] is not False):
        raise ValueError('S03_BROWSER4_GENERATED_BUILD_CONTRACT')
    for name, pin in contract['producer_files'].items():checked_pin(root,name,pin)
    package = document(file(root,'package.json'))
    if package['scripts']['build:cp6-disposable'] != contract['command']:
        raise ValueError('S03_BROWSER4_FIXED_NORMAL_APP_BUILD_COMMAND_CHANGED')
    index_name = 'cp6-ui-build/index.html'
    if index_name not in names:raise ValueError('S03_BROWSER4_GENERATED_BUILD_INDEX_REQUIRED')
    original, output = Index(), Index();original.feed(file(root,'index.html').decode());output.feed(file(root,index_name).decode())
    if (original.tokens != output.tokens or original.modules != 1 or output.modules != 1
            or not output.assets or len(output.assets) != len(set(output.assets))):
        raise ValueError('S03_BROWSER4_GENERATED_NORMAL_APP_INDEX_CHANGED')
    asset = re.compile(r'cp6-ui-build/assets/[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.(?:js|css|svg|png|jpg|jpeg|webp|woff2?|ttf)$')
    for reference in output.assets:
        if not reference.startswith('/assets/') or 'cp6-ui-build' + reference not in names or not asset.fullmatch('cp6-ui-build' + reference):
            raise ValueError('S03_BROWSER4_GENERATED_BUILD_REFERENCE_CHANGED')
    public = {name[len('public/'):]: pin for name,pin in contract['producer_files'].items() if name.startswith('public/')}
    generated = names - {index_name} - {'cp6-ui-build/' + name for name in public}
    reachable, pending = set(), ['cp6-ui-build' + name for name in output.assets]
    # Vite emits literal relative imports and a literal map of dynamic chunks.
    # A hash-looking extra script is not admitted merely by its filename.
    literal = re.compile(r'''["'`]((?:/assets/|assets/|\./)[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.(?:js|css|svg|png|jpg|jpeg|webp|woff2?|ttf))["'`]''')
    while pending:
        name = pending.pop()
        if name in reachable:continue
        if name not in generated:raise ValueError('S03_BROWSER4_GENERATED_BUILD_DEPENDENCY_MISSING:' + name)
        reachable.add(name)
        if name.endswith(('.js', '.css')):
            for reference in literal.findall(file(root, name, 32 * 1024 * 1024).decode()):
                dependency = 'cp6-ui-build/assets/' + reference.rsplit('/', 1)[-1]
                if dependency not in reachable:pending.append(dependency)
    if reachable != generated:
        raise ValueError('S03_BROWSER4_GENERATED_UNREFERENCED_BUILD_LEAF:' + repr(sorted(generated - reachable)))
    for name in names:
        raw = file(root,name,32*1024*1024)
        if name == index_name:continue
        relative = name[len('cp6-ui-build/'):]
        if relative in public:
            expected=public[relative]
            if len(raw)!=expected['bytes'] or sha256(raw).hexdigest()!=expected['sha256']:
                raise ValueError('S03_BROWSER4_GENERATED_PUBLIC_ASSET_CHANGED')
        elif not asset.fullmatch(name) or not raw:
            raise ValueError('S03_BROWSER4_GENERATED_UNKNOWN_BUILD_LEAF:' + name)
    return names


def admit(root, here, names):
    root,here,names=Path(root),Path(here),set(names)
    p0=load('s03_browser4_exact_P0_output_validator',here/'inherited-output-validation/generated_receipts.py')
    later=load('s03_browser4_exact_later_output_validator',here/'inherited-output-validation/generated_later.py')
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    accepted = load('s03_browser4_bound_immutable_original_input_scope', here / 'accepted_inputs.py')
    input_names, input_proof = accepted.present(root, here, cfg)
    selected_inputs = set(names) & input_names
    first,p0proof=p0.admit(root,here/'inherited-output-validation',names - selected_inputs)
    second,laterproof=later.admit(root,here/'inherited-output-validation',names-set(first)-selected_inputs)
    accepted=set(first)|set(second)|selected_inputs;built=build(root,here,names-accepted);accepted.update(built)
    own={name for name in names-accepted if evidence(root,here,name)};accepted.update(own)
    return accepted,dict(classification='BOUNDED_NON_SOURCE_OUTPUTS_NOT_ORIGINAL_OR_PASS_AUTHORITY',
        P0=p0proof,later=laterproof,normal_App_build_files=len(built),own_evidence_files=len(own),
        exact_accepted14_input_stage=input_proof,
        actual_Native_Auth_browser_credit=0,source_authority=False,Original_authority=False)
