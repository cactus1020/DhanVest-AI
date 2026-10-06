-- New verified records are stored separately from the preserved legacy import.
begin;
create table if not exists public.market_history (
  id bigint generated always as identity primary key,
  stock_id integer not null references public.stocks(id),
  date date not null,
  close_price numeric not null check(close_price>0),
  volume bigint not null check(volume>=0),
  source_verified boolean not null default true,
  source_url text not null,
  retrieved_at timestamptz not null default now(),
  unique(stock_id,date)
);
create table if not exists public.ingestion_runs (
  id bigint generated always as identity primary key,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null,
  session_date date,
  record_count integer not null default 0,
  error_code text
);
alter table public.market_history enable row level security;
alter table public.ingestion_runs enable row level security;
revoke all on public.market_history, public.ingestion_runs from anon, authenticated;
grant all on public.market_history, public.ingestion_runs to service_role;
grant usage, select on sequence public.market_history_id_seq, public.ingestion_runs_id_seq to service_role;
commit;
