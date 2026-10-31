-- dim_commercial_density_county hard-codes one column per target NAICS; fail if the seed grows
select naics
from {{ ref('stg_naics_targets') }}
where naics not in ('7211', '7225', '622', '311', '3121')
