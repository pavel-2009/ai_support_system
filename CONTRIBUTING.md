# Contributing

This document describes the development workflow for the current repository.

## 1. Requirements

### Backend

- Python 3.11+.
- Git.
- PostgreSQL and Redis for a full local environment, or Docker Compose.
- An OpenAI-compatible LLM endpoint for end-to-end AI flows.

The repository's Docker backend image uses Python 3.11. GitHub Actions currently tests with Python 3.12.

### Frontend

Frontend development uses the Node toolchain defined by `frontend/Dockerfile`. The production build uses Node 22 and nginx 1.27.

## 2. Local setup

Create a virtual environment:

```bash
cd app
python3.11 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Run the required infrastructure with Docker when convenient:

```bash
docker compose up -d postgres redis ollama
```

Apply migrations:

```bash
cd app
alembic upgrade head
```

Run the API:

```bash
cd app
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Run Celery separately:

```bash
cd app
PYTHONPATH=. celery -A app.celery.celery_app:celery_app worker --loglevel=info
```

## 3. Pre-commit

There is currently no committed `.pre-commit-config.yaml` in the repository. Do not document a pre-commit command as a required CI gate until the configuration is added.

For local quality checks, use the project's actual test suite and any configured linters/type checkers available in your development environment.

## 4. Testing

### All tests

```bash
cd app
pytest
```

### With coverage

```bash
cd app
pytest --cov=app --cov-report=term-missing
```

### Unit tests

```bash
cd app
pytest tests/unit
```

### E2E tests

```bash
cd app
pytest tests/e2e
```

The exact E2E dependency requirements should be checked before running an individual test file; some flows require infrastructure such as Redis/Celery.

### CI-equivalent test command

GitHub Actions currently runs:

```bash
pytest --cov=app --cov-report=term-missing --cov-report=xml --junitxml=pytest-report.xml
```

The CI environment sets:

- `DATABASE_URL=sqlite+aiosqlite:///./app.db`
- `JWT_SECRET_KEY=test-secret-key`
- `PYTHONPATH=.`
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`

CI also starts a Redis service and a Celery worker before running tests.

## 5. Performance / load testing

Performance tests are separate from the normal pytest suite.

The current Locust scenario is in:

```text
app/locustfile.py
```

It exercises:

- user registration/login;
- conversation creation;
- message submission;
- escalation polling;
- operator login;
- operator assignment;
- operator reply.

Example:

```bash
cd app
locust -f locustfile.py \
  --host http://localhost:8001 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --csv=tests/performance/results
```

For load tests that intentionally bypass the normal rate limit:

```bash
RATE_LIMIT_OVERRIDE=10000/minute docker compose up -d --build
```

Do not put multi-minute load tests into the ordinary pull-request CI path unless they are deliberately designed as a separate performance job.

## 6. Migrations

Alembic owns schema evolution.

Before modifying models, inspect the current revision:

```bash
cd app
alembic current
```

After changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe change"
```

Review the generated migration manually. Then apply it locally:

```bash
alembic upgrade head
```

Useful commands:

```bash
alembic history
alembic current
alembic upgrade head
alembic downgrade -1
```

Never rewrite a migration that has already been shared/applied. Add a new migration instead.

## 7. Ruff and Mypy

The current repository does not contain a committed `pyproject.toml`, `ruff.toml`, or `mypy.ini` configuration. Therefore Ruff and Mypy are not currently reproducible project-level gates.

If you have them installed locally, you may run them against the application:

```bash
cd app
ruff check .
mypy app
```

Treat their output as advisory until the repository adds pinned/configured tooling and CI gates.

Do not add a new formatting/type-checking rule in an unrelated feature PR without first agreeing on the project configuration.

## 8. Code organization rules

### Routers

Keep HTTP-specific concerns in routers:

- authentication dependencies;
- request/response schemas;
- status-code mapping;
- HTTP exceptions.

Do not put multi-step database workflows directly into routers.

### Services

Put application/business workflows in services.

Services should use the Unit of Work and repositories rather than manually committing transactions.

### Unit of Work

The Unit of Work owns transaction boundaries.

Repositories must not independently commit a transaction that belongs to the surrounding Unit of Work.

### State Machine

Conversation status changes must go through `ConversationStateMachine`.

If a new state or transition is needed:

1. update the state enum;
2. update `STATE_GRAPH`;
3. add/adjust state-machine methods;
4. add unit tests for allowed and forbidden transitions;
5. update `ARCHITECTURE.md`.

### Events

Domain events should be queued in the Unit of Work and published after a successful commit.

Event handlers must be resilient: a handler failure must be logged and must not pretend that an already committed DB transaction was rolled back.

### External I/O

Do not hold database sessions/transactions while waiting on external services such as an LLM.

For long-running background operations, prefer short DB read/write phases around the external call.

## 9. Branch naming

Use short descriptive branches based on the change type:

```text
feature/<short-description>
fix/<short-description>
refactor/<short-description>
test/<short-description>
docs/<short-description>
perf/<short-description>
chore/<short-description>
```

Examples:

```text
feature/operator-sla
fix/celery-read-transaction
perf/message-load-test
docs/architecture
```

Do not use vague names such as `new`, `changes` or `test2`.

## 10. Commit expectations

Keep commits focused.

Prefer:

```text
fix: release DB session before LLM request
test: cover invalid conversation transitions
docs: document Celery transaction boundaries
perf: add message throughput scenario
```

Avoid mixing unrelated refactors, formatting-only changes and behavioral changes in the same commit.

## 11. Pull request requirements

A PR should:

- explain the problem and the intended change;
- identify important architectural implications;
- include tests for changed behavior;
- include migration files for schema changes;
- update documentation when API/architecture/deployment behavior changes;
- avoid committing secrets or local `.env` files;
- keep unrelated changes out of scope.

Before opening a PR, run at minimum:

```bash
cd app
pytest
```

For changes involving migrations:

```bash
alembic upgrade head
```

For performance-sensitive changes, run the relevant Locust scenario separately and record the workload and environment.

## 12. PR checklist

- [ ] Tests pass locally.
- [ ] New behavior has tests.
- [ ] Existing tests were not weakened to hide failures.
- [ ] Migration added if the schema changed.
- [ ] State-machine tests updated if conversation transitions changed.
- [ ] Event behavior tested if domain events changed.
- [ ] API documentation updated if endpoints/contracts changed.
- [ ] README/ARCHITECTURE/DEPLOYMENT updated when applicable.
- [ ] No secrets committed.
- [ ] No unrelated refactor included.
- [ ] Performance impact considered for DB/Redis/Celery/LLM changes.

## 13. Documentation expectations

When architecture changes, update:

- `README.md` for user/developer-facing behavior;
- `ARCHITECTURE.md` for component boundaries and data flow;
- `DEPLOYMENT.md` for operational/configuration changes;
- `CONTRIBUTING.md` for workflow/tooling changes.

Documentation should describe the current implementation, not planned future architecture.

## 14. CI

The GitHub Actions workflow is the current automated quality gate.

It:

1. checks out the repository;
2. installs Python 3.12;
3. installs `app/requirements.txt`;
4. starts Redis;
5. waits for Redis;
6. starts a Celery worker;
7. waits for Celery readiness;
8. runs pytest with coverage and JUnit output;
9. uploads test/coverage/Celery artifacts;
10. writes coverage information to the GitHub Actions summary.

If CI fails, inspect the failed test first and reproduce it locally before changing application behavior.

## 15. Performance work

Performance changes should be evaluated using an explicit workload rather than a single local request measurement.

Record:

- concurrency/users;
- spawn rate;
- duration;
- endpoint mix;
- database/Redis/LLM configuration;
- p50/p95/p99 latency where relevant;
- request failure rate;
- Celery queue behavior;
- DB pool behavior.

Keep performance infrastructure and application correctness tests conceptually separate.
