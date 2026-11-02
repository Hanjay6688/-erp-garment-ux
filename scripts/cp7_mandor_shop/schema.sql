-- Private facts only. No cash payment, kasbon, FG movement or wage posting.
-- This unactivated preparation has no installer or public command yet.
create schema cp7_mandor_shop authorization postgres;
revoke all on schema cp7_mandor_shop from public,anon,authenticated,service_role;

create table cp7_mandor_shop.contractor_accounts(
 contractor_id uuid primary key references erp.contractors(id),
 customer_id uuid not null unique references erp.customers(id),
 created_by uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 unique(contractor_id,customer_id)
);

-- Draft selection remains editable and has no receivable or payroll effect.
create table cp7_mandor_shop.draft_buyers(
 sale_id uuid primary key references erp.sales_headers(id),
 contractor_id uuid not null,
 customer_id uuid not null,
 selected_by uuid not null,
 selected_at timestamptz not null default statement_timestamp(),
 foreign key(contractor_id,customer_id)
  references cp7_mandor_shop.contractor_accounts(contractor_id,customer_id)
);
create index draft_buyers_contractor on cp7_mandor_shop.draft_buyers(contractor_id,sale_id);

-- Written with the existing Native sale POST, in that same transaction.
create table cp7_mandor_shop.sales(
 sale_id uuid primary key references erp.sales_headers(id),
 contractor_id uuid not null,
 customer_id uuid not null,
 contractor_name_at_post text not null check(length(btrim(contractor_name_at_post))>0),
 posted_by uuid not null,
 posted_at timestamptz not null default statement_timestamp(),
 foreign key(contractor_id,customer_id)
  references cp7_mandor_shop.contractor_accounts(contractor_id,customer_id),
 unique(sale_id,contractor_id)
);
create index sales_contractor on cp7_mandor_shop.sales(contractor_id,sale_id);

-- The Native header's contractor is checked before creating this identity.
create table cp7_mandor_shop.payroll_identities(
 payroll_id uuid primary key references erp.payroll_settlements(id),
 contractor_id uuid not null references erp.contractors(id),
 created_by uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 unique(payroll_id,contractor_id)
);
create index payroll_identities_contractor on cp7_mandor_shop.payroll_identities(contractor_id,payroll_id);

create table cp7_mandor_shop.requests(
 actor uuid not null,
 request_id uuid not null,
 action text not null,
 payload jsonb not null check(jsonb_typeof(payload)='object'),
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 response jsonb not null check(jsonb_typeof(response)='object'),
 created_at timestamptz not null default statement_timestamp(),
 primary key(actor,request_id)
);
create table cp7_mandor_shop.command_context(
 backend_pid integer not null,
 transaction_id bigint not null,
 actor uuid not null,
 request_id uuid not null,
 action text not null,
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 primary key(backend_pid,transaction_id)
);

-- Unconstrained numeric plus explicit cents check rejects fractional cents;
-- numeric(20,2) alone would round the input before a CHECK could inspect it.
create table cp7_mandor_shop.allocations(
 id uuid primary key,
 sale_id uuid not null,
 payroll_id uuid not null,
 contractor_id uuid not null,
 amount numeric not null check(amount>0 and amount<1000000000000000000 and amount=trunc(amount,2)),
 actor uuid not null,
 request_id uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 foreign key(sale_id,contractor_id)references cp7_mandor_shop.sales(sale_id,contractor_id),
 foreign key(payroll_id,contractor_id)references cp7_mandor_shop.payroll_identities(payroll_id,contractor_id),
 foreign key(actor,request_id)references cp7_mandor_shop.requests(actor,request_id)deferrable initially deferred,
 unique(id,sale_id,payroll_id,contractor_id,amount)
);
create index allocations_sale on cp7_mandor_shop.allocations(sale_id,id);
create index allocations_payroll on cp7_mandor_shop.allocations(payroll_id,id);
create index allocations_contractor on cp7_mandor_shop.allocations(contractor_id,id);

-- A settlement owns one actual noncash GL journal. It is not sales_payments.
create table cp7_mandor_shop.settlements(
 id uuid primary key,
 payroll_id uuid not null,
 contractor_id uuid not null,
 journal_id uuid not null unique references erp.journal_entries(id),
 total_amount numeric not null check(total_amount>0 and total_amount<1000000000000000000 and total_amount=trunc(total_amount,2)),
 economic_date date not null,
 book_date date not null check(book_date>=economic_date),
 actor uuid not null,
 request_id uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 foreign key(payroll_id,contractor_id)references cp7_mandor_shop.payroll_identities(payroll_id,contractor_id),
 foreign key(actor,request_id)references cp7_mandor_shop.requests(actor,request_id)deferrable initially deferred,
 unique(id,payroll_id,contractor_id)
);
create index settlements_payroll on cp7_mandor_shop.settlements(payroll_id,id);
create table cp7_mandor_shop.settlement_lines(
 settlement_id uuid not null,
 allocation_id uuid not null,
 sale_id uuid not null,
 payroll_id uuid not null,
 contractor_id uuid not null,
 amount numeric not null check(amount>0 and amount<1000000000000000000 and amount=trunc(amount,2)),
 primary key(settlement_id,allocation_id),
 foreign key(settlement_id,payroll_id,contractor_id)
  references cp7_mandor_shop.settlements(id,payroll_id,contractor_id),
 foreign key(allocation_id,sale_id,payroll_id,contractor_id,amount)
  references cp7_mandor_shop.allocations(id,sale_id,payroll_id,contractor_id,amount)
);
create index settlement_lines_invoice on cp7_mandor_shop.settlement_lines(sale_id,settlement_id);
create index settlement_lines_allocation on cp7_mandor_shop.settlement_lines(allocation_id,settlement_id);
create table cp7_mandor_shop.settlement_reversals(
 id uuid primary key,
 settlement_id uuid not null unique references cp7_mandor_shop.settlements(id),
 reversal_journal_id uuid not null unique references erp.journal_entries(id),
 reason text not null check(length(btrim(reason))>0),
 actor uuid not null,
 request_id uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 foreign key(actor,request_id)references cp7_mandor_shop.requests(actor,request_id)deferrable initially deferred
);

create table cp7_mandor_shop.allocation_events(
 id uuid primary key,
 allocation_id uuid not null references cp7_mandor_shop.allocations(id),
 ordinal integer not null check(ordinal>0),
 predecessor_id uuid references cp7_mandor_shop.allocation_events(id),
 kind text not null check(kind in('RESERVE','RELEASE','SETTLE','REOPEN','REVERSE')),
 settlement_id uuid references cp7_mandor_shop.settlements(id),
 reversal_id uuid references cp7_mandor_shop.settlement_reversals(id),
 actor uuid not null,
 request_id uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 unique(allocation_id,ordinal),
 check((ordinal=1)=(predecessor_id is null)),
 check((kind in('SETTLE','REOPEN','REVERSE'))=(settlement_id is not null)),
 check((kind in('REOPEN','REVERSE'))=(reversal_id is not null)),
 foreign key(actor,request_id)references cp7_mandor_shop.requests(actor,request_id)deferrable initially deferred
);
create index allocation_events_predecessor on cp7_mandor_shop.allocation_events(predecessor_id);
create index allocation_events_settlement on cp7_mandor_shop.allocation_events(settlement_id,allocation_id);
create index allocation_events_reversal on cp7_mandor_shop.allocation_events(reversal_id);

-- Current projection is written only by the event owner, never the browser.
create table cp7_mandor_shop.allocation_states(
 allocation_id uuid primary key,
 sale_id uuid not null,
 payroll_id uuid not null,
 contractor_id uuid not null,
 amount numeric not null check(amount>0 and amount<1000000000000000000 and amount=trunc(amount,2)),
 state text not null check(state in('RESERVED','SETTLED','RELEASED')),
 last_ordinal integer not null check(last_ordinal>0),
 last_event_id uuid not null unique references cp7_mandor_shop.allocation_events(id),
 settlement_id uuid references cp7_mandor_shop.settlements(id),
 check((state='SETTLED')=(settlement_id is not null)),
 foreign key(allocation_id,sale_id,payroll_id,contractor_id,amount)
  references cp7_mandor_shop.allocations(id,sale_id,payroll_id,contractor_id,amount)
);
create unique index allocation_states_one_active_invoice_payroll
 on cp7_mandor_shop.allocation_states(sale_id,payroll_id)where state in('RESERVED','SETTLED');
create index allocation_states_invoice on cp7_mandor_shop.allocation_states(sale_id,state,payroll_id);
create index allocation_states_payroll on cp7_mandor_shop.allocation_states(payroll_id,state,allocation_id);
create index allocation_states_contractor on cp7_mandor_shop.allocation_states(contractor_id,state,sale_id);

-- Live bridge to a Native draft deduction. RELEASE may remove this bridge
-- and its editable draft row while the immutable allocation/event history stays.
create table cp7_mandor_shop.deduction_links(
 allocation_id uuid primary key,
 sale_id uuid not null,
 payroll_id uuid not null,
 contractor_id uuid not null,
 amount numeric not null check(amount>0 and amount<1000000000000000000 and amount=trunc(amount,2)),
 deduction_id uuid not null unique references erp.payroll_deductions(id),
 foreign key(allocation_id,sale_id,payroll_id,contractor_id,amount)
  references cp7_mandor_shop.allocations(id,sale_id,payroll_id,contractor_id,amount)
);
create index deduction_links_payroll on cp7_mandor_shop.deduction_links(payroll_id,allocation_id);

create function cp7_mandor_shop.immutable_fact()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 raise exception 'CP7_MANDOR_SHOP_POSTED_FACT_IMMUTABLE_USE_LAWFUL_EVENT_OR_REVERSAL';
end $$;
alter function cp7_mandor_shop.immutable_fact()owner to postgres;
revoke all on function cp7_mandor_shop.immutable_fact()from public,anon,authenticated,service_role;

create trigger immutable_accounts before update or delete on cp7_mandor_shop.contractor_accounts
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_sales before update or delete on cp7_mandor_shop.sales
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_payroll_identities before update or delete on cp7_mandor_shop.payroll_identities
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_requests before update or delete on cp7_mandor_shop.requests
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_allocations before update or delete on cp7_mandor_shop.allocations
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_settlements before update or delete on cp7_mandor_shop.settlements
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_settlement_lines before update or delete on cp7_mandor_shop.settlement_lines
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_settlement_reversals before update or delete on cp7_mandor_shop.settlement_reversals
 for each row execute function cp7_mandor_shop.immutable_fact();
create trigger immutable_allocation_events before update or delete on cp7_mandor_shop.allocation_events
 for each row execute function cp7_mandor_shop.immutable_fact();

alter table cp7_mandor_shop.contractor_accounts enable row level security;
alter table cp7_mandor_shop.draft_buyers enable row level security;
alter table cp7_mandor_shop.sales enable row level security;
alter table cp7_mandor_shop.payroll_identities enable row level security;
alter table cp7_mandor_shop.requests enable row level security;
alter table cp7_mandor_shop.command_context enable row level security;
alter table cp7_mandor_shop.allocations enable row level security;
alter table cp7_mandor_shop.settlements enable row level security;
alter table cp7_mandor_shop.settlement_lines enable row level security;
alter table cp7_mandor_shop.settlement_reversals enable row level security;
alter table cp7_mandor_shop.allocation_events enable row level security;
alter table cp7_mandor_shop.allocation_states enable row level security;
alter table cp7_mandor_shop.deduction_links enable row level security;
revoke all on all tables in schema cp7_mandor_shop from public,anon,authenticated,service_role;
