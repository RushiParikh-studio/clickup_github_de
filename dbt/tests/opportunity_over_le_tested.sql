select county_fips, systems_tested, systems_over_4ppt
from {{ ref('fct_pfas_commercial_opportunity') }}
where systems_over_4ppt > systems_tested
