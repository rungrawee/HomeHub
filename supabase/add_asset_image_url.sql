-- Run once in Supabase SQL Editor before importing CSV files with property images.
alter table public.assets
add column if not exists image_url text;
