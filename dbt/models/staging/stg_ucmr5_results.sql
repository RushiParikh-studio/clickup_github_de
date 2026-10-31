-- One row per UCMR 5 result. Over-threshold means a PFOA or PFOS result of 0.004 ug/L (4 ppt) or more.
select
    pwsid,
    state,
    size as system_size,
    facilityid as facility_id,
    samplepointid as sample_point_id,
    sampleid as sample_id,
    try_strptime(collectiondate, '%m/%d/%Y')::date as collection_date,
    contaminant,
    try_cast(mrl as double) as mrl_ugl,
    analyticalresultssign as result_sign,
    case when analyticalresultssign = '<' then null
         else try_cast(analyticalresultvalue as double) end as value_ugl,
    coalesce(analyticalresultssign = '=', false) as is_detect,
    contaminant in ('PFOA', 'PFOS') as is_pfoa_pfos,
    coalesce(
        contaminant in ('PFOA', 'PFOS')
        and analyticalresultssign <> '<'
        and try_cast(analyticalresultvalue as double) >= 0.004,
        false
    ) as is_over_4ppt
from {{ source('raw', 'ucmr5_all') }}
