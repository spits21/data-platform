with source as (
    select * from raw.supabase_application_roles
),
cleaned as (
    select
        id                                        as role_id,
        name                                      as role_name,
        users_id                                  as user_id
    from source
    where id is not null
)
select * from cleaned
