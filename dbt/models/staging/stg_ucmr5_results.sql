-- Phase 5: switch this to the real UCMR 5 extract; for now it reads the synthetic fixture seed.
select
    pwsid,
    state,
    contaminant,
    cast(value_ugl as double) as value_ugl,
    cast(collection_date as date) as collection_date,
    cast(value_ugl as double) > 0.004 as is_over_4ppt
from {{ ref('fixture_ucmr5_sample') }}
