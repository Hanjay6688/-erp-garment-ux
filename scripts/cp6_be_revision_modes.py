"""BE audit revision plus BF/BD/BE regression on disposable copies; writer evidence."""
import cp6_be_revision_probe as revision
import cp6_bf_modes as bf
import cp6_be_probe as be
import uuid
INSTALL_BF=True

def cases(cur,today):return revision.cases(cur,today)+be.cases(cur,today)+bf.cases(cur,today)
def races(tools,today):return bf.races(tools,today)
def http_cases(http,today):
    def sewing():
      with http.connect() as conn,conn.cursor() as cur:
        with bf.bd_revision.bd._fixture_usage(cur):f=revision.sewing_fixture(cur,today)
        conn.commit()
      owner=http.login('OWNER','be-revision-sewing-owner');warehouse=http.login('GUDANG','be-revision-sewing-warehouse')
      args=dict(p_event_id=f['event'],p_reason='BE real Auth sewing inverse',p_client_request_id=str(uuid.uuid4()),p_expected_version=f['version'])
      anon=http.anon_rpc('erp_reverse_sewing_terminal_v1',args)
      denied=warehouse.rpc('erp_reverse_sewing_terminal_v1',args)
      held=owner.rpc('erp_reverse_sewing_terminal_v1',args)
      missing=owner.rpc('erp_reverse_sewing_terminal_v1',{k:v for k,v in args.items() if k!='p_expected_version'})
      with http.connect() as conn,conn.cursor() as cur:
        state=revision.one(cur,'select erp.pocket_period_state_v1(%s)',f['pool']);conn.rollback()
      cancelled=owner.rpc('erp_save_pocket_fabric_action_v1',dict(p_action='CANCEL_PERIOD',p_payload=dict(id=f['pool'],expected_revision=state['revision'],reason='Release consumed sewing denominator'),p_client_request_id=str(uuid.uuid4())))
      assert cancelled['status']==200,cancelled
      done=owner.rpc('erp_reverse_sewing_terminal_v1',args);again=owner.rpc('erp_reverse_sewing_terminal_v1',args)
      page=owner.rpc('erp_get_pocket_periods_v1',dict(p_query=f['pool'],p_offset=0))
      hidden=warehouse.rpc('erp_get_pocket_periods_v1',dict(p_query=f['pool'],p_offset=0))
      with http.connect() as conn,conn.cursor() as cur:
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
      try:revoked=owner.rpc('erp_reverse_sewing_terminal_v1',args)
      finally:
        with http.connect() as conn,conn.cursor() as cur:
          cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
      with http.connect() as conn,conn.cursor() as cur:
        count=revision.one(cur,'select count(*) from erp.sewing_terminal_events where reversal_of_id=%s',f['event']);conn.rollback()
      return revision.b.verdict(dict(anon=anon['status'] in (401,403),warehouse=denied['status']==403,
        dependency=held['status']>=400 and 'sebelum mengoreksi hasil jahit' in str(held),
        version_required=missing['status']>=400 and 'expected_version are required' in str(missing),
        owner=done['status']==200,replay=done==again and count==1,revoked=revoked['status']>=400,
        page_owner=page['status']==200 and page['body']['periods'][0]['id']==f['pool'],page_restricted=hidden['status']==403))
    return [('BE_REV_HTTP:PUBLIC_SEWING_AND_PERIOD_ACCESS',sewing)]+bf.http_cases(http,today)
