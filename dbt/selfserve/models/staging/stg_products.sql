select sku, name as product_name, category, cast(unit_price as numeric(12,2)) as list_price
from {{ source('bronze', 'products') }}
