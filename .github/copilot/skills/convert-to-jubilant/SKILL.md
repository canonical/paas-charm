---
name: convert-to-jubilant
description: >-
  Guide for converting paas-charm integration tests from pytest-asyncio
  (pytest-operator / python-libjuju) to the synchronous jubilant library.
  Use this skill when asked to migrate, convert, or update integration tests
  to use jubilant.
user-invocable: true
---

# Converting Integration Tests from pytest-asyncio to Jubilant

This guide covers how to convert `paas-charm` integration tests from the async
`pytest-asyncio` + `pytest-operator` (`OpsTest`) + `python-libjuju`
(`Model`/`Application`) stack to the synchronous `jubilant` library.

---

## 1. Remove Old Imports, Add New Ones

**Remove:**
```python
import asyncio
import json
import aiohttp
import pytest_asyncio
from juju.application import Application
from juju.errors import JujuError
from juju.model import Model
from pytest_operator.plugin import OpsTest
```

**Add:**
```python
import jubilant
import pytest
import requests
from tests.integration.types import App
```

---

## 2. Test Function Signatures

**Before:**
```python
async def test_something(
    ops_test: OpsTest,
    model: Model,
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
```

**After:**
```python
def test_something(
    flask_app: App,
    juju: jubilant.Juju,
    session_with_retry: requests.Session,
):
```

- Drop `async def` → `def`
- Replace `OpsTest`, `Model`, `Application` with `jubilant.Juju` and the `App` NamedTuple
- Replace `get_unit_ips` with `juju.status()` iteration (see §6)
- Replace direct `requests.get()` calls with the `session_with_retry` fixture (a
  `requests.Session` with automatic retry/backoff logic)

---

## 3. Fixtures: Scope and Decorator

**Before:**
```python
@pytest_asyncio.fixture(scope="module", name="my_app")
async def my_app_fixture(...):
    ...
    return app
```

**After:**
```python
@pytest.fixture(scope="module", name="my_app")
def my_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "myframework"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        config={"some-option": "value"},   # optional
    )
```

- Use `@pytest.fixture` (not `@pytest_asyncio.fixture`)
- Make it synchronous (`def`, not `async def`)
- For standard app deployment, delegate to the shared `generate_app_fixture()`
  helper in `tests/integration/conftest.py` — this handles deploy, postgresql
  integration, and waiting
- Use `yield from` (not `return`) so teardown works properly
- Framework-specific `conftest.py` files should only define fixtures truly unique
  to that framework (e.g., `update_config`, `traefik_app`, `cwd`)

---

## 4. The `juju` Session Fixture

A single session-scoped `juju` fixture is defined in
`tests/integration/conftest.py`. It supports three modes controlled by CLI
options:

```python
@pytest.fixture(scope="session")
def juju(request: pytest.FixtureRequest) -> jubilant.Juju:
    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        return jubilant.Juju()

    model = request.config.getoption("--model")
    if model:
        return jubilant.Juju(model=model)

    keep_models = cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        return juju
```

The CLI options `--model`, `--keep-models`, and `--use-existing` must be
registered in `tests/conftest.py`:
```python
parser.addoption("--keep-models", action="store_true", default=False)
parser.addoption("--model", action="store", default=None)
parser.addoption("--use-existing", action="store_true", default=False)
```

---

## 5. API Mapping: Deploying and Waiting

| Old (async)                                             | New (jubilant)                                                              |
|---------------------------------------------------------|-----------------------------------------------------------------------------|
| `model.deploy(...)`                                     | `juju.deploy(charm=..., app=..., resources=..., config=...)`                |
| `model.add_relation(a, b)`                              | `juju.integrate(a, b)`                                                      |
| `model.remove_relation(a, b)`                           | `juju.remove_relation(a, b)`                                                |
| `model.wait_for_idle(status="active")`                  | `juju.wait(lambda s: jubilant.all_active(s, *app_names))`                   |
| `model.wait_for_idle(status="blocked")`                 | `juju.wait(lambda s: s.apps[app_name].is_blocked)`                          |
| `app.set_config({"key": "val"})`                        | `juju.config(app_name, {"key": "val"})`                                     |
| `ops_test.juju("exec", "--unit", ...)`                  | `juju.cli("exec", "--unit", ...)`                                            |
| `await action.wait()` / `action.results`                | `task = juju.run(unit_name, action_name, params); task.results`             |

**Idempotency guards** — wrap `juju.deploy()` and `juju.integrate()` to handle
re-runs against existing models (`--use-existing`):

```python
try:
    juju.deploy(charm=charm_file, app=app_name, resources=resources, config=config)
except jubilant.CLIError as err:
    if "application already exists" not in err.stderr:
        raise err

try:
    juju.integrate(app_name, "postgresql-k8s:database")
except jubilant.CLIError as err:
    if "already exists" not in err.stderr:
        raise err
```

Use `error=jubilant.any_blocked` on `juju.wait()` to fail fast if an app enters
a blocked state:
```python
juju.wait(
    lambda status: status.apps[app_name].is_active,
    error=jubilant.any_blocked,
)
```

---

## 6. Accessing Unit Addresses

**Before:**
```python
for unit_ip in await get_unit_ips(app.name):
    response = requests.get(f"http://{unit_ip}:8000/", timeout=5)
```

**After:**
```python
status = juju.status()
for unit in status.apps[app.name].units.values():
    response = session_with_retry.get(f"http://{unit.address}:8000/", timeout=5)
```

Use `session_with_retry` instead of raw `requests.get()`. The session retries on
transient HTTP errors (5xx, connection resets) avoiding flaky tests while apps
are starting.

---

## 7. The `update_config` Fixture Pattern

Config-modifying tests use a fixture that saves/restores config around the test:

```python
@pytest.fixture(scope="function")
def update_config(juju: jubilant.Juju, request: pytest.FixtureRequest, my_app: App):
    app_name = my_app.name
    orig_config = juju.config(app_name)

    request_config = {k: str(v) for k, v in request.param.items()}
    juju.config(app_name, request_config)
    juju.wait(
        lambda status: status.apps[app_name].is_active or status.apps[app_name].is_blocked,
        successes=5,
        delay=10,
    )

    yield request_config

    # Teardown: restore original config
    restore_config = {k: str(v) for k, v in orig_config.items() if k in request_config}
    reset_config = [k for k in request_config if orig_config.get(k) is None]
    juju.config(app_name, restore_config, reset=reset_config)
```

Use it in tests with `indirect`:
```python
@pytest.mark.parametrize("update_config, expected", [...], indirect=["update_config"])
@pytest.mark.usefixtures("update_config")
def test_something(my_app: App, juju: jubilant.Juju, expected):
    ...
```

---

## 8. Parallel HTTP Requests (replacing `asyncio.gather` / `aiohttp`)

**Before:**
```python
async with aiohttp.ClientSession() as session:
    results = await asyncio.gather(*[session.get(url) for url in urls])
```

**After:**
```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(session_with_retry.get, url, timeout=5) for url in urls]
    results = [f.result() for f in futures]
```

---

## 9. Running Juju Actions

**Before:**
```python
action = await unit.run_action("create-superuser", email="test@example.com")
await action.wait()
password = action.results["password"]
```

**After:**
```python
unit_name = list(juju.status().apps[app.name].units.keys())[0]
task = juju.run(unit_name, "create-superuser", {"email": "test@example.com", "username": "test"})
password = task.results["password"]
```

---

## 10. Input Validation in Image Fixtures

All `--*-image` pytest options should raise immediately if missing (fail before
any resources are allocated):

```python
@pytest.fixture(scope="module", name="my_app_image")
def fixture_my_app_image(pytestconfig: Config):
    image = pytestconfig.getoption("--my-app-image")
    if not image:
        raise ValueError("the following arguments are required: --my-app-image")
    return image
```

---

## 11. Deploying Third-Party Apps (Traefik, Redis, Loki, etc.)

Use idempotent guards and `error=jubilant.any_blocked`:

```python
@pytest.fixture(scope="module", name="traefik_app")
def deploy_traefik_fixture(juju: jubilant.Juju, traefik_app_name: str, external_hostname: str):
    if not juju.status().apps.get(traefik_app_name):
        juju.deploy(
            "traefik-k8s",
            app=traefik_app_name,
            channel="edge",
            trust=True,
            config={"external_hostname": external_hostname, "routing_mode": "subdomain"},
        )
    juju.wait(
        lambda status: status.apps[traefik_app_name].is_active,
        error=jubilant.any_blocked,
    )
    return App(traefik_app_name)
```

---

## 12. The `App` Type

Replace all `Application` (from `juju.application`) with the lightweight `App`
NamedTuple from `tests/integration/types.py`:

```python
class App(NamedTuple):
    name: str
```

Tests reference the app name via `app.name` and get live unit data from
`juju.status()`.

---

## 13. Framework-Specific `conftest.py` Files

After migration, each framework's `conftest.py` should only contain fixtures
unique to that framework. Move the main app fixture to the central
`tests/integration/conftest.py` using `generate_app_fixture()`. Keep in the
framework-specific `conftest.py`:

- `cwd` autouse fixture (`os.chdir` into the charm's directory)
- `update_config` / `update_secret_config` fixtures
- Fixtures unique to that framework (e.g., `traefik_app` for Go ingress tests)

Remove from framework `conftest.py`: old `charm_file`, `*_app_image`, `*_app`
fixtures (these move to the central conftest or are replaced by
`generate_app_fixture()`).

---

## Conversion Checklist

When migrating a test file or conftest:

- [ ] Remove `async def` / `await` from all test functions and fixtures
- [ ] Replace `@pytest_asyncio.fixture` with `@pytest.fixture`
- [ ] Replace `Application` → `App`, `Model`/`OpsTest` → `jubilant.Juju`
- [ ] Replace `get_unit_ips` with `juju.status().apps[name].units.values()`
- [ ] Replace `requests.get()` with `session_with_retry.get()` (the session fixture)
- [ ] Replace `app.set_config()` with `juju.config(app.name, {...})`
- [ ] Replace `model.wait_for_idle()` with `juju.wait(lambda status: ...)`
- [ ] Replace `ops_test.juju(...)` with `juju.cli(...)`
- [ ] Replace `unit.run_action()` with `juju.run(unit_name, action, params)`
- [ ] Wrap `juju.deploy()` / `juju.integrate()` with `CLIError` idempotency guards
- [ ] Validate `--*-image` CLI options with `if not image: raise ValueError(...)`
- [ ] Use `yield App(app_name)` (not `return`) in app fixtures
- [ ] Move the main app fixture to `generate_app_fixture()` in the central conftest
- [ ] Register `--model`, `--keep-models`, `--use-existing` in `tests/conftest.py`
      if not already present
