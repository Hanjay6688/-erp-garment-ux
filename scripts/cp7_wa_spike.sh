#!/usr/bin/env bash
# WA-0 (owner D17-6): what the CI Supabase stack offers for WhatsApp forwarding, before any design is built on it.
# Facts only, printed as lines "WA0 <name> <value>": extensions available, pg_net worker database, a fake CallMeBot
# reached from Postgres in a cloned database, rollback sends nothing, Vault round trip. No real message, no real key.
set -uo pipefail
PG="postgresql://postgres:postgres@127.0.0.1:54322"
q() { psql "$PG/$1" -X -v ON_ERROR_STOP=1 -At -c "$2"; }
say() { echo "WA0 $1 $2"; }

say extensions "$(q postgres "select string_agg(name||'='||coalesce(installed_version,'-')||'/'||default_version,' ' order by name) from pg_available_extensions where name in('pg_net','supabase_vault','pg_cron','http')")"
say preload "$(q postgres "show shared_preload_libraries")"
say pg_net_database_name "$(q postgres "select coalesce(current_setting('pg_net.database_name',true),'(unset)')")"

# Fake CallMeBot on the stack's docker network: answers 200 'Message queued', or 500 when text contains FAIL.
NET="$(docker network ls --format '{{.Name}}' | grep -m1 supabase_network)"
say docker_network "$NET"
docker run -d --rm --name fake-callmebot --network "$NET" python:3.12-alpine python -u -c '
import http.server,urllib.parse
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        print("FAKE_REQUEST",self.path.split("?")[0],sorted(q),q.get("text"),flush=True)
        fail="FAIL" in (q.get("text") or [""])[0]
        self.send_response(500 if fail else 200);self.end_headers()
        self.wfile.write(b"error" if fail else b"Message queued")
    def log_message(self,*a):pass
http.server.ThreadingHTTPServer(("0.0.0.0",8080),H).serve_forever()' >/dev/null
sleep 5
say fake_server "$(docker ps --filter name=fake-callmebot --format '{{.Status}}')"

# Vault round trip in postgres (the hosted shape) before any clone.
say vault_postgres "$(q postgres "select (select decrypted_secret from vault.decrypted_secrets where id=vault.create_secret('FAKEKEY-WA0','cp7_wa0_probe'))='FAKEKEY-WA0'" 2>&1 | tail -1)"
q postgres "delete from vault.secrets where name='cp7_wa0_probe'" >/dev/null 2>&1

# A second database standing in for the harness clone (the harness copies postgres with every session fenced; here an
# empty database is enough to learn whether the pg_net worker can serve a database other than postgres).
createdb -h 127.0.0.1 -p 54322 -U postgres wa0_clone 2>&1 | tail -1; say clone_created "$?"
say vault_create_clone "$(q wa0_clone "create extension if not exists supabase_vault" 2>&1 | tail -1)"
say vault_clone "$(q wa0_clone "select (select decrypted_secret from vault.decrypted_secrets where id=vault.create_secret('FAKEKEY-WA0C','cp7_wa0_probe'))='FAKEKEY-WA0C'" 2>&1 | tail -1)"

send() { # db text -> request id
  q "$1" "select net.http_get(url:='http://fake-callmebot:8080/whatsapp.php',params:=jsonb_build_object('phone','+620000000000','text','$2','apikey','FAKEKEY'))"; }
wait_resp() { # db id
  for i in $(seq 1 30); do r="$(q "$1" "select coalesce(status_code::text,'null')||' '||coalesce(left(content,40),'')||' err='||coalesce(error_msg,'') from net._http_response where id=$2" 2>/dev/null)"
    [ -n "$r" ] && { echo "$r"; return; }; sleep 1; done; echo TIMEOUT; }

# pg_net in the clone, worker pointed at the clone.
say pg_net_create_clone "$(q wa0_clone "create extension if not exists pg_net" 2>&1 | tail -1)"
say set_database_name "$(q postgres "alter system set pg_net.database_name='wa0_clone'" 2>&1 | tail -1)"
q postgres "select pg_reload_conf()" >/dev/null
say worker_restart "$(q wa0_clone "select net.worker_restart()" 2>&1 | tail -1)"
sleep 3
id="$(send wa0_clone 'WA0 hello' 2>&1 | tail -1)"; say clone_send_id "$id"
say clone_response "$(wait_resp wa0_clone "$id")"
id="$(send wa0_clone 'WA0 FAIL' 2>&1 | tail -1)"; say clone_send_fail_id "$id"
say clone_response_fail "$(wait_resp wa0_clone "$id")"
# Rollback: the queued request disappears with the transaction.
psql "$PG/wa0_clone" -X -At -c "begin; select net.http_get(url:='http://fake-callmebot:8080/whatsapp.php',params:=jsonb_build_object('text','WA0 ROLLBACK')); rollback;" >/dev/null 2>&1
sleep 6
say fake_requests "$(docker logs fake-callmebot 2>&1 | grep -c FAKE_REQUEST)"
say rollback_reached_server "$(docker logs fake-callmebot 2>&1 | grep -c 'WA0 ROLLBACK')"
say queue_row_shape "$(q wa0_clone "select string_agg(column_name,',' order by ordinal_position) from information_schema.columns where table_schema='net' and table_name='http_request_queue'")"
say response_retention "$(q postgres "select coalesce(current_setting('pg_net.ttl',true),'(unset)')")"
say pg_cron_in_clone "$(q wa0_clone "select count(*) from pg_extension where extname='pg_cron'")"
# Hosted shape: worker back on postgres, pg_net created there.
q postgres "alter system reset pg_net.database_name" >/dev/null 2>&1; q postgres "select pg_reload_conf()" >/dev/null
say pg_net_create_postgres "$(q postgres "create extension if not exists pg_net" 2>&1 | tail -1)"
say worker_restart_postgres "$(q postgres "select net.worker_restart()" 2>&1 | tail -1)"
sleep 3
id="$(send postgres 'WA0 postgres' 2>&1 | tail -1)"; say postgres_send_id "$id"
say postgres_response "$(wait_resp postgres "$id")"
docker logs fake-callmebot 2>&1 | sed 's/^/WA0 fake_log /'
docker stop fake-callmebot >/dev/null 2>&1 || true
exit 0
