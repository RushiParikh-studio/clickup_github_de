{{ config(contract={'enforced': true}) }}

-- Grain: county. Ranks counties where tested water systems exceed 4 ppt and target businesses cluster.
with zcta_names as (
    select county_fips, max(county_name) as county_name
    from {{ ref('stg_zcta_county') }}
    group by county_fips
),

joined as (
    select
        e.county_fips,
        coalesce(nullif(trim(split_part(a.county_name, ',', 1)), ''), z.county_name) as county_name,
        s.state_abbr as state,
        e.share_systems_over_4ppt,
        e.systems_tested,
        e.systems_over_4ppt,
        e.pop_county,
        coalesce(d.target_estab_total, 0)::bigint as target_estab_total
    from {{ ref('fct_pfas_exposure_county') }} as e
    left join {{ ref('dim_commercial_density_county') }} as d on e.county_fips = d.county_fips
    left join {{ ref('stg_acs_population') }} as a on e.county_fips = a.county_fips
    left join zcta_names as z on e.county_fips = z.county_fips
    left join {{ ref('state_fips') }} as s on e.state_fips = s.state_fips
),

scored as (
    select
        *,
        {{ opportunity_score('share_systems_over_4ppt', 'target_estab_total') }} as opportunity_score,
        systems_tested >= {{ var('min_systems_tested', 3) }} as is_ranked
    from joined
)

select
    county_fips::varchar as county_fips,
    county_name::varchar as county_name,
    state::varchar as state,
    share_systems_over_4ppt::double as share_systems_over_4ppt,
    systems_tested::bigint as systems_tested,
    systems_over_4ppt::bigint as systems_over_4ppt,
    pop_county::bigint as pop_county,
    target_estab_total::bigint as target_estab_total,
    opportunity_score::double as opportunity_score,
    -- Ranks only for counties with at least min_systems_tested tested systems; others get NULL.
    (case when is_ranked then row_number() over (
        partition by is_ranked
        order by opportunity_score desc, target_estab_total desc, county_fips
    ) end)::bigint as rank_national,
    (case when is_ranked then row_number() over (
        partition by is_ranked, state
        order by opportunity_score desc, target_estab_total desc, county_fips
    ) end)::bigint as rank_state
from scored
