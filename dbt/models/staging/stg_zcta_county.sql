-- One row per ZCTA: the county holding the largest land part (tie: smallest county FIPS).
select
    geoid_zcta5_20 as zcta5,
    geoid_county_20 as county_fips,
    namelsad_county_20 as county_name,
    try_cast(arealand_part as double) / nullif(try_cast(arealand_zcta5_20 as double), 0) as land_share
from {{ source('raw', 'zcta_county') }}
where geoid_zcta5_20 is not null and geoid_zcta5_20 <> ''
qualify row_number() over (
    partition by geoid_zcta5_20
    order by try_cast(arealand_part as double) desc nulls last, geoid_county_20
) = 1
