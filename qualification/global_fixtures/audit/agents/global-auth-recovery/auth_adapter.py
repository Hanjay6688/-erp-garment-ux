"""Same-application-database Auth for the owning Global attempt."""
from base64 import urlsafe_b64decode
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit
from uuid import UUID, uuid4
import json
import re
import secrets
import time

APP = 'cp6_rollback'
ISSUER_DB = 'postgres'
AUTH_URL = 'http://127.0.0.1:54321/auth/v1'
MARKER = 'cp7_global_attempt_subject'
AUTH_CORE = ('users', 'identities', 'sessions', 'refresh_tokens')
AUDIT = 'audit_log_entries'
FULL_RESTORE = ('baseline_full22_all_rows_all_sequences_equal', 'baseline_full25_portable_catalogue_equal',
                'cp6_restored', 'baseline_advisors_equal')
IDENTITY_SQL = """select current_database(),oid::bigint,(pg_control_system()).system_identifier::text
                  from pg_database where datname=current_database()"""
MAP_SQL = """select id::text,auth_user_id::text from erp.app_users
             where id=any(%s::uuid[]) or auth_user_id=any(%s::uuid[])"""
SUBJECT_SQL = """select id::text,email,raw_app_meta_data->>%s from auth.users
                 where lower(email)=%s or raw_app_meta_data->>%s=%s or id::text=%s"""


class AuthRefusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AuthRefusal('GLOBAL_AUTH_' + reason)


def error_code(error):
    if type(error) is AuthRefusal and re.fullmatch(r'GLOBAL_AUTH_[A-Z0-9_]+', str(error)):
        return str(error)
    return 'GLOBAL_AUTH_RUNTIME_IO_REFUSED'


def canonical_uuid(value):
    try:
        return str(UUID(value)) if isinstance(value, str) else None
    except ValueError:
        return None


def db_url(value, database):
    try:
        uri = urlsplit(value)
        good = (uri.scheme == 'postgresql' and uri.hostname in ('127.0.0.1', 'localhost')
                and uri.port == 54322 and uri.username == 'supabase_admin'
                and bool(uri.password) and uri.path == '/' + database and not uri.query and not uri.fragment)
    except (ValueError, TypeError):
        good = False
    require(good, 'FIXED_LOCAL_DATABASE_REQUIRED')
    return uri


def database_identity(cur, database):
    identity = cur.execute(IDENTITY_SQL).fetchone()
    require(identity and identity[0] == database and type(identity[1]) is int and identity[1] > 0
            and isinstance(identity[2], str) and identity[2].isdigit(), 'EXACT_DATABASE_IDENTITY_REQUIRED')
    return identity


def identifier(name):
    require(isinstance(name, str) and re.fullmatch(r'[a-z_][a-z_0-9]*', name), 'AUTH_CATALOGUE_IDENTIFIER_REFUSED')
    return '"' + name + '"'


def issuer_census(cur):
    tables, sequences = {}, {}
    relations = cur.execute("""select c.relname::text,c.relkind::text from pg_class c join pg_namespace n
                               on n.oid=c.relnamespace where n.nspname='auth'
                               and c.relkind in ('r','p','S') order by c.relname""").fetchall()
    for name, kind in relations:
        qualified = 'auth.' + identifier(name)
        if kind == 'S':
            value, called = cur.execute('select last_value,is_called from ' + qualified).fetchone()
            sequences[name] = dict(last_value=value, is_called=called)
        elif name != AUDIT:
            count, digest = cur.execute(
                """select count(*),encode(sha256(convert_to(coalesce(string_agg(raw,chr(10)
                   order by raw collate "C"),''),'UTF8')),'hex') from
                   (select to_jsonb(t)::text raw from """ + qualified + ' t) q').fetchone()
            tables[name] = dict(count=count, sha256=digest)
    require(set(AUTH_CORE) <= tables.keys() and (AUDIT, 'r') in relations, 'EXACT_MANAGED_AUTH_SCHEMA_REQUIRED')
    audit = dict(cur.execute("""select id::text,encode(sha256(convert_to(to_jsonb(a)::text,'UTF8')),'hex')
                                from auth.audit_log_entries a""").fetchall())
    return dict(tables=tables, sequences=sequences, audit=audit)


@dataclass
class Subject:
    nonce: str
    app_id: str
    role: str
    label: str
    uid: str | None = None
    uid_recorded: bool = False
    absent_create_acknowledged: bool = False

    @property
    def email(self):
        return 'cp7-global-auth-' + self.nonce + '@example.invalid'


class Attempt:
    """Only the owning runner may start this single-use transport."""

    def __init__(self, *, connect, transport, retain, attempt, allowed_actors, allowed_rpcs, head=None):
        self.connect = connect
        self.transport = transport
        self.retain = retain
        self.attempt = attempt
        self.head = head
        self.allowed_actors = frozenset(allowed_actors)
        self.allowed_rpcs = frozenset(allowed_rpcs)
        self.subjects = {}
        self.phase = 'NEW'
        self.browser = None
        self.receipts = []
        self.baseline = None
        self.app = None
        self.issuer = None
        self._keys = None
        self._secrets = set()
        self._actors = []
        self.verified_actors = 0
        self.application_rpc_responses = 0
        self.rest_verified = False

    def _record(self, key, data):
        result = self.retain('GLOBAL_AUTH_' + self.attempt + '_' + key + '.json',
                             dict(contract='cp7.global.owning-auth.v1', attempt=self.attempt, **data))
        self.receipts.append(result)
        return result

    @contextmanager
    def _cursor(self, url, database, *, identity=None, write=False):
        try:
            with self.connect(url, connect_timeout=5) as conn, conn.cursor() as cur:
                if not write:
                    cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                    cur.execute("SET LOCAL TIME ZONE 'UTC'")
                observed = database_identity(cur, database)
                if identity is not None:
                    require(observed == identity, 'DATABASE_OID_OR_CLUSTER_CHANGED')
                yield cur, observed
                if write:
                    conn.commit()
                else:
                    conn.rollback()
        except AuthRefusal:
            raise
        except Exception:
            raise AuthRefusal('GLOBAL_AUTH_DATABASE_OPERATION_REFUSED') from None

    def begin(self, conn, cur, url, issuer_url, verify, report):
        require(self.phase == 'NEW', 'ONE_OWNING_ATTEMPT_REQUIRED')
        require(self.head is None or report.get('qualification_commit') == self.head,
                'EXACT_OWNING_QUALIFICATION_COMMIT_REQUIRED')
        app_url, issuer = db_url(url, APP), db_url(issuer_url, ISSUER_DB)
        require(app_url.netloc == issuer.netloc, 'SAME_DISPOSABLE_CLUSTER_REQUIRED')
        require(cur.connection is conn and not conn.autocommit and conn.info.dbname == APP
                and conn.info.host in ('localhost', '127.0.0.1') and conn.info.port == 54322
                and conn.info.transaction_status.name == 'IDLE', 'IDLE_OWNING_DISPOSABLE_OBSERVER_REQUIRED')
        self.url, self.issuer_url = url, issuer_url
        try:
            app = database_identity(cur, APP)
            proof = verify(cur)
            require(type(proof) is dict and proof.get('full25_verified') is True
                    and database_identity(cur, APP) == app, 'LIVE_GLOBAL_INSTALL_VERIFICATION_REQUIRED')
            self.app = app
        finally:
            conn.rollback()
        with self._cursor(self.issuer_url, ISSUER_DB) as (watch, issuer):
            require(issuer[2] == self.app[2] and issuer[1] != self.app[1], 'SEPARATE_ISSUER_SAME_CLUSTER_REQUIRED')
            self.issuer = issuer
            self.baseline = issuer_census(watch)
        self._record('BASELINE', dict(qualification_commit=self.head, application_oid=self.app[1], issuer_oid=self.issuer[1],
                                     cluster_system_id=self.app[2], managed_auth=self.baseline))
        self.phase = 'ACTIVE'
        report['global_auth_application'] = dict(database=APP, oid=self.app[1], issuer_database=ISSUER_DB,
                                                issuer_database_oid=self.issuer[1], issuer=AUTH_URL)

    def _ready(self):
        require(self.phase == 'ACTIVE', 'ACTIVE_VERIFIED_ATTEMPT_REQUIRED')
        if self._keys is None:
            self._keys = self.transport.start()
            self._secrets.update(self._keys)
        with self._cursor(self.issuer_url, ISSUER_DB, identity=self.issuer) as (cur, _):
            evidence = self.transport.verify_backend(cur, self.app)
        if not self.rest_verified:
            self._record('REST_BOUND', evidence)
            self.rest_verified = True
        return self._keys

    def _subject(self, subject):
        with self._cursor(self.issuer_url, ISSUER_DB, identity=self.issuer) as (cur, _):
            rows = cur.execute(SUBJECT_SQL, (MARKER, subject.email, MARKER, subject.nonce, subject.uid)).fetchall()
        if not rows:
            return None
        require(len(rows) == 1, 'SYNTHETIC_IDENTITY_NOT_UNIQUE')
        uid, email, marker = rows[0]
        require(canonical_uuid(uid) == uid and uid is not None and email == subject.email
                and marker == subject.nonce and (subject.uid is None or subject.uid == uid),
                'SYNTHETIC_IDENTITY_MISMATCH')
        return uid

    def _capture_uid(self, subject, *, attempts=1):
        for index in range(attempts):
            observed = self._subject(subject)
            if observed is not None:
                subject.uid = observed
                if not subject.uid_recorded:
                    self._record(subject.nonce + '_UID', dict(subject_nonce=subject.nonce, auth_uid=observed))
                    subject.uid_recorded = True
                return observed
            if index + 1 < attempts:
                time.sleep(0.25)
        return None

    def _bind_app_user(self, subject):
        with self._cursor(self.url, APP, identity=self.app, write=True) as (cur, _):
            require(not cur.execute(MAP_SQL, ([subject.app_id], [subject.uid])).fetchall(), 'APPLICATION_MAPPING_ALREADY_PRESENT')
            roles = cur.execute('select id::text from erp.app_roles where role_code=%s and is_active',
                                (subject.role,)).fetchall()
            require(len(roles) == 1, 'EXACT_ACTIVE_APPLICATION_ROLE_REQUIRED')
            mapped = cur.execute("""insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
                select %s,%s,%s,role_code,id,true from erp.app_roles where role_code=%s and is_active
                returning id::text,auth_user_id::text,role,role_id::text,is_active""",
                (subject.app_id, subject.uid, 'Global qualification ' + subject.nonce, subject.role)).fetchall()
            require(mapped == [(subject.app_id, subject.uid, subject.role, roles[0][0], True)],
                    'EXACT_APPLICATION_MAPPING_REQUIRED')
        return roles[0][0]

    def _request(self, operation, *args, **kwargs):
        try:
            result = operation(*args, **kwargs)
        except Exception:
            raise AuthRefusal('GLOBAL_AUTH_LOCAL_WIRE_OUTCOME_UNKNOWN') from None
        require(type(result) is dict and type(result.get('status')) is int, 'TYPED_WIRE_RESPONSE_REQUIRED')
        return result

    def _claims(self, token, uid):
        segments = []
        try:
            segments = token.split('.')
            encoded = segments[1]
            claims = json.loads(urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
        except (ValueError, TypeError, IndexError, AttributeError):
            claims = {}
        require(type(claims) is dict and len(segments) == 3 and claims.get('iss') == AUTH_URL
                and claims.get('sub') == uid and claims.get('aud') == 'authenticated'
                and claims.get('role') == 'authenticated' and canonical_uuid(claims.get('session_id'))
                and type(claims.get('exp')) is int and claims['exp'] > time.time(), 'EXACT_REAL_GOTRUE_CLAIMS_REQUIRED')
        return claims['session_id']

    def login(self, role, label):
        require((role, label) in self.allowed_actors and (role, label) not in self.subjects,
                'ONE_EXACT_REVIEWED_SYNTHETIC_ACTOR_REQUIRED')
        anon, _ = self._ready()
        subject = Subject(uuid4().hex, str(uuid4()), role, label)
        require(self._subject(subject) is None, 'SYNTHETIC_INTENT_ALREADY_PRESENT')
        self._record(subject.nonce + '_INTENT', dict(subject_nonce=subject.nonce, app_user_id=subject.app_id,
                                                   role=role, label=label, issuer_oid=self.issuer[1],
                                                   application_oid=self.app[1]))
        self.subjects[(role, label)] = subject
        password = 'Gl!' + secrets.token_hex(24)
        self._secrets.update((password, subject.email))
        created = None
        try:
            created = self._request(self.transport.auth, 'admin/users',
                                    dict(email=subject.email, password=password, email_confirm=True,
                                         app_metadata={MARKER: subject.nonce}), admin=True)
        finally:
            # Read the exact intent on the issuer even after a dropped/malformed response.
            observed = self._capture_uid(subject, attempts=4)
        body = created.get('body') if created else None
        if observed is None and created and created['status'] in (400, 401, 403, 422):
            subject.absent_create_acknowledged = True
            self._record(subject.nonce + '_CREATE_REFUSAL', dict(subject_nonce=subject.nonce, http_status=created['status']))
        require(created and created['status'] in (200, 201) and type(body) is dict and observed
                and body.get('id') == observed, 'CREATE_ACK_AND_EXACT_ISSUER_UID_REQUIRED')
        role_id = self._bind_app_user(subject)
        reply = self._request(self.transport.auth, 'token?grant_type=password',
                              dict(email=subject.email, password=password))
        data = reply.get('body')
        require(reply['status'] == 200 and type(data) is dict and isinstance(data.get('access_token'), str),
                'REAL_PASSWORD_LOGIN_REQUIRED')
        token = data['access_token']
        self._secrets.add(token)
        if isinstance(data.get('refresh_token'), str):
            self._secrets.add(data['refresh_token'])
        session_id = self._claims(token, subject.uid)
        headers = dict(apikey=anon, Authorization='Bearer ' + token)
        trusted = self._request(self.transport.call, AUTH_URL + '/user', None, headers, method='GET')
        user = trusted.get('body')
        require(trusted['status'] == 200 and type(user) is dict and user.get('id') == subject.uid
                and user.get('email') == subject.email and type(user.get('app_metadata')) is dict
                and user['app_metadata'].get(MARKER) == subject.nonce, 'GOTRUE_USER_VERIFICATION_REQUIRED')
        with self._cursor(self.issuer_url, ISSUER_DB, identity=self.issuer) as (cur, _):
            require(cur.execute('select user_id::text from auth.sessions where id=%s', (session_id,)).fetchall()
                    == [(subject.uid,)], 'EXACT_ISSUER_SESSION_REQUIRED')
            require(not cur.execute(MAP_SQL, ([subject.app_id], [subject.uid])).fetchall(), 'PRIMARY_APPLICATION_MAPPING_REFUSED')
        profile = self._request(self.transport.call, self.transport.url +
                                '/v_erp_my_profile?select=id,auth_user_id,role,is_active', None, headers, method='GET')
        require(profile == dict(status=200, body=[dict(id=subject.app_id, auth_user_id=subject.uid, role=role, is_active=True)]),
                'REAL_REST_APPLICATION_MAPPING_REQUIRED')
        self._record(subject.nonce + '_MAPPING', dict(subject_nonce=subject.nonce, auth_uid=subject.uid,
                                                     app_user_id=subject.app_id, role=role, role_id=role_id,
                                                     verified_claims=['iss', 'sub', 'aud', 'role', 'session_id', 'exp'],
                                                     verified_issuer=AUTH_URL, verified_role='authenticated',
                                                     real_REST_mapping_verified=True))
        self.verified_actors += 1
        actor = self.transport.client(self, token, subject.uid, role)
        self._actors.append(actor)
        return actor

    def _rpc(self, token, name, args):
        require(isinstance(name, str) and name in self.allowed_rpcs and type(args) is dict,
                'EXACT_REVIEWED_RPC_REQUIRED')
        self._ready()
        result = self._request(self.transport.rpc, token, name, args)
        raw = json.dumps(result, default=str)
        require(not any(secret in raw for secret in self._secrets)
                and not re.search(r'eyJ[\w-]+\.[\w-]+\.[\w-]+', raw), 'SECRET_IN_RPC_RESPONSE_REFUSED')
        self.application_rpc_responses += 1
        return result

    def anon_rpc(self, name, args=None):
        return self._rpc(None, name, {} if args is None else args)

    def service_rpc(self, name, args=None):
        _, service = self._ready()
        return self._rpc(service, name, {} if args is None else args)

    def own_browser(self, browser):
        require(self.phase == 'ACTIVE' and self.browser is None, 'ONE_ATTEMPT_OWNED_BROWSER_REQUIRED')
        require(browser.attempt == self.attempt and callable(browser.reap), 'FOREIGN_BROWSER_OWNER_REFUSED')
        self.browser = browser

    def before_restore(self, report):
        if self.phase == 'NEW':
            return
        require(self.phase == 'ACTIVE', 'ACTIVE_TRANSPORT_TEARDOWN_REQUIRED')
        self.phase = 'STOPPING'
        teardown = report.setdefault('global_auth_before_restore', {})
        errors = []
        if self.browser is not None:
            try:
                result = self.browser.reap()
                teardown['browser'] = {key: result.get(key) is True for key in
                                       ('process_group_empty', 'process_tree_empty')}
                require(result.get('process_group_empty') is True and result.get('process_tree_empty') is True,
                        'OWNED_BROWSER_NOT_REAPED')
            except Exception as error:
                errors.append(error_code(error))
        try:
            teardown['REST'] = self.transport.reap()
            if self.issuer is not None:
                with self._cursor(self.issuer_url, ISSUER_DB, identity=self.issuer) as (cur, _):
                    self.transport.verify_no_backend(cur)
        except Exception as error:
            errors.append(error_code(error))
        self._keys = None
        self._secrets.clear()
        for actor in self._actors:
            actor.close()
        self._actors.clear()
        teardown['errors'] = errors
        if errors:
            self.transport.forget_keys()
        require(not errors, 'OWNED_TRANSPORT_REAP_INCOMPLETE')
        teardown['verified'] = True
        self.phase = 'RESTORE_READY'

    def _restored_application(self, report):
        require(self.phase == 'RESTORE_READY' and all(report.get(key) is True for key in FULL_RESTORE)
                and (report.get('baseline_restore') or {}).get('only_pg_cron_errors') is True,
                'EXACT_FULL_APPLICATION_RESTORE_REQUIRED')
        for subject in self.subjects.values():
            self._capture_uid(subject, attempts=4 if subject.uid is None else 1)
        apps = [subject.app_id for subject in self.subjects.values()]
        uids = [subject.uid for subject in self.subjects.values() if subject.uid is not None]
        with self._cursor(self.url, APP) as (cur, restored):
            require(restored[2] == self.app[2] and restored[1] not in (self.app[1], self.issuer[1]),
                    'FRESH_RESTORED_APPLICATION_OID_REQUIRED')
            require(not cur.execute(MAP_SQL, (apps, uids)).fetchall(), 'RESTORED_APPLICATION_MAPPINGS_REMAIN')
        return restored, apps, uids

    def _delete(self, subject):
        uid = self._subject(subject)
        if uid is None:
            require(subject.absent_create_acknowledged or subject.uid is not None, 'UNRESOLVED_SYNTHETIC_CREATE_INTENT')
            return dict(auth_uid=subject.uid, already_absent=True)
        require(subject.uid == uid and subject.uid_recorded, 'RECORDED_ISSUER_UID_REQUIRED_FOR_DELETE')
        statuses = []
        for _ in range(2):
            try:
                reply = self._request(self.transport.auth, 'admin/users/' + uid, None, admin=True, method='DELETE')
                statuses.append(reply['status'])
            except AuthRefusal:
                # A connection failure can occur after a committed deletion.
                statuses.append(None)
            if self._capture_uid(subject, attempts=1) is None:
                return dict(auth_uid=uid, http_statuses=statuses, absence_observed=True)
        raise AuthRefusal('GLOBAL_AUTH_EXACT_ISSUER_SUBJECT_DELETE_INCOMPLETE')

    def _complete_cleanup(self, report):
        require(self.app is not None and self.baseline is not None, 'AUTH_ATTEMPT_BASELINE_REQUIRED')
        restored, app_ids, uids = self._restored_application(report)
        summary = dict(status='INCOMPLETE', application_database=APP, installed_application_oid=self.app[1],
                       restored_application_oid=restored[1], issuer_database_oid=self.issuer[1],
                       restored_application_mappings_absent=True, deletions={}, failures={},
                       verified_actors=self.verified_actors, application_rpc_responses=self.application_rpc_responses)
        report['global_auth_cleanup'] = summary
        self._record('RESTORED_APPLICATION', dict(application_oid=restored[1], absent_app_user_ids=app_ids,
                                                  absent_auth_uids=uids, original_full_restore_verified=True))
        for subject in self.subjects.values():
            try:
                summary['deletions'][subject.nonce] = self._delete(subject)
            except Exception as error:
                summary['failures'][subject.nonce] = error_code(error)
        with self._cursor(self.issuer_url, ISSUER_DB, identity=self.issuer) as (cur, _):
            issuer_maps = cur.execute(MAP_SQL, (app_ids, uids)).fetchall()
            after = issuer_census(cur)
            residual = {}
            for table in AUTH_CORE:
                column = 'id' if table == 'users' else 'user_id'
                residual[table] = cur.execute('select count(*) from auth.' + identifier(table) +
                                              ' where ' + column + '::text=any(%s::text[])', (uids,)).fetchone()[0]
        before = self.baseline
        changed = sorted(name for name in before['tables'].keys() | after['tables'].keys()
                         if before['tables'].get(name) != after['tables'].get(name))
        summary.update(managed_auth_tables=dict(before=before['tables'], after=after['tables'], changed=changed),
                       residual_subject_rows=residual, primary_application_mappings_absent=not issuer_maps,
                       issuer_audit=dict(before_count=len(before['audit']), after_count=len(after['audit']),
                                         added_ids=sorted(after['audit'].keys() - before['audit'].keys()),
                                         previous_rows_unchanged=all(after['audit'].get(key) == value
                                                                     for key, value in before['audit'].items())),
                       issuer_sequences=dict(before=before['sequences'], after=after['sequences'],
                                             equal=before['sequences'] == after['sequences']))
        if (not summary['failures'] and not changed and not any(residual.values()) and not issuer_maps
                and summary['issuer_audit']['previous_rows_unchanged']):
            summary['status'] = 'PASS'
        original = self._record('FINAL_CLEANUP', summary)
        summary['originals'] = list(self.receipts)
        require(original in summary['originals'] and summary['status'] == 'PASS', 'MANAGED_AUTH_CLEANUP_INCOMPLETE')
        self.phase = 'FINISHED'
        return summary

    def after_restore(self, report):
        try:
            return self._complete_cleanup(report)
        finally:
            self.transport.forget_keys()
