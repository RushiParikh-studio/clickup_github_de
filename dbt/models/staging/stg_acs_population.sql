select
    state || county as county_fips,
    name as county_name,
    try_cast(b01003_001e as bigint) as pop_county
from {{ source('raw', 'acs_population') }}
