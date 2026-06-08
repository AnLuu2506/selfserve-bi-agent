-- SILVER: cleaned, conformed, completed orders only, joined to product attributes
select
    ol.order_id,
    ol.customer_id,
    ol.region,
    ol.order_ts,
    date_trunc('month', ol.order_ts)::date as order_month,
    ol.sku,
    p.product_name,
    p.category,
    ol.qty,
    ol.unit_price,
    ol.line_revenue
from {{ ref('stg_order_lines') }} ol
left join {{ ref('stg_products') }} p using (sku)
where ol.status = 'completed'
