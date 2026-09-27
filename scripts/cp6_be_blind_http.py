"""Independent disposable Auth/PostgREST probe for the BE facade.

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
OUT = ROOT / "be-blind-http-results.json"
FIXTURE = ROOT / "be-blind-http-fixture.json"


def status_env() -> dict[str, str]:
    raw = subprocess.check_output(["supabase", "status", "--workdir", "cp6-be-blind-local", "-o", "env"],
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
    return request(url, "/rest/v1/rpc/erp_save_product_conversion_action_v1", anon, bearer,
                   {"p_action": action, "p_payload": payload, "p_client_request_id": str(request_id)})


def main() -> None:
    local = status_env()
    fixture = json.loads(FIXTURE.read_text())
    url, anon, service = (local[x] for x in ("API_URL", "ANON_KEY", "SERVICE_ROLE_KEY"))
    owner_auth, owner_credentials = create_user(url, service)
    spare_auth, _ = create_user(url, service)
    viewer_auth, viewer_credentials = create_user(url, service)
    with psycopg.connect(os.environ["PGURL"], autocommit=True) as conn, conn.cursor() as cur:
        owner = cur.execute("select id from erp.app_roles where role_code='OWNER' and is_active").fetchone()
        assert owner, "Owner role required in baseline fixture"
        for user, role_id, code in ((owner_auth, owner[0], "OWNER"), (spare_auth, owner[0], "OWNER")):
            cur.execute("""insert into erp.app_users(auth_user_id,full_name,role,role_id)
                           values(%s,%s,%s,%s)""", (user, "Blind BE local audit", code, role_id))

    owner_jwt = token(url, anon, owner_credentials)
    view_code_name = "BE_AUD_" + uuid.uuid4().hex[:10].upper()
    create_code, create_role = request(url, "/rest/v1/rpc/erp_save_role_v1", anon, owner_jwt,
        {"p_payload": {"code": view_code_name, "name": "BE independent view-only role",
                        "permission_keys": ["warehouse.brand_conversion.view"],
                        "confirm_high_risk": False, "change_reason": "BE auditor permission matrix"},
         "p_client_request_id": str(uuid.uuid4()), "p_expected_version": None})
    assert create_code == 200, (create_code, create_role)
    with psycopg.connect(os.environ["PGURL"], autocommit=True) as conn, conn.cursor() as cur:
        viewer = cur.execute("select id,role_code from erp.app_roles where role_code=%s and is_active",
                             (view_code_name,)).fetchone()
        assert viewer, "Owner-created view-only role missing"
        cur.execute("""insert into erp.app_users(auth_user_id,full_name,role,role_id)
                       values(%s,%s,%s,%s)""", (viewer_auth, "Blind BE local audit", viewer[1], viewer[0]))
    viewer_jwt = token(url, anon, viewer_credentials)
    policy_payload = fixture["payload"]
    action_id = uuid.uuid4()
    first_code, first = rpc(url, anon, owner_jwt, "POST", policy_payload, action_id)
    assert first_code == 200 and first.get("status") == "POSTED", (first_code, first)
    owner_replay_code, owner_replay = rpc(url, anon, owner_jwt, "POST", policy_payload, action_id)
    assert owner_replay_code == 200 and owner_replay.get("conversion_id") == first.get("conversion_id")
    view_code, view = rpc(url, anon, viewer_jwt, "POST", policy_payload, uuid.uuid4())
    assert view_code >= 400 and "PERMISSION_DENIED" in str(view), (view_code, view)
    with psycopg.connect(os.environ["PGURL"], autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("""update erp.app_users set role_id=%s,role=%s,row_version=row_version+1
                       where auth_user_id=%s""", (viewer[0], viewer[1], owner_auth))
    replay_code, replay = rpc(url, anon, owner_jwt, "POST", policy_payload, action_id)
    fresh_code, fresh = rpc(url, anon, owner_jwt, "POST", policy_payload, uuid.uuid4())
    assert replay_code >= 400 and "PERMISSION_DENIED" in str(replay), (replay_code, replay)
    assert fresh_code >= 400 and "PERMISSION_DENIED" in str(fresh), (fresh_code, fresh)
    read_code, read = request(url, "/rest/v1/rpc/erp_get_product_conversion_workspace_v1", anon, owner_jwt,
                              {"p_filters": {"source_lot_id": fixture["source_lot_id"]}})
    assert read_code == 200 and all(lot.get("unit_hpp") is None for lot in read.get("lots", []))
    assert all(doc.get("extra_cost") is None and doc.get("target_value") is None for doc in read.get("documents", []))
    anon_code, anon_result = rpc(url, anon, anon, "POST", policy_payload, uuid.uuid4())
    assert anon_code >= 400, (anon_code, anon_result)
    result = {"status": "BE_AUTH_HTTP_PERMISSION_PROVEN", "candidate": "2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b",
              "first": first.get("status"), "owner_replay_same": owner_replay.get("conversion_id") == first.get("conversion_id"),
              "viewer_refusal": view.get("message"),
              "replay_after_owner_demoted": {"http": replay_code, "message": replay.get("message")},
              "fresh_after_owner_demoted": {"http": fresh_code, "message": fresh.get("message")},
              "demoted_workspace": {"lots": len(read.get("lots", [])), "financial_fields_null": True},
              "anon_http": anon_code, "request_id": str(action_id), "production_go": False}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(OUT.read_text(), flush=True)


if __name__ == "__main__":
    main()
