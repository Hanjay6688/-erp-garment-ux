-- Closed preparation. No installer or application/native owning hook is open.
create schema cp7_global_nonpo_envelope authorization postgres;
revoke all on schema cp7_global_nonpo_envelope from public,anon,authenticated,service_role;

-- A future owning installer may seal only an ACTUAL accepted final parent and
-- the exact current catalog/relation/source observation. There is no seed row.
create table cp7_global_nonpo_envelope.profiles(
 id text primary key check(id~'^[0-9a-f]{64}$'),
 parent_head text not null check(parent_head~'^[0-9a-f]{40}$'),
 parent_tree text not null check(parent_tree~'^[0-9a-f]{40}$'),
 actual_parent_root_receipt jsonb not null check(jsonb_typeof(actual_parent_root_receipt)='object'),
 expected_catalogs jsonb not null check(jsonb_typeof(expected_catalogs)='array'and jsonb_array_length(expected_catalogs)>0),
 expected_relations jsonb not null check(jsonb_typeof(expected_relations)='array'and jsonb_array_length(expected_relations)>=42),
 native_authority_sha256 text not null check(native_authority_sha256~'^[0-9a-f]{64}$'),
 sealed_at timestamptz not null default statement_timestamp()
);
alter table cp7_global_nonpo_envelope.profiles enable row level security;
revoke all on cp7_global_nonpo_envelope.profiles from public,anon,authenticated,service_role;

create function cp7_global_nonpo_envelope.immutable_profile()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin raise exception 'CP7_GLOBAL_SEALED_PROFILE_IMMUTABLE_USE_NEW_REVIEWED_INSTALLATION';end $$;
alter function cp7_global_nonpo_envelope.immutable_profile()owner to postgres;
revoke all on function cp7_global_nonpo_envelope.immutable_profile()from public,anon,authenticated,service_role;
create trigger immutable_profile before update or delete on cp7_global_nonpo_envelope.profiles
 for each row execute function cp7_global_nonpo_envelope.immutable_profile();
