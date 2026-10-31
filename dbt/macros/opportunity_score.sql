{#-
  Territory opportunity score: share of tested systems over 4 ppt, weighted by the log of the
  number of target businesses in the county. ln(1 + n) damps very large counties.
  A missing establishment count is treated as 0 (score 0 when share is present);
  a missing share gives a missing score (never a fake 0).
-#}
{% macro opportunity_score(share, estab) %}({{ share }} * ln(1 + coalesce({{ estab }}, 0)))
{%- endmacro %}
