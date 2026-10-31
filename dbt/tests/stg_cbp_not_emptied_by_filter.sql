-- Fails when CBP raw rows exist but the size/legal-form filter removed all of them.
select 1 as emptied
where (select count(*) from {{ ref('stg_cbp_county_naics') }}) = 0
  and (select count(*) from {{ source('raw', 'cbp_county_naics') }}) > 0
