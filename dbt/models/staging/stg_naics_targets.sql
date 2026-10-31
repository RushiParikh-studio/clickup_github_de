select
    cast(naics as varchar) as naics,
    label
from {{ ref('naics_targets') }}
