-- Fable local stand-in for the Supabase platform pieces the CP2 restore references (PG16, NOT the hosted image).
create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
create schema extensions; create schema vault; create schema auth; create schema storage; create schema cron; create schema net;
create extension pgcrypto with schema extensions; create extension "uuid-ossp" with schema extensions; create extension pg_stat_statements with schema extensions;
create table auth.users(id uuid primary key, email text, raw_app_meta_data jsonb, raw_user_meta_data jsonb, created_at timestamptz default now());
create table auth.identities(id uuid primary key, user_id uuid);
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
create function auth.jwt() returns jsonb language sql stable as $$select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb$$;
create function auth.role() returns text language sql stable as $$select coalesce(auth.jwt()->>'role','')$$;
create table storage.buckets(id text primary key, name text, public boolean default false, created_at timestamptz default now(), updated_at timestamptz default now(), owner uuid, file_size_limit bigint, allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(), bucket_id text, name text, metadata jsonb, created_at timestamptz default now());
create table cron.job(jobid bigserial primary key, schedule text not null, command text not null, nodename text default 'localhost', nodeport int default 5432, database text default current_database(), username text default current_user, active boolean default true, jobname text);
create function cron.schedule(job_name text, schedule text, command text) returns bigint language sql as $$insert into cron.job(jobname,schedule,command) values(job_name,schedule,command) returning jobid$$;
create function cron.unschedule(job_id bigint) returns boolean language sql as $$delete from cron.job where jobid=job_id returning true$$;
create function net.http_post(url text, body jsonb default '{}', params jsonb default '{}', headers jsonb default '{}', timeout_milliseconds int default 5000) returns bigint language sql as $$select 0::bigint$$;
create schema supabase_migrations;
create table supabase_migrations.schema_migrations(version text primary key, statements text[], name text, created_by text, idempotency_key text);
