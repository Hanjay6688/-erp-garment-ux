"""Exercise the candidate component against the disposable Global through its usual two RPCs."""
import hashlib
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import psycopg
import cp7_r3_reminders_cases as rem

HERE = Path(__file__).resolve().parent
APP = Path(os.environ["REMINDER_APP"]).resolve()
OUT = Path(os.environ["WRITER_RESULTS"])
OUT.mkdir(exist_ok=True, parents=True)
RELEASE = json.loads((HERE / "candidate.json").read_text())
ORIGINAL = "2026-11-20T07:00:32.942069+00:00"
DB = dict(host=os.environ["PGHOST"], dbname="cp6_rollback", user="supabase_admin")


def store(name, value):
    target = OUT / (name + ".json")
    tmp = target.with_suffix(".part")
    tmp.write_text(json.dumps(value, indent=2, default=str) + "\n")
    tmp.replace(target)


def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def seal():
    with psycopg.connect(**DB) as c:
        return c.execute("select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()").fetchone()[0]


def install():
    parent = seal()
    assert parent["sha256"] == "a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7"
    directory = HERE.parent / "close12" / "product"
    pins = dict(zip(["install.py", "definitions.patch", "manifest.json", "README.md"], [
        "77cc2c35a78c1fde725e37199a80f87a5f9965e3", "73cba3c8e32aef7254a8be78e17a19a43d1bb5d7",
        "87959104d1a4989aabb1fbe8ad3167fdf8e7fe76", "083ee3912101304ceb637ad32d9214a92b6b8626"]))
    assert all(git_blob(directory / name) == expected for name, expected in pins.items())
    spec = importlib.util.spec_from_file_location("g14_installer", directory / "install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with psycopg.connect(**DB) as c:
        mod.apply(c, "up")
    installed = seal()
    assert installed["sha256"] == RELEASE["database_sha256"] and installed["groups"] == 25
    ui = {name: change for name, change in RELEASE["files"].items() if name.startswith("src/")}
    assert all(git_blob(APP / name) == change["before"] for name, change in ui.items())
    subprocess.run(["git", "apply", "--no-index", str(HERE / "ui.patch")], cwd=APP, check=True)
    assert all(git_blob(APP / name) == change["after"] for name, change in ui.items())
    store("installation", dict(release=RELEASE, parent_seal=parent, installed=installed, source=ui))


class Adapter(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, body, mime="application/json", code=200):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            return self.reply(b'<html><head><meta charset="utf-8"></head><body><div id="root"></div><script src="/ui.js"></script></body></html>', "text/html")
        if self.path == "/ui.js":
            return self.reply((OUT / "ui.js").read_bytes(), "text/javascript")
        self.reply(b"", code=404)

    def do_POST(self):
        try:
            args = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with psycopg.connect(**DB) as c, c.cursor() as q:
                value = self.call(q, args)
            self.reply(json.dumps(value, default=str).encode())
        except Exception as e:
            store("adapter-first-error", dict(route=self.path, detail=str(e)[:1000]))
            self.reply(json.dumps({"error": str(e)[:500]}).encode(), code=500)

    def call(self, q, args):
        if self.path == "/seed":
            self.server.actor = rem.owner(q)
            for i in range(args["n"]):
                clock = datetime.fromisoformat(ORIGINAL) + timedelta(minutes=i)
                rem.save(q, self.server.actor, "SAVE", rem.body(clock.isoformat(), title=f"R{i}", note=""))
            return True
        actor = self.server.actor
        if self.path == "/facts":
            rows = {r["id"]:r for r in rem.own_rows(q, actor)}
            ordered = [rows[i] for i in rem.order_of(q, actor, "OPEN")]
            return [dict(id=r["id"], title=r["title"], note=r["note"], due=r["due_at"].isoformat(), version=r["row_version"]) for r in ordered]
        if self.path == "/change":
            if args["mode"] == "insert":
                return rem.save(q, actor, "SAVE", rem.body("2026-11-19T01:00:00Z", title="Earlier"))
            ids = rem.order_of(q, actor, "OPEN")
            row = rem.row(q, ids[-1] if args["mode"] == "reorder" else ids[0])
            if args["mode"] == "remove":
                return rem.save(q, actor, "DONE", {"id":row["id"]}, expected=row["row_version"])
            assert args["mode"] == "reorder"
            body = rem.body(row["due_at"].isoformat(), title=row["title"], priority="URGENT", rid=row["id"])
            return rem.save(q, actor, "SAVE", body, expected=row["row_version"])
        assert self.path == "/rpc"
        name, params = args["name"], args["args"]
        if name == "erp_cp7_get_reminders_v1":
            value = rem.get(q, actor, params["p_query"])
        else:
            assert name == "erp_cp7_save_reminder_v1"
            value = rem.save(q, actor, params["p_action"], params["p_payload"], params["p_expected"], params["p_request"])
        return {"data": value, "error": None}


if __name__ == "__main__":
    install()
    subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=APP, check=True)
    subprocess.run(["node", str(APP / "node_modules/vitest/vitest.mjs"), "run", "src/ConnectedRemindersPage.dom.test.tsx",
                    "src/ConnectedRemindersWa.dom.test.tsx", "src/cp6BusinessTime.test.ts", "--reporter=json",
                    "--outputFile=" + str(OUT / "vitest.json")], cwd=APP, check=True)
    with ThreadingHTTPServer(("127.0.0.1", 0), Adapter) as http:
        thread = Thread(target=http.serve_forever, daemon=True)
        thread.start()
        try:
            subprocess.run(["node", str(HERE / "browser.cjs"), str(APP), str(OUT),
                            f"http://127.0.0.1:{http.server_address[1]}"], cwd=APP, check=True)
        finally:
            http.shutdown()
            thread.join()
