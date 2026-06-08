-- light typing/renaming only; no business logic here
select
    order_id,
    customer_id,
    region,
    cast(order_ts as timestamp)            as order_ts,
    status,
    sku,
    cast(qty as integer)                   as qty,
    cast(unit_price as numeric(12,2))      as unit_price,
    cast(qty as integer) * cast(unit_price as numeric(12,2)) as line_revenue
from {{ source('bronze', 'order_lines') }}
