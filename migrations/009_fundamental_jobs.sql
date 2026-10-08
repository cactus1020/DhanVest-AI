create table if not exists public.dhanvest_fundamental_runs (
 id bigint generated always as identity primary key,
 started_at timestamptz not null default now(), finished_at timestamptz,
 status text not null check(status in ('running','complete','partial','failed')),
 company_count integer not null default 0, observed_records integer not null default 0,
 failed_symbols text[] not null default '{}'
);
alter table public.dhanvest_fundamental_runs enable row level security;
revoke all on public.dhanvest_fundamental_runs from public,anon,authenticated,service_role;
grant select,insert,update on public.dhanvest_fundamental_runs to service_role;
grant usage,select on sequence public.dhanvest_fundamental_runs_id_seq to service_role;
