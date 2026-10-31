-- All-sizes, all-legal-forms rows only. Suppressed employment (flag D or non-numeric) is NULL.
select
    state || county as county_fips,
    naics2017 as naics,
    naics2017_label as naics_label,
    name as county_name,
    try_cast(estab as bigint) as estab,
    case when emp_n = 'D' then null else try_cast(emp as bigint) end as emp
from {{ source('raw', 'cbp_county_naics') }}
-- EMPSZES/LFO may be absent (NULL) in some API responses; treat NULL as the all-rows value.
where coalesce(empszes, '001') = '001' and coalesce(lfo, '001') = '001'
