begin;
create or replace function public.dhanvest_recent_market_history()
returns setof public.market_history
language sql stable security invoker
set search_path = public
as $$
  select recent.* from public.stocks s
  cross join lateral (
    select h.* from public.market_history h
    where h.stock_id=s.id order by h.date desc limit 61
  ) recent;
$$;
revoke all on function public.dhanvest_recent_market_history() from public, anon, authenticated;
grant execute on function public.dhanvest_recent_market_history() to service_role;
commit;
