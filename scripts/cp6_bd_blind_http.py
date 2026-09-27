"""Independent disposable Auth/PostgREST probe for the BD facade.

Creates local-only users through Auth, ERP assignments through a privileged
fixture connection, then calls the public RPC with their actual JWTs.
No token, password, or service key is written to logs or artifacts.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bd-blind-http-results.json"


def status_env() -> dict[str, str]:
    raw = subprocess.check_output(["supabase", "status", "--workdir", "cp6-bd-blind-local", "-o", "env"],
                                  cwd=ROOT, text=True)
    env = {}
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.removeprefix("export ").split("=", 1)
            parts = shlex.split(value)
            env[key] = parts[0] if parts else ""
    for key in ("API_URL", "ANON_KEY", "SERVICE_ROLE_KEY"):
        assert env.get(key), f"Missing local Supabase status field {key}"
    return env


def request(url: str, path: str, apikey: str, bearer: str, body: dict) -> tuple[int, dict]:
    call = Request(url.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
        headers={"apikey": apikey, "Authorization": "Bearer " + bearer,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urlopen(call, timeout=15) as response:
            return response.status, json.loads(response.read() or b"{}")
    except HTTPError as error:
        data = error.read()
        return error.code, json.loads(data) if data else {"message": "no body"}


def create_user(url: str, service: str) -> tuple[uuid.UUID, str]:
    name = uuid.uuid4().hex
    email, password = f"audit-{name}@example.invalid", uuid.uuid4().hex + "aB!8"
    code, result = request(url, "/auth/v1/admin/users", service, service,
        {"email": email, "password": password, "email_confirm": True})
    assert code in (200, 201) and result.get("id"), (code, {"message": result.get("msg") or result.get("message")})
    return uuid.UUID(result["id"]), (email + "\n" + password)


def token(url: str, anon: str, credential: str) -> str:
    email, password = credential.split("\n", 1)
    code, result = request(url, "/auth/v1/token?grant_type=password", anon, anon,
                           {"email": email, "password": password})
    assert code == 200 and result.get("access_token"), (code, result.get("msg") or result.get("message"))
    return result["access_token"]


def rpc(url: str, anon: str, bearer: str, action: str, payload: dict, request_id: uuid.UUID) -> tuple[int, dict]:
    return request(url, "/rest/v1/rpc/erp_save_laundry_bd_action_v1", anon, bearer,
                   {"p_action": action, "p_payload": payload, "p_client_request_id": str(request_id)})


def main() -> None:
    local = status_env()
    url, anon, service = (local[x] for x in ("API_URL", "ANON_KEY", "SERVICE_ROLE_KEY"))
    owner_auth, owner_credentials = create_user(url, service)
    spare_auth, _ = create_user(url, service)
    viewer_auth, viewer_credentials = create_user(url, service)
    with psycopg.connect(os.environ["PGURL"], autocommit=True) as conn, conn.cursor() as cur:
        owner = cur.execute("select id from erp.app_roles where role_code='OWNER' and is_active").fetchone()
        viewer = cur.execute("""
            select r.id,r.role_code from erp.app_roles r
            where r.is_active and r.role_code<>'OWNER'
              and exists(select 1 from erp.app_role_permissions rp where rp.role_id=r.id
                         and rp.permission_key='production.laundry.view')
              and not exists(select 1 from erp.app_role_permissions rp where rp.role_id=r.id
                             and rp.permission_key in('finance.hpp.view','finance.hpp.manage','settings.erp.manage'))
            order by r.role_code limit 1
        """).fetchone()
        assert owner and viewer, "Owner and a laundry view-only role are required in the baseline fixture"
        for user, role_id, code in ((owner_auth, owner[0], "OWNER"), (spare_auth, owner[0], "OWNER"),
                                    (viewer_auth, viewer[0], viewer[1])):
            cur.execute("""insert into erp.app_users(auth_user_id,full_name,role,role_id)
                           values(%s,%s,%s,%s)""", (user, "Blind BD local audit", code, role_id))

    owner_jwt = token(url, anon, owner_credentials)
    viewer_jwt = token(url, anon, viewer_credentials)
    policy_payload = {"policy_key": "LAU_DEC04", "operation": "SET", "expected_version": "1",
                      "reason": "Audit permission replay", "value": {"sale_with_unknown_laundry": "REFUSE"}}
    action_id = uuid.uuid4()
    first_code, first = rpc(url, anon, owner_jwt, "SET_POLICY", policy_payload, action_id)
    assert first_code == 200 and first.get("status") == "SET", (first_code, first)
    view_code, view = rpc(url, anon, viewer_jwt, "SET_POLICY", policy_payload, uuid.uuid4())
    assert view_code >= 400 and ("BD_OWNER_ONLY" in str(view) or "PERMISSION_DENIED" in str(view)), (view_code, view)
    with psycopg.connect(os.environ["PGURL"], autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("""update erp.app_users set role_id=%s,role=%s,row_version=row_version+1
                       where auth_user_id=%s""", (viewer[0], viewer[1], owner_auth))
    replay_code, replay = rpc(url, anon, owner_jwt, "SET_POLICY", policy_payload, action_id)
    fresh_code, fresh = rpc(url, anon, owner_jwt, "SET_POLICY", policy_payload, uuid.uuid4())
    assert replay_code == 200 and replay.get("status") == "SET" and replay.get("replayed") is True, (replay_code, replay)
    assert fresh_code >= 400 and ("BD_OWNER_ONLY" in str(fresh) or "PERMISSION_DENIED" in str(fresh)), (fresh_code, fresh)
    read_code, read = request(url, "/rest/v1/rpc/erp_get_laundry_bd_workspace_v1", anon, owner_jwt, {"p_filters": {}})
    assert read_code == 200 and read.get("money_visible") is False and read.get("invoices") is None, (read_code, read)
    anon_code, anon_result = rpc(url, anon, anon, "SET_POLICY", policy_payload, uuid.uuid4())
    assert anon_code >= 400, (anon_code, anon_result)
    result = {"status": "AUTH_HTTP_REPLAY_PROVEN", "candidate": "08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec",
              "first": first.get("status"), "viewer_refusal": view.get("message"),
              "replay_after_owner_demoted": {"http": replay_code, "status": replay.get("status"), "replayed": replay.get("replayed")},
              "fresh_after_owner_demoted": {"http": fresh_code, "message": fresh.get("message")},
              "demoted_workspace": {"money_visible": read.get("money_visible"), "invoices": read.get("invoices")},
              "anon_http": anon_code, "request_id": str(action_id), "production_go": False}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(OUT.read_text(), flush=True)


if __name__ == "__main__":
    main()
