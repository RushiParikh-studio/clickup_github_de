export UV_PYTHON_PREFERENCE := managed
export UV_PYTHON_DOWNLOADS := automatic
export DBT_PROFILES_DIR := $(CURDIR)/dbt

.PHONY: ci
ci:
	uv run ruff check .
	uv run ruff format --check .
	uvx ty check
	bash scripts/check_boundary.sh
	uv run pytest -q
	cd dbt && uv run dbt build --target ci
