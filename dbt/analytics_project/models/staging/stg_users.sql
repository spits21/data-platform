with source as (
    select * from raw.supabase_users
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
        id                                        as user_id,
        email                                     as email,
        full_name                                 as full_name,
        title                                     as title,
        department_id                             as department_id,
        is_active::boolean                        as is_active,
        role                                      as role,
        metadata                                  as metadata,
        created_at::timestamptz                   as created_at,
        updated_at::timestamptz                   as updated_at
    from deduplicated
    where row_num = 1
)
select * from cleaned
