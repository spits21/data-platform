-- Join incidents with change request details
with incidents as (
    select * from {{ ref('stg_servicenow_incidents') }}
),
change_requests as (
    select
        change_request_id,
        change_request_number
    from {{ ref('stg_servicenow_change_requests') }}
)
select
    i.*,
    cr.change_request_number
from incidents i
left join change_requests cr on i.caused_by_change = cr.change_request_id
