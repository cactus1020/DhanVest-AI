-- DhanVest-only virtual trading. No real funds, broker orders or shared auth changes.
create table if not exists public.dhanvest_paper_accounts (
 user_id uuid primary key references auth.users(id),
 cash numeric(18,2) not null default 1000000 check(cash >= 0),
 initial_cash numeric(18,2) not null default 1000000,
 created_at timestamptz not null default now()
);
create table if not exists public.dhanvest_paper_positions (
 user_id uuid references public.dhanvest_paper_accounts(user_id),
 symbol text not null,
 quantity bigint not null check(quantity >= 0),
 cost_basis numeric(18,2) not null check(cost_basis >= 0),
 primary key(user_id,symbol)
);
create table if not exists public.dhanvest_paper_trades (
 id bigint generated always as identity primary key,
 user_id uuid not null references public.dhanvest_paper_accounts(user_id),
 request_id uuid not null,
 symbol text not null, side text not null check(side in ('buy','sell')),
 quantity bigint not null check(quantity > 0),
 price numeric(18,2) not null check(price > 0),
 fee numeric(18,2) not null, realized_pnl numeric(18,2) not null default 0,
 quote_date date not null, quote_retrieved_at timestamptz not null,
 created_at timestamptz not null default now(),
 unique(user_id,request_id)
);
alter table public.dhanvest_paper_accounts enable row level security;
alter table public.dhanvest_paper_positions enable row level security;
alter table public.dhanvest_paper_trades enable row level security;
revoke all on public.dhanvest_paper_accounts, public.dhanvest_paper_positions, public.dhanvest_paper_trades from anon, authenticated;
grant all on public.dhanvest_paper_accounts, public.dhanvest_paper_positions, public.dhanvest_paper_trades to service_role;
grant usage, select on sequence public.dhanvest_paper_trades_id_seq to service_role;

create or replace function public.dhanvest_paper_order(
 p_user uuid, p_request uuid, p_symbol text, p_side text, p_quantity bigint,
 p_price numeric, p_date date, p_retrieved timestamptz
) returns setof public.dhanvest_paper_trades language plpgsql security invoker set search_path=public as $$
declare a public.dhanvest_paper_accounts; pos public.dhanvest_paper_positions;
 total numeric; fee_amount numeric; removed_cost numeric; profit numeric := 0;
begin
 if p_side not in ('buy','sell') or p_quantity is null or p_quantity < 1 or p_quantity > 1000000
 or p_price is null or p_price <= 0 or p_price > 10000000 or p_symbol !~ '^[A-Z0-9_.-]{1,25}$'
 or p_date is null or p_retrieved is null then raise exception 'invalid_order'; end if;
 insert into dhanvest_paper_accounts(user_id) values(p_user) on conflict do nothing;
 select * into a from dhanvest_paper_accounts where user_id=p_user for update;
 if exists(select 1 from dhanvest_paper_trades where user_id=p_user and request_id=p_request) then
  if not exists(select 1 from dhanvest_paper_trades where user_id=p_user and request_id=p_request
   and symbol=p_symbol and side=p_side and quantity=p_quantity) then raise exception 'request_conflict'; end if;
  return query select * from dhanvest_paper_trades where user_id=p_user and request_id=p_request; return;
 end if;
 select * into pos from dhanvest_paper_positions where user_id=p_user and symbol=p_symbol;
 total := round(p_quantity * p_price,2); fee_amount := round(total * 0.0025,2);
 if p_side='buy' then
  if a.cash < total+fee_amount then raise exception 'insufficient_cash'; end if;
  update dhanvest_paper_accounts set cash=cash-total-fee_amount where user_id=p_user;
  insert into dhanvest_paper_positions(user_id,symbol,quantity,cost_basis)
  values(p_user,p_symbol,p_quantity,total+fee_amount)
  on conflict(user_id,symbol) do update set quantity=dhanvest_paper_positions.quantity+p_quantity,
   cost_basis=dhanvest_paper_positions.cost_basis+total+fee_amount;
 else
  if pos.quantity is null or pos.quantity < p_quantity then raise exception 'insufficient_shares'; end if;
  removed_cost := case when pos.quantity=p_quantity then pos.cost_basis else round(pos.cost_basis*p_quantity/pos.quantity,2) end;
  profit := total-fee_amount-removed_cost;
  update dhanvest_paper_positions set quantity=quantity-p_quantity,cost_basis=cost_basis-removed_cost where user_id=p_user and symbol=p_symbol;
  update dhanvest_paper_accounts set cash=cash+total-fee_amount where user_id=p_user;
 end if;
 return query insert into dhanvest_paper_trades(user_id,request_id,symbol,side,quantity,price,fee,realized_pnl,quote_date,quote_retrieved_at)
 values(p_user,p_request,p_symbol,p_side,p_quantity,p_price,fee_amount,profit,p_date,p_retrieved) returning *;
end $$;
revoke all on function public.dhanvest_paper_order(uuid,uuid,text,text,bigint,numeric,date,timestamptz) from public,anon,authenticated;
grant execute on function public.dhanvest_paper_order(uuid,uuid,text,text,bigint,numeric,date,timestamptz) to service_role;
