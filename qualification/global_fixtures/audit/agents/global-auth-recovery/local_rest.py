"""Attempt-owned local PostgREST using the retained disposable stack and wire."""
from pathlib import Path
from types import FunctionType, SimpleNamespace
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import json
import os
import re
import subprocess
import time
import urllib.error

from auth_adapter import APP, AUTH_URL, ISSUER_DB, AuthRefusal, require

DOCKER = ('docker', '--host', 'unix:///var/run/docker.sock')
DB = 'supabase_db_cp5-local'
AUTH = 'supabase_auth_cp5-local'
GATEWAY = 'supabase_kong_cp5-local'
TEMPLATE = 'supabase_rest_cp5-local'
OWNER_LABEL = 'erp.cp7.global.auth-attempt'
BACKENDS = """select pid,datid::bigint,datname,usename from pg_stat_activity
              where application_name=%s order by pid"""


class LocalOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def private_function(fn, **changes):
    return FunctionType(fn.__code__, dict(fn.__globals__, **changes), fn.__name__, fn.__defaults__, fn.__closure__)


def wire(modes):
    # The frozen _call still handles HTTP status, JSON and SQLSTATE bodies.
    # Its private opener disables environment proxies and bearer redirects.
    opener = build_opener(ProxyHandler({}), LocalOnlyRedirect())
    request = SimpleNamespace(Request=Request, urlopen=opener.open)
    return private_function(modes._call, urllib=SimpleNamespace(request=request, error=urllib.error))


def docker(*args, extra_env=None):
    env = {name: value for name, value in os.environ.items() if name not in ('DOCKER_CONTEXT', 'DOCKER_HOST')}
    if extra_env:
        env.update(extra_env)
    try:
        return subprocess.run([*DOCKER, *args], env=env, capture_output=True, text=True, timeout=35)
    except (OSError, subprocess.TimeoutExpired):
        raise AuthRefusal('GLOBAL_AUTH_LOCAL_DOCKER_RESULT_UNKNOWN') from None


def inspect(*names):
    result = docker('inspect', '--type', 'container', *names)
    require(result.returncode == 0, 'EXACT_LOCAL_CONTAINER_INSPECTION_REQUIRED')
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise AuthRefusal('GLOBAL_AUTH_LOCAL_CONTAINER_RESPONSE_INVALID') from None


def bindings(container, internal_port):
    return (container['NetworkSettings'].get('Ports') or {}).get(str(internal_port) + '/tcp') or []


def network_id(container, name):
    return container['NetworkSettings']['Networks'][name]['NetworkID']


def environment(container):
    return dict(item.split('=', 1) for item in container['Config']['Env'] if '=' in item)


def postgres_uri(raw, database, aliases, role):
    try:
        uri = urlsplit(raw)
        valid = (uri.scheme in ('postgresql', 'postgres') and uri.hostname in aliases and uri.username == role
                 and bool(uri.password) and uri.port in (None, 5432) and uri.path == '/' + database
                 and not uri.query and not uri.fragment)
    except (TypeError, ValueError):
        valid = False
    require(valid, 'EXACT_LOCAL_TEMPLATE_DATABASE_URI_REQUIRED')
    return uri


class Actor:
    """Private login material. The inherited token client retains the wire shape."""

    def __init__(self, client):
        self._client = client
        self.auth_user_id, self.role = client.auth_user_id, client.role

    def rpc(self, name, args=None):
        require(self._client is not None, 'ACTOR_CREDENTIALS_ALREADY_RELEASED')
        return self._client.rpc(name, args)

    def close(self):
        self._client = None


class OwnedRest:
    def __init__(self, modes, candidate, attempt, nonce):
        self.modes = modes
        self.call = wire(modes)
        self.get_status = private_function(modes._status_env, BASE=Path(candidate).parent / 'base' / 'cp5-local')
        self.name = 'cp7-global-auth-' + attempt + '-' + nonce
        require(len(self.name) < 64 and re.fullmatch(r'[a-z0-9-]+', self.name), 'EXACT_ATTEMPT_CONTAINER_NAME_REQUIRED')
        self.claimed = False
        self.container_id = None
        self.url = None
        self._anon = self._service = None

    def start(self):
        require(not self.claimed and self.url is None, 'ONE_ATTEMPT_OWNED_REST_REQUIRED')
        db, issuer, gateway, rest = inspect(DB, AUTH, GATEWAY, TEMPLATE)
        expected = (DB, AUTH, GATEWAY, TEMPLATE)
        require(tuple(row['Name'].lstrip('/') for row in (db, issuer, gateway, rest)) == expected
                and all(row['State']['Running'] is True for row in (db, issuer, gateway, rest)),
                'EXACT_RUNNING_DISPOSABLE_STACK_REQUIRED')
        require(any(row['HostPort'] == '54322' and row['HostIp'] in ('127.0.0.1', '0.0.0.0')
                    for row in bindings(db, 5432))
                and any(row['HostPort'] == '54321' and row['HostIp'] in ('127.0.0.1', '0.0.0.0')
                        for row in bindings(gateway, 8000)), 'EXACT_LOOPBACK_STACK_PORTS_REQUIRED')
        common = set(db['NetworkSettings']['Networks'])
        for item in (issuer, gateway, rest):
            common.intersection_update(item['NetworkSettings']['Networks'])
        require(len(common) == 1, 'EXACT_DISPOSABLE_STACK_NETWORK_REQUIRED')
        network = common.pop()
        require(len({network_id(item, network) for item in (db, issuer, gateway, rest)}) == 1,
                'EXACT_DISPOSABLE_STACK_NETWORK_ID_REQUIRED')
        aliases = {DB, *(db['NetworkSettings']['Networks'][network].get('Aliases') or [])}
        issuer_environment = environment(issuer)
        postgres_uri(issuer_environment.get('GOTRUE_DB_DATABASE_URL'), ISSUER_DB, aliases, 'supabase_auth_admin')
        config = {key: value for key, value in environment(rest).items() if key.startswith('PGRST_')}
        uri = postgres_uri(config.get('PGRST_DB_URI'), ISSUER_DB, aliases, 'authenticator')
        require(config.get('PGRST_JWT_SECRET') and re.fullmatch(r'sha256:[a-f0-9]{64}', rest['Image']),
                'EXACT_LOCAL_REST_IMAGE_AND_SIGNER_REQUIRED')
        config.update(PGRST_DB_URI=urlunsplit((uri.scheme, uri.netloc, '/' + APP,
                                             urlencode({'application_name': self.name}), '')),
                      PGRST_DB_SCHEMAS='public', PGRST_DB_CONFIG='false', PGRST_SERVER_PORT='3000',
                      PGRST_SERVER_HOST='0.0.0.0', PGRST_LOG_LEVEL='crit')
        try:
            status = self.get_status()
        except Exception:
            raise AuthRefusal('GLOBAL_AUTH_DISPOSABLE_SUPABASE_STATUS_REFUSED') from None
        require(status.get('API_URL') == AUTH_URL.removesuffix('/auth/v1')
                and all(isinstance(status.get(key), str) and status[key] for key in ('ANON_KEY', 'SERVICE_ROLE_KEY')),
                'EXACT_DISPOSABLE_API_AND_KEYS_REQUIRED')
        self._anon, self._service = status['ANON_KEY'], status['SERVICE_ROLE_KEY']
        require(not self._owned(), 'REST_ATTEMPT_CONTAINER_ALREADY_PRESENT')
        self.claimed = True
        command = ['run', '-d', '--name', self.name, '--label', OWNER_LABEL + '=' + self.name,
                   '--network', network_id(db, network), '--publish', '127.0.0.1::3000', '--log-driver', 'none']
        for key in sorted(config):
            command.extend(('--env', key))
        result = docker(*command, rest['Image'], extra_env=config)
        require(result.returncode == 0 and re.fullmatch(r'[a-f0-9]{64}', result.stdout.strip()),
                'OWNED_REST_LAUNCH_REFUSED')
        self.container_id = result.stdout.strip()
        owned = self._owned()
        require(owned and owned['Id'] == self.container_id and owned['State']['Running'] is True,
                'EXACT_STARTED_REST_CONTAINER_REQUIRED')
        port = bindings(owned, 3000)
        require(len(port) == 1 and port[0]['HostIp'] == '127.0.0.1' and port[0]['HostPort'].isdigit(),
                'EXACT_OWNED_REST_LOOPBACK_BINDING_REQUIRED')
        self.url = 'http://127.0.0.1:' + port[0]['HostPort']
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                if self.call(self.url + '/', None, {}, method='GET')['status'] == 200:
                    return self._anon, self._service
            except (OSError, TimeoutError):
                pass
            time.sleep(0.5)
        raise AuthRefusal('GLOBAL_AUTH_OWNED_REST_NOT_READY')

    def _owned(self):
        result = docker('ps', '-aq', '--no-trunc', '--filter', 'name=^/' + self.name + '$')
        require(result.returncode == 0, 'REST_OWNERSHIP_LIST_REQUIRED')
        ids = result.stdout.split()
        if not ids:
            return None
        require(len(ids) == 1 and re.fullmatch(r'[a-f0-9]{64}', ids[0]), 'EXACT_REST_OWNERSHIP_ID_REQUIRED')
        row, = inspect(ids[0])
        require(row['Name'] == '/' + self.name and row['Id'] == ids[0]
                and (row['Config'].get('Labels') or {}).get(OWNER_LABEL) == self.name
                and (self.container_id is None or self.container_id == row['Id']), 'FOREIGN_REST_CONTAINER_REFUSED')
        return row

    def verify_backend(self, cur, application):
        rows = cur.execute(BACKENDS, (self.name,)).fetchall()
        require(self.url and rows and all(oid == application[1] and database == APP and role == 'authenticator'
                                         for _, oid, database, role in rows), 'REST_NOT_ON_VERIFIED_APPLICATION_OID')
        return dict(application_oid=application[1], backend_pids=[row[0] for row in rows],
                    container_id=self.container_id, public_schema_only=True)

    def verify_no_backend(self, cur):
        for _ in range(8):
            cur.execute('select pg_stat_clear_snapshot()')
            if not cur.execute(BACKENDS, (self.name,)).fetchall():
                return
            time.sleep(0.25)
        raise AuthRefusal('GLOBAL_AUTH_OWNED_REST_DATABASE_BACKEND_REMAINS')

    def auth(self, path, body, admin=False, method='POST'):
        operation = private_function(self.modes.Http._auth, AUTH_URL=AUTH_URL + '/', _call=self.call)
        return operation(self, path, body, admin, method)

    def rpc(self, token, name, args):
        operation = private_function(self.modes.Http._rpc, REST_URL=self.url, _call=self.call)
        return operation(self, token, name, args)

    def client(self, attempt, token, uid, role):
        return Actor(self.modes.HttpUser(attempt, token, uid, role))

    def reap(self):
        owned = self._owned() if self.claimed else None
        if owned:
            result = docker('rm', '-f', owned['Id'])
            require(result.returncode == 0 or self._owned() is None, 'OWNED_REST_REMOVE_REFUSED')
        require(not self.claimed or self._owned() is None, 'OWNED_REST_CONTAINER_REMAINS')
        self.url = None
        return dict(owner=self.name, container_id=self.container_id or (owned and owned['Id']), remaining=False)

    def forget_keys(self):
        self._anon = self._service = None
