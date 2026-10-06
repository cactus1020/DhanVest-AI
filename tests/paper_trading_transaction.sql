-- Disposable integration assertions; all test rows are rolled back.
begin;
do $$
declare u uuid := gen_random_uuid(); r uuid := gen_random_uuid(); c numeric; n bigint;
begin
 insert into auth.users(id) values(u);
 perform * from public.dhanvest_paper_order(u,r,'GP','buy',10,100,current_date,now());
 select cash into c from public.dhanvest_paper_accounts where user_id=u;
 if c <> 998997.50 then raise exception 'buy balance assertion failed'; end if;
 perform * from public.dhanvest_paper_order(u,r,'GP','buy',10,100,current_date,now());
 select count(*) into n from public.dhanvest_paper_trades where user_id=u;
 if n <> 1 then raise exception 'idempotency assertion failed'; end if;
 perform * from public.dhanvest_paper_order(u,gen_random_uuid(),'GP','sell',4,110,current_date,now());
 select cash into c from public.dhanvest_paper_accounts where user_id=u;
 if c <> 999436.40 then raise exception 'sell balance assertion failed'; end if;
 select quantity into n from public.dhanvest_paper_positions where user_id=u and symbol='GP';
 if n <> 6 then raise exception 'holdings assertion failed'; end if;
 begin
  perform * from public.dhanvest_paper_order(u,gen_random_uuid(),'GP','sell',7,110,current_date,now());
  raise exception 'oversell unexpectedly succeeded';
 exception when raise_exception then
  if sqlerrm <> 'insufficient_shares' then raise; end if;
 end;
 begin
  perform * from public.dhanvest_paper_order(u,gen_random_uuid(),'GP','buy',1000000,110,current_date,now());
  raise exception 'overspend unexpectedly succeeded';
 exception when raise_exception then
  if sqlerrm <> 'insufficient_cash' then raise; end if;
 end;
 select cash into c from public.dhanvest_paper_accounts where user_id=u;
 if c <> 999436.40 then raise exception 'failed order changed cash'; end if;
 if has_table_privilege('anon','public.dhanvest_paper_accounts','select')
 or has_table_privilege('authenticated','public.dhanvest_paper_trades','insert') then
  raise exception 'private table permissions assertion failed';
 end if;
end $$;
rollback;
