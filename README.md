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
make ci            # ruff, pytest, dbt build --target ci
```

Copy `.env.example` to `.env` and fill values locally; never commit `.env`.
