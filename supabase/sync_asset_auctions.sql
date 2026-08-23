-- Run once in Supabase SQL Editor before using the updated CSV importer.
-- The delete and insert happen in one database transaction.
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
    select
        p_asset_id,
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
