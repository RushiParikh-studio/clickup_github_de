-- Grain: county. Establishments per target NAICS (hotels 7211, restaurants 7225, hospitals 622,
-- food manufacturing 311, beverage manufacturing 3121). Missing county x NAICS counts as 0.
select
    c.county_fips,
    coalesce(sum(c.estab) filter (where c.naics = '7211'), 0)::bigint as hotels,
    coalesce(sum(c.estab) filter (where c.naics = '7225'), 0)::bigint as restaurants,
    coalesce(sum(c.estab) filter (where c.naics = '622'), 0)::bigint as hospitals,
    coalesce(sum(c.estab) filter (where c.naics = '311'), 0)::bigint as food_mfg,
    coalesce(sum(c.estab) filter (where c.naics = '3121'), 0)::bigint as bev_mfg,
    coalesce(sum(c.estab), 0)::bigint as target_estab_total
from {{ ref('stg_cbp_county_naics') }} as c
inner join {{ ref('stg_naics_targets') }} as t on c.naics = t.naics
group by c.county_fips
