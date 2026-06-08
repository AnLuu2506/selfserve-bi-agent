-- GOLD: product leaderboard for "top SKUs" questions
select
    sku,
    product_name,
    category,
    sum(qty)          as units_sold,
    sum(line_revenue) as revenue
from {{ ref('slv_order_lines') }}
group by 1, 2, 3
order by revenue desc
