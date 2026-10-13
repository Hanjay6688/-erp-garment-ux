import contextlib
import io
import json
import unittest

import healthcheck as h


def config():
    return {"ERP_HEALTHCHECK_ENABLED": "true", "ERP_HEALTHCHECK_PROJECT_REF": h.TARGET_PROJECT,
            "ERP_HEALTHCHECK_DATABASE_URL":
            f"postgresql://erp_healthcheck:TEST_ONLY@db.{h.TARGET_PROJECT}.supabase.co:5432/postgres"}


class Connection:
    def __init__(self, row=(1, "postgres", "on", h.ROLE, False, False, False, False), error=None):
        self.row, self.error = row, error
        self.read_only = False
        self.statements = []
        self.rolled_back = self.closed = False

    def execute(self, sql):
        if not self.read_only:
            raise AssertionError("Query before read-only transaction")
        self.statements.append(sql)
        if sql == h.QUERY and self.error:
            raise self.error
        return self

    def fetchone(self):
        return self.row

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class HealthcheckTests(unittest.TestCase):
    def invoke(self, env, conn=None, connect_error=None):
        calls = []

        def connect(**kwargs):
            calls.append(kwargs)
            if connect_error:
                raise connect_error
            return conn

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = h.run(env, connect)
        return code, json.loads(output.getvalue()), calls

    def test_disabled_never_connects(self):
        env = config()
        env["ERP_HEALTHCHECK_ENABLED"] = "false"
        result, receipt, calls = self.invoke(env)
        self.assertEqual((result, receipt["code"], calls), (1, "NOT_ENABLED", []))

    def test_legacy_and_unapproved_project_never_connect(self):
        for ref in ["vlxdhpkjeevubjxexnfo", "", "another_project"]:
            with self.subTest(ref=ref):
                env = config()
                env["ERP_HEALTHCHECK_PROJECT_REF"] = ref
                self.assertEqual(self.invoke(env)[2], [])
                self.assertEqual(self.invoke(env)[1]["code"], "PROJECT_NOT_APPROVED")

    def test_dsn_override_and_wrong_target_never_connect(self):
        for url in [
            "postgresql://erp_healthcheck:secret@127.0.0.1/postgres",
            config()["ERP_HEALTHCHECK_DATABASE_URL"] + "?host=evil.example",
            config()["ERP_HEALTHCHECK_DATABASE_URL"].replace("/postgres", "/other"),
            config()["ERP_HEALTHCHECK_DATABASE_URL"].replace("erp_healthcheck:", "postgres:"),
            config()["ERP_HEALTHCHECK_DATABASE_URL"].replace(":5432/", ":6543/"),
            "postgresql://erp_healthcheck.badref:secret@aws-0-ap-southeast-1.pooler.supabase.com/postgres",
            "postgresql://erp_healthcheck:secret@db.vlxdhpkjeevubjxexnfo.supabase.co/postgres",
        ]:
            with self.subTest(url=url):
                env = config()
                env["ERP_HEALTHCHECK_DATABASE_URL"] = url
                code, receipt, calls = self.invoke(env)
                self.assertEqual((code, receipt["code"], calls), (1, "INVALID_CONNECTION_CONFIG", []))

    def test_session_pooler_is_bound_to_project(self):
        env = config()
        env["ERP_HEALTHCHECK_DATABASE_URL"] = (
            f"postgresql://erp_healthcheck.{h.TARGET_PROJECT}:TEST_ONLY"
            "@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres")
        args = h.connection_args(env)
        self.assertEqual(args["user"], "erp_healthcheck." + h.TARGET_PROJECT)
        self.assertEqual((args["sslmode"], args["sslrootcert"]), ("verify-full", "system"))

    def test_success_rolls_back_closes_and_does_not_query_business_tables(self):
        conn = Connection()
        code, receipt, calls = self.invoke(config(), conn)
        self.assertEqual((code, receipt["status"]), (0, "PASS"))
        self.assertTrue(conn.rolled_back and conn.closed)
        self.assertEqual(len(conn.statements), 4)
        self.assertTrue(all(s.startswith("SET LOCAL ") or s == h.QUERY for s in conn.statements))
        self.assertEqual(calls[0]["connect_timeout"], 8)
        self.assertNotIn("TEST_ONLY", json.dumps(receipt))

    def test_unexpected_database_readwrite_or_privileged_role_fails(self):
        good = [1, "postgres", "on", h.ROLE, False, False, False, False]
        for index, value in [(0, 0), (1, "other"), (2, "off"), (3, "postgres"),
                             (4, True), (5, True), (6, True), (7, True)]:
            with self.subTest(index=index):
                row = good.copy()
                row[index] = value
                conn = Connection(tuple(row))
                code, receipt, _ = self.invoke(config(), conn)
                self.assertEqual((code, receipt["code"]), (1, "UNEXPECTED_DATABASE_OR_ROLE"))
                self.assertTrue(conn.rolled_back and conn.closed)

    def test_connection_failure_redacts_exception(self):
        code, receipt, _ = self.invoke(config(), connect_error=RuntimeError("PASSWORD_SECRET raw-host"))
        self.assertEqual((code, receipt["code"]), (1, "CONNECTION_OR_QUERY_FAILED"))
        self.assertNotIn("PASSWORD_SECRET", json.dumps(receipt))

    def test_query_failure_redacts_and_cleans_up(self):
        conn = Connection(error=RuntimeError("PRIVATE_SERVER_DATA"))
        code, receipt, _ = self.invoke(config(), conn)
        self.assertEqual((code, receipt["status"]), (1, "FAIL"))
        self.assertTrue(conn.rolled_back and conn.closed)
        self.assertNotIn("PRIVATE_SERVER_DATA", json.dumps(receipt))


if __name__ == "__main__":
    unittest.main(verbosity=2)
