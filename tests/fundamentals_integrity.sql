-- Read-only release evidence; contains no unrelated application queries.
select
 (select count(*) from public.stocks) as stocks,
 (select count(*) from public.daily_data) as preserved_daily_rows,
 (select count(*) from public.factor_scores) as preserved_saved_scores,
 (select count(*) from public.dhanvest_fundamentals) as financial_versions,
 (select count(*) from public.dhanvest_fundamentals where roe is not null and debt_to_equity is not null) as reviewed_ratio_versions,
 has_table_privilege('anon','public.dhanvest_fundamentals','select') as anon_financial_access,
 has_table_privilege('service_role','public.dhanvest_fundamentals','delete') as server_financial_delete;
