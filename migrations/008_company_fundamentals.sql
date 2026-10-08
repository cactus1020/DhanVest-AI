-- Versioned quantitative facts, separate from preserved market history.
create table if not exists public.dhanvest_fundamentals (
 record_id text primary key,
 stock_id integer references public.stocks(id),
 symbol text not null, company_name text not null, sector text not null,
 period_end date not null, period_kind text not null check(period_kind in ('annual','quarterly')),
 eps numeric, nav_per_share numeric, net_profit_mn numeric,
 roe numeric, debt_to_equity numeric check(debt_to_equity>=0),
 roe_method text, debt_method text,
 source_url text not null, source_verified boolean not null,
 source_observed_at timestamptz not null,
 availability_basis text not null,
 benchmark_price numeric check(benchmark_price>0), price_date date,
 notes jsonb not null default '[]'::jsonb
);
create index if not exists dhanvest_fundamentals_stock_period_idx on public.dhanvest_fundamentals(stock_id,period_end desc);
alter table public.dhanvest_fundamentals enable row level security;
revoke all on public.dhanvest_fundamentals from public,anon,authenticated,service_role;
grant select,insert on public.dhanvest_fundamentals to service_role;
