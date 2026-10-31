-- a county cannot have more over-threshold systems than tested systems
select county_fips, systems_tested, systems_over_4ppt
from {{ ref('fct_pfas_exposure_county') }}
where systems_over_4ppt > systems_tested
