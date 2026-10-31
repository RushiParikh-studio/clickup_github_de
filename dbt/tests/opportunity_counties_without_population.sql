{{ config(severity='warn') }}
-- Warn (not fail): counties with no ACS population match. Expected for Connecticut, where the
-- 2020 ZCTA-county file uses legacy counties and ACS/CBP use planning regions; those rows get no
-- population and zero target establishments.
select county_fips, county_name, state
from {{ ref('fct_pfas_commercial_opportunity') }}
where pop_county is null
