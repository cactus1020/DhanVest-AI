-- Run this in the Supabase SQL Editor

-- 1. Create stocks table
create table if not exists public.stocks (
  id serial primary key,
  symbol text not null unique,
  name text,
  sector text
);

-- 2. Create daily_data table
create table if not exists public.daily_data (
  id serial primary key,
  stock_id integer references public.stocks(id) on delete cascade,
  date date not null,
  close_price numeric,
  volume integer,
  pe_ratio numeric,
  roe numeric,
  debt_to_equity numeric
);

-- Indexes for fast lookup
create index if not exists idx_daily_data_stock_id on public.daily_data(stock_id);
create index if not exists idx_daily_data_date on public.daily_data(date);

-- 3. Create factor_scores table
create table if not exists public.factor_scores (
  id serial primary key,
  stock_id integer references public.stocks(id) on delete cascade unique,
  quality_score numeric default 0.0,
  value_score numeric default 0.0,
  momentum_score numeric default 0.0,
  liquidity_score numeric default 0.0,
  composite_score numeric default 0.0,
  ai_explanation_bn text,
  ai_explanation_en text
);

-- Turn on Row Level Security and configure access
alter table public.stocks enable row level security;
alter table public.daily_data enable row level security;
alter table public.factor_scores enable row level security;

-- Create policies to allow public read access to factor_scores and stocks
create policy "Allow public read access to stocks" on public.stocks
  for select using (true);
  
create policy "Allow public read access to factor_scores" on public.factor_scores
  for select using (true);

-- Backend (service_role) bypasses RLS, so it can write data without policies.
