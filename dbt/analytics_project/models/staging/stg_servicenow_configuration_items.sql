-- models/staging/stg_servicenow_configuration_items.sql
with source as (
    select * from raw.supabase_configuration_items_snapshots
),
deduplicated as (
    select *,
        row_number() over (
            partition by id, date(snapshot_timestamp)    -- deduplicate within each day
            order by updated_at desc                     -- keep most recent update per day
        ) as row_num
    from source
    where id is not null
),
cleaned as (
    select
        id                  as record_id,
        name                as record_name,
        status              as status,
        created_at::timestamp as created_at,
        updated_at::timestamp as updated_at,
        date(snapshot_timestamp) as snapshot_date,
        snapshot_timestamp
    from deduplicated
    where row_num = 1
)
select * from cleaned
