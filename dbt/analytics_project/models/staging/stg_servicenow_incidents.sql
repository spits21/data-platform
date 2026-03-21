with source as (
    select * from raw.supabase_incidents
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
        id                                        as incident_id,
        number                                    as incident_number,
        short_description                         as short_description,
        description                               as description,
        reporter_id                               as reporter_id,
        assignee_id                               as assignee_id,
        priority                                  as priority,
        impact                                    as impact,
        urgency                                   as urgency,
        state                                     as state,
        ci_id                                     as ci_id,
        caused_by                                 as caused_by,
        caused_by_change                          as caused_by_change,
        created_at::timestamp                     as created_at,
        updated_at::timestamp                     as updated_at
    from deduplicated
    where row_num = 1
)
select * from cleaned