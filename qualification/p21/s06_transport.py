"""Transactional pg_net fixture. It records synthetic messages without networking."""

FAKE_KEY = 'FAKEKEY-S06-CLOSE05'


def install(cur):
    cur.execute("select set_config('cp7.s06_fake_key',%s,true)", (FAKE_KEY,))
    cur.execute('''
        create schema if not exists net;
        create table if not exists net._http_response (
            id bigint primary key, status_code integer, timed_out boolean,
            error_msg text, content text);
        create temporary table s06_fake_requests (
            id bigint generated always as identity primary key, phone text not null, body text not null);
        create or replace function net.http_get(
            url text, params jsonb default '{}'::jsonb, headers jsonb default '{}'::jsonb,
            timeout_milliseconds integer default 1000)
        returns bigint language plpgsql security definer set search_path='' as $$
        declare request_id bigint;
        begin
            if url <> 'https://api.callmebot.com/whatsapp.php'
               or params->>'phone' is distinct from '+620000000000'
               or params->>'apikey' is distinct from current_setting('cp7.s06_fake_key') then
                raise exception 'CP7_S06_FAKE_TRANSPORT_INPUT';
            end if;
            insert into pg_temp.s06_fake_requests(phone,body)
                values(params->>'phone',params->>'text') returning id + 9000000000 into request_id;
            insert into net._http_response(id,status_code,timed_out,content)
                values(request_id,200,false,'Message queued. You will receive it soon.');
            return request_id;
        end $$;
        revoke all on function net.http_get(text,jsonb,jsonb,integer) from public;
        grant usage on schema net to postgres;
        grant select on net._http_response to postgres;
        grant execute on function net.http_get(text,jsonb,jsonb,integer) to postgres;
    ''', prepare=False)


def read_requests(cur):
    return cur.execute('select phone,body from pg_temp.s06_fake_requests order by id').fetchall()
