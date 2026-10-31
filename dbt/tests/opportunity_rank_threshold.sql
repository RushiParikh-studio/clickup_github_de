-- Ranked exactly when systems_tested >= var('min_systems_tested'); both ranks null or both set.
select county_fips, systems_tested, rank_national, rank_state
from {{ ref('fct_pfas_commercial_opportunity') }}
where (rank_national is not null) <> (systems_tested >= {{ var('min_systems_tested', 3) }})
   or (rank_national is null) <> (rank_state is null)
