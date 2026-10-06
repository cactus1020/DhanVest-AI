-- Append-only announcement versions for point-in-time model research.
create table if not exists public.dhanvest_news_events (
 event_id text primary key,
 source_event_id text not null,
 title text not null check(length(title) between 1 and 1000),
 symbols text[] not null check(cardinality(symbols)>0),
 kind text not null check(kind in ('official','report','unverified')),
 published_date date not null,
 first_seen_at timestamptz not null,
 available_at timestamptz not null,
 availability_basis text not null check(availability_basis='prospective_capture'),
 source_url text not null,
 content_hash text not null,
 positive_keyword_count integer not null default 0,
 negative_keyword_count integer not null default 0,
 check(available_at=first_seen_at)
);
create index if not exists dhanvest_news_available_idx on public.dhanvest_news_events(available_at);
create table if not exists public.dhanvest_news_runs (
 id bigint generated always as identity primary key,
 started_at timestamptz not null default now(),
 finished_at timestamptz,
 status text not null check(status in ('running','complete','partial','failed')),
 company_count integer not null default 0,
 observed_versions integer not null default 0,
 failed_symbols text[] not null default '{}'
);
alter table public.dhanvest_news_events enable row level security;
alter table public.dhanvest_news_runs enable row level security;
revoke all on public.dhanvest_news_events,public.dhanvest_news_runs from anon,authenticated;
revoke all on public.dhanvest_news_events,public.dhanvest_news_runs from service_role;
grant select,insert on public.dhanvest_news_events to service_role;
grant select,insert,update on public.dhanvest_news_runs to service_role;
grant usage,select on sequence public.dhanvest_news_runs_id_seq to service_role;
