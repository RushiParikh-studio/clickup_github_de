export UV_PYTHON_PREFERENCE := managed
export UV_PYTHON_DOWNLOADS := automatic
export DBT_PROFILES_DIR := $(CURDIR)/dbt

.PHONY: ci fixtures dbt-ci extract prod publish

ci:
	uv run ruff check .
	uv run ruff format --check .
	uvx ty check
	bash scripts/check_boundary.sh
	uv run pytest -q
	$(MAKE) dbt-ci

# Load committed synthetic fixtures into dbt/target/ci.duckdb (raw schema).
fixtures:
	uv run python scripts/load_fixtures.py

dbt-ci: fixtures
	cd dbt && uv run dbt build --target ci

# Full data: UCMR 5 + ZCTA need no key; CBP + ACS need CENSUS_API_KEY (env or gitignored .env).
extract:
	uv run python -m extract --out data/raw

prod: extract
	uv run python -m extract.load --src data/raw --db dbt/target/prod.duckdb
	cd dbt && uv run dbt build --target prod
	$(MAKE) publish

publish:
	uv run python -m publish.top20 --db dbt/target/prod.duckdb --out docs
