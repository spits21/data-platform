with application_roles as (
    select * from {{ ref('stg_application_roles') }}
),
users as (
    select * from {{ ref('stg_users') }}
),
joined as (
    select
        application_roles.role_id,
        application_roles.role_name,
        users.user_id,
        users.email,
        users.full_name,
        users.title,
        users.department_id,
        users.is_active,
        users.role,
        users.metadata,
        users.created_at,
        users.updated_at
    from application_roles
    inner join users
        on application_roles.user_id = users.user_id
)
select * from joined
