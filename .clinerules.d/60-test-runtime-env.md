# 60 — Test and Runtime Environment

## Test invocation (canonical)

```bash
PYTHONPATH=src python3 -m pytest tests/ -x -q
```

## Targeted smoke run

For focused validation after changes:

```bash
PYTHONPATH=src python3 -m pytest tests/test_<module>.py -x -q
```

For specific test functions:

```bash
PYTHONPATH=src python3 -m pytest tests/test_<module>.py::test_function_name -x -q
```

## Required environment

- `.env` must be present (copy `.env.example`, set `ATHLETE_ID`)
- Do not run tests that require API keys without explicit user confirmation
- `pyenv` / `.python-version` controls the interpreter — do not override
- Workspace-dependent tests require a valid `runtime/` tree

## Lint and typecheck

```bash
./scripts/run_lint.sh
./scripts/run_typecheck.sh
```

For targeted linting:

```bash
./scripts/run_lint.sh src/rps/specific_module
```

## Compile check

```bash
python3 -m py_compile $(git ls-files '*.py')
```

## Docker / containerized tests

If tests require Docker:

```bash
docker-compose up -d
PYTHONPATH=src python3 -m pytest tests/ -x -q
docker-compose down
```

Do not leave stale containers running after validation.

## Test discipline

- Add a reproducing test before fixing a bug.
- Do not commit fixes without test coverage unless explicitly impossible.
- If a test requires external state (API, workspace), document the setup in the test docstring.
