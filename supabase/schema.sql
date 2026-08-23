-- Initial schema for the LED asset search project.
-- Run this file once in the Supabase SQL Editor.

create table if not exists public.assets (
    id uuid primary key default gen_random_uuid(),
    source_key text not null unique,
    lot text,
    sequence text,
    case_number text,
    asset_type text,
    deed_number text,
    rai text,
    ngan text,
    square_wah text,
    area_detail text,
    price numeric(15, 2),
    price_final numeric(15, 2),
    deposit_amount numeric(15, 2),
    tambon text,
    amphur text,
    province text,
    owner_name text,
    officer_name text,
    sale_location text,
    location text,
    image_url text,
    detail_url text,
    raw_detail text,
    source_updated_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.auctions (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    auction_round integer,
    auction_date date,
    status text,
    created_at timestamptz not null default now(),
    unique (asset_id, auction_round, auction_date)
);

create index if not exists assets_province_amphur_idx
    on public.assets (province, amphur);

create index if not exists assets_deed_number_idx
    on public.assets (deed_number);

create index if not exists assets_price_final_idx
    on public.assets (price_final);

create index if not exists auctions_date_idx
    on public.auctions (auction_date);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists assets_set_updated_at on public.assets;
create trigger assets_set_updated_at
before update on public.assets
for each row execute function public.set_updated_at();

-- Keep tables private until the API authentication and RLS policies are ready.
alter table public.assets enable row level security;
alter table public.auctions enable row level security;

-- Keep existing databases compatible when this schema is run again.
alter table public.assets add column if not exists image_url text;

-- Atomically keep auction history identical to the latest scraper result.
create or replace function public.sync_asset_auctions(
    p_asset_id uuid,
    p_auctions jsonb
)
returns integer
language plpgsql
security invoker
set search_path = public
as $$
declare
    synced_count integer := 0;
begin
    delete from public.auctions where asset_id = p_asset_id;
    insert into public.auctions (asset_id, auction_round, auction_date, status)
    select p_asset_id,
           (item ->> 'auction_round')::integer,
           (item ->> 'auction_date')::date,
           coalesce(item ->> 'status', '')
    from jsonb_array_elements(coalesce(p_auctions, '[]'::jsonb)) as item;
    get diagnostics synced_count = row_count;
    return synced_count;
end;
$$;

revoke execute on function public.sync_asset_auctions(uuid, jsonb)
from public, anon, authenticated;
grant execute on function public.sync_asset_auctions(uuid, jsonb)
to service_role;
