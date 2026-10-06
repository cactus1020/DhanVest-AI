-- Preserve receipts: the server needs read/insert, not update/delete privileges.
revoke all on public.dhanvest_paper_trades from service_role;
grant select,insert on public.dhanvest_paper_trades to service_role;
