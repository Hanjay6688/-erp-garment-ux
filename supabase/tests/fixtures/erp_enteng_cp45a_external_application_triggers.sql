\set ON_ERROR_STOP on

set client_min_messages=warning;

create trigger trg_cp45_guard_last_owner_auth_delete before delete on auth.users for each row execute function erp.guard_last_owner_auth_delete();
