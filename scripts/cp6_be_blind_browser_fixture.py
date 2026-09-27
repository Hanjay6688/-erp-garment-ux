"""Disposable BE browser prerequisites and independent read-back, no product writes outside public commands."""
from datetime import date, timedelta
import json
import os
import sys

import psycopg
import cp6_be_browser_fixture as product_fixture
import cp6_bd_probe as bd


def main():
    url = os.environ["PGURL"].replace("//postgres:", "//supabase_admin:", 1)
    assert url.endswith("@127.0.0.1:54322/postgres"), "BLIND_BROWSER_LOCAL_ONLY"
    action, arg = sys.argv[1], json.loads(sys.argv[2])
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        if action == "create":
            # The business oracle already imports pocket sources on day -10.
            # Give the browser source its own history day to assert one pool.
            fixture_day = date.fromisoformat(arg["today"])
            if arg["kind"] == "pocket":
                fixture_day -= timedelta(days=7)
            result = product_fixture.create(cur, fixture_day, arg["kind"])
            bd.api.admin(cur)
            conn.commit()
        elif action == "read":
            result = product_fixture.read(cur, arg)
            conn.rollback()
        elif action == "bind":
            cur.execute("""insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
                select gen_random_uuid(),%s,'Blind browser owner','OWNER',id,true
                from erp.app_roles where role_code='OWNER' and is_active returning id""", (arg["auth_id"],))
            result = {"bound": cur.fetchone() is not None}
            conn.commit()
        else:
            raise ValueError("BLIND_BROWSER_ACTION")
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
