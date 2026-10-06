-- Private research ledger: collecting evidence does not enable public forecasts.
create table if not exists public.dhanvest_shadow_predictions (
 id uuid primary key,
 stock_id bigint not null references public.stocks(id),
 model_version text not null,
 horizon_sessions integer not null check(horizon_sessions in (2,40)),
 predicted_at timestamptz not null,
 feature_cutoff timestamptz not null check(feature_cutoff<=predicted_at),
 base_date date not null,
 base_price numeric not null check(base_price>0),
 up_probability numeric not null check(up_probability between 0 and 1),
 input_signature text not null,
 status text not null default 'research_only' check(status='research_only'),
 unique(stock_id,model_version,horizon_sessions,input_signature)
);
create table if not exists public.dhanvest_shadow_outcomes (
 prediction_id uuid primary key references public.dhanvest_shadow_predictions(id),
 outcome_date date not null,
 outcome_price numeric not null check(outcome_price>0),
 return_fraction numeric not null,
 actual_direction text not null check(actual_direction in ('up','flat','down')),
 evaluated_at timestamptz not null default now(),
 source_url text not null
);
alter table public.dhanvest_shadow_predictions enable row level security;
alter table public.dhanvest_shadow_outcomes enable row level security;
revoke all on public.dhanvest_shadow_predictions,public.dhanvest_shadow_outcomes from anon,authenticated;
revoke all on public.dhanvest_shadow_predictions,public.dhanvest_shadow_outcomes from service_role;
grant select,insert on public.dhanvest_shadow_predictions,public.dhanvest_shadow_outcomes to service_role;
