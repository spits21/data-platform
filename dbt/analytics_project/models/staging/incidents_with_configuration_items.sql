-- Join incidents with latest configuration item details
with incidents as (
    select * from {{ ref('stg_servicenow_incidents') }}
),
latest_config_items as (
    select *,
        row_number() over (
            partition by record_id
            order by snapshot_timestamp desc
        ) as row_num
    from {{ ref('stg_servicenow_configuration_items') }}
),
config_items as (
    select
        record_id,
        record_name
    from latest_config_items
    where row_num = 1
)
select
    i.*,
    c.record_name as configuration_item_name
from incidents i
left join config_items c on i.ci_id = c.record_id
