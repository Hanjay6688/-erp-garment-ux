"""Real two-backend pocket-busy/refusal/retry schedule; no product changes.

The retained same-UUID race still requires actual blocking. Distinct UUIDs
must fail fast at the actual pocket try-lock, leave the complete committed
catalogue/rows/sequences unchanged, and retry only after holder release.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from queue import Queue
import json
import psycopg

HERE=Path(__file__).resolve().parent


def require(ok,detail):
    if not ok:raise AssertionError(detail)


def require_busy(outcome):
    require(type(outcome)is dict and outcome.get('ok')is False
        and outcome.get('sqlstate')=='P0001'
        and (outcome.get('message')or'').startswith('POCKET_PERIOD_BUSY:'),
        dict(error='SKU27_EXACT_POCKET_BUSY_REQUIRED',actual=outcome))


def require_contention(proof,same_uuid):
    if same_uuid:
        require(proof.get('kind')=='BLOCKED'and proof.get('holder_blocks_worker')is True,proof)
        return
    require(proof.get('kind')=='FAIL_FAST'and proof.get('holder_blocks_worker')is False
        and proof.get('distinct_actual_backend_pids')is True
        and proof.get('holder_in_transaction_at_refusal')is True
        and proof.get('retry_only_after_holder_release')is True,proof)
    require_busy(proof.get('first_attempt'))
    receipt=proof.get('complete_busy_no_effect',{})
    require(receipt.get('all22_and_all_current_rows_sequences_unchanged')is True
        and receipt.get('before_sha256')==receipt.get('after_sha256')
        and receipt.get('dropped_fields')==[],proof)


def run(tools,first_op,second_op,commit,*,same_uuid,native_fixture):
    if same_uuid:return tools.two_sessions(first_op,second_op,commit)
    n=native_fixture;ready=Queue()

    def local(connection,cursor):
        require(connection.info.host in('localhost','127.0.0.1')and connection.info.port==54322,
                'SKU27_RACE_LOCAL_DISPOSABLE_ONLY')
        require(cursor.execute('select current_database()').fetchone()==('cp6_auditor_race',),
                'SKU27_RACE_EXACT_COPY_REQUIRED')

    def snapshot():
        with tools.connect()as connection,connection.cursor()as cursor:
            local(connection,cursor);value=n.capture(cursor);connection.rollback();return value

    def unchanged(before,label):
        with tools.connect()as connection,connection.cursor()as cursor:
            local(connection,cursor);proof=n.unchanged(cursor,before,label);connection.rollback();return proof

    def send(announce=False):
        try:
            with tools.connect()as connection,connection.cursor()as cursor:
                local(connection,cursor)
                cursor.execute("set local lock_timeout='20s';set local statement_timeout='60s'")
                pid=cursor.execute('select pg_backend_pid()').fetchone()[0]
                if announce:ready.put(pid)
                result=second_op(cursor);connection.commit()
                return dict(ok=True,result=result)
        except psycopg.Error as error:
            return dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary)

    with tools.connect()as holder,holder.cursor()as cursor,ThreadPoolExecutor(max_workers=1)as pool:
        local(holder,cursor);hpid=cursor.execute('select pg_backend_pid()').fetchone()[0]
        held=first_op(cursor)
        try:
            require(holder.info.transaction_status==psycopg.pq.TransactionStatus.INTRANS,
                    'SKU27_HOLDER_MUST_REMAIN_UNCOMMITTED')
            before=snapshot()
            contract=json.loads((HERE/'RACE_CONTRACT.json').read_bytes())
            require(before['catalog']['functions']['erp.pocket_period_lock_v1()']==contract['actual_pocket_function_row19'],
                    'SKU27_ACTUAL_POCKET_TRY_LOCK_CONTRACT_CHANGED')
            future=pool.submit(send,True);wpid=ready.get(timeout=20)
            try:first=future.result(timeout=6)
            except TimeoutError as error:
                raise AssertionError('SKU27_DISTINCT_UUID_MUST_FAIL_FAST_NOT_WAIT')from error
            require_busy(first)
            require(hpid!=wpid and holder.info.transaction_status==psycopg.pq.TransactionStatus.INTRANS,
                    'SKU27_REAL_UNRELEASED_HOLDER_REQUIRED')
            busy_proof=unchanged(before,'DISTINCT_UUID_POCKET_BUSY_'+('COMMIT'if commit else'ROLLBACK'))
            (holder.commit if commit else holder.rollback)()
            require(holder.info.transaction_status==psycopg.pq.TransactionStatus.IDLE,
                    'SKU27_RETRY_BEFORE_HOLDER_RELEASE_REFUSED')
            retry_before=snapshot()if commit else None
            outcome=send()
            retry_proof=None
            if commit:
                require(outcome.get('ok')is False and outcome.get('sqlstate')=='P0001'
                    and (outcome.get('message')or'').startswith('STALE_VERSION:'),outcome)
                retry_proof=unchanged(retry_before,'DISTINCT_UUID_COMMITTED_STALE_RETRY')
            proof=dict(kind='FAIL_FAST',holder_blocks_worker=False,first_attempt=first,
                holder_backend_pid=hpid,worker_backend_pid=wpid,distinct_actual_backend_pids=hpid!=wpid,
                holder_in_transaction_at_refusal=True,retry_only_after_holder_release=True,
                complete_busy_no_effect=busy_proof,complete_stale_retry_no_effect=retry_proof,
                same_request_and_payload_retried=True,holder_committed=commit)
            require_contention(proof,False)
            return held,proof,outcome
        finally:
            # Release before the executor waits for a blocked worker on failure.
            if holder.info.transaction_status!=psycopg.pq.TransactionStatus.IDLE:holder.rollback()
