-- GOLD: monthly revenue by region and category (a self-serve mart)
select
    order_month,
    region,
    category,
    count(distinct order_id) as orders,
    sum(qty)                 as units,
    sum(line_revenue)        as revenue
from {{ ref('slv_order_lines') }}
group by 1, 2, 3
