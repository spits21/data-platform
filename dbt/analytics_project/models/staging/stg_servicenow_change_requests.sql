with source as (
    select * from raw.supabase_change_requests
),
deduplicated as (
    select *,
        row_number() over (
            partition by id
            order by updated_at desc
        ) as row_num
    from source
    where id is not null
),
cleaned as (
    select
        id                                        as change_request_id,
        number                                    as change_request_number,
        title                                     as title,
        description                               as description,
        status                                    as status,
        risk                                      as risk,
        created_at::timestamp                     as created_at,
        updated_at::timestamp                     as updated_at
    from deduplicated
    where row_num = 1
)
select * from cleaned
