# Agua US data ingestion demo

Demo repository: a small dbt + DuckDB project with CI/CD that reports back to ClickUp.

## How DIN ids flow

1. Work starts from a ClickUp task with a custom id such as `DIN-7`.
2. Create the branch from the task so the name starts with the id: `DIN-7/short-name`.
3. Commit messages start with `DIN-7 ` (the `commit-msg` hook adds it from the branch name).
4. The PR title contains the id; the `link-check` workflow fails if no `DIN-n` is in the branch or title.
5. CI posts an upserted `[CI]` comment and sets task fields; merging to `main` runs `deploy`, which sets the environment and the task status.

ClickUp steps are skipped when `CLICKUP_TOKEN` is not set.

## Local run

```
uv sync
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
make ci            # ruff, ty, boundary check, pytest, fixtures -> dbt build --target ci
```

Python version is pinned in `.python-version`; change it there and run `uv sync`. The Makefile and `[tool.uv]` use the managed interpreter (`UV_PYTHON_PREFERENCE=managed`) so the exact `.python-version` pin wins over any system Python.

Copy `.env.example` to `.env` and fill values locally; never commit `.env`.

## Pipeline

```
extract/  (UCMR 5 zip, ZCTA-county file, CBP, ACS -> data/raw/*.parquet, all VARCHAR)
  -> extract/load.py  (raw schema in a DuckDB file; CI loads tests/fixtures/*.csv instead)
  -> dbt/  staging (stg_*) -> conformed (fct_pfas_exposure_county, dim_commercial_density_county)
           -> fct_pfas_commercial_opportunity (contract enforced)
  -> publish/top20.py  (docs/top20.md, docs/top20.json, docs/dashboard.html)
```

- `opportunity_score = share of tested systems over 4 ppt x ln(1 + target establishments)`; target establishments
  are NAICS 7211, 7225, 622, 311 and 3121 from the latest available County Business Patterns vintage.
- A system is a PWSID; it is over 4 ppt when any PFOA or PFOS result is at or above 0.004 ug/L. Systems reach
  counties through their ZIP codes and the 2020 ZCTA-county relationship file (largest land-area share per ZCTA).
  A system that serves several counties counts once in each of them.
- CI (`ci` workflow) builds only from the synthetic fixtures in `tests/fixtures/` (regenerate with
  `uv run python scripts/make_fixtures.py`). Full data runs only in `deploy` (environment `prod`).
- Locally: `make prod` runs the full chain; CBP and ACS need `CENSUS_API_KEY` in the environment or in a gitignored
  `.env`. `uv run python -m extract --only ucmr5,zcta` runs the keyless sources.
- `deploy` uploads `prod-state` (dbt manifest) and `published` (top 20 + dashboard); `dbt-docs` runs after a successful
  deploy and puts dbt docs plus the dashboard on GitHub Pages. A manual deploy can take a `task_id` input (`DIN-n`)
  so ClickUp reporting runs without a push.
- After publishing, `deploy` runs `publish/clickup_doc.py`, which replaces the content of the ClickUp Doc page
  `CLICKUP_PAGE_ID` (Doc `CLICKUP_DOC_ID`, both workflow constants) with `docs/top20.md` through the v3 Edit a Page
  endpoint, prefixed by a line naming the run and date. It needs `CLICKUP_TOKEN` and `CLICKUP_TEAM_ID`; if the token is
  missing or the API answers non-2xx it only emits a `::warning::`, so a Doc refresh never fails a deploy.

- Small-sample guard: only counties with at least `min_systems_tested` tested systems (dbt var, default 3) get
  `rank_national` / `rank_state`; others keep share and score with NULL ranks, and the top 20 is drawn from ranked
  counties. Override with `dbt build --vars '{min_systems_tested: 5}'`.
- Known gaps: systems whose ZIP codes have no ZCTA (PO-box ZIPs) drop out; `systems_tested` is not additive
  across counties; Connecticut rows from the 2020 ZCTA file use legacy counties that do not match the planning
  regions in ACS/CBP, so they carry no population or establishments (a warn-level dbt test lists them).
