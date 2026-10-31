-- Grain: county. A system (PWSID) is tested if it has any PFOA or PFOS result and over 4 ppt if
-- any such result is 0.004 ug/L or more. A system serving several counties counts once in each.
with systems as (
    select
        pwsid,
        bool_or(is_over_4ppt) as is_over
    from {{ ref('stg_ucmr5_results') }}
    where is_pfoa_pfos
    group by pwsid
),

system_county as (
    select distinct
        z.pwsid,
        c.county_fips
    from {{ ref('stg_ucmr5_zip') }} as z
    inner join {{ ref('stg_zcta_county') }} as c on z.zip5 = c.zcta5
),

by_county as (
    select
        sc.county_fips,
        count(*) as systems_tested,
        count(*) filter (where s.is_over) as systems_over_4ppt
    from system_county as sc
    inner join systems as s on sc.pwsid = s.pwsid
    group by sc.county_fips
)

select
    b.county_fips,
    left(b.county_fips, 2) as state_fips,
    b.systems_tested::bigint as systems_tested,
    b.systems_over_4ppt::bigint as systems_over_4ppt,
    b.systems_over_4ppt::double / b.systems_tested as share_systems_over_4ppt,
    a.pop_county
from by_county as b
left join {{ ref('stg_acs_population') }} as a on b.county_fips = a.county_fips
