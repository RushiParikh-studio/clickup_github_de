-- one row per county x NAICS
select county_fips, naics, count(*) as n
from {{ ref('stg_cbp_county_naics') }}
group by 1, 2
having count(*) > 1
