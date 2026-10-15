# Ubuntu 26.04 tutorial walkthroughs

The six manual Spread tasks in `docs/tutorial/code-26-04/` exercise the same
commands included in the published tutorials. They are separate from the
library's concierge-based integration tests and are never selected by default.

## Fast PR checks

Run `tox -e tutorial` to check all six tutorials' included files and snippet
markers, shell syntax, framework configuration, versions, and the retry helper.
The existing `Tests` pull-request workflow runs these checks on a hosted
Ubuntu runner without secrets, VM allocation, snap installation or deployments.
They are consistency checks, **not** end-to-end walkthrough results. The existing
unit and integration jobs remain unchanged.

## Opt-in live walkthroughs

Provision a **disposable Ubuntu 26.04 guest** separately, with 4 CPUs, 8 GB RAM,
and a 50 GB disk, matching the tutorials. The guest needs a reachable SSH server,
an `ubuntu` user with password authentication and passwordless sudo, snapd, and
outbound network access. Use a fresh guest for each framework. Spread does not
create or delete this guest. The tests install snaps, initialize LXD and
Kubernetes, create and destroy a Juju controller, and remove the Kubernetes snap.
Do not point them at a workstation or a shared cluster.

From the repository root, with `opcli` and Spread installed:

```bash
# List only; no guest is contacted.
tox -e tutorial-list

# Run one framework in an already-provisioned guest.
export TUTORIAL_HOST=192.0.2.10
opcli spread run -- -v -pass '<guest SSH password>' \
  tutorial:ubuntu-26.04:docs/tutorial/code-26-04/flask
```

Replace `flask` with `django`, `expressjs`, `fastapi`, `go`, or `spring-boot`.
The default `tutorial-list` entrypoint lists only Django, Express, FastAPI, Flask,
and Go. Run those five on separate fresh guests and exclude `spring-boot`.
To list all six explicitly, use
`opcli spread run -- -list tutorial:ubuntu-26.04:docs/tutorial/code-26-04/`.
Spring Boot's tutorial and task are retained,
but incremental rock builds currently encounter an upstream Java symlink issue.

The suite installs Juju `3.6/stable`, Canonical Kubernetes
`1.34-classic/stable`, and Rockcraft and Charmcraft `latest/edge`. Its registry
and cluster setup are the shared files in `docs/reuse/tutorial/`. The small
`tools/retry` helper supports the task files' `-n` and `--wait` options without
depending on Charmcraft's external snap testing tools.

Each framework task creates its tiny `paas-config.yaml` directly, using the
same commands included in its tutorial. Shared Go/Express migration snippets
live in `docs/reuse/tutorial/fixtures/`; the suite's `prepare-each` stages these
under their original filenames. Framework-specific app code and charm
configuration remain separate.

Do not add early builder cleanup or silently increase guest capacity to conceal
storage failures. Retained builders, the controller's storage, the 8 GiB registry
claim, and PostgreSQL can exhaust a 50 GB guest. Record those failures and keep
the logs. Runtime permission simulations or upstream Java workarounds do not
belong in the tutorial source or fixtures.

Automatic end-to-end CI is deliberately not enabled: the current reusable
integration workflow provisions a different concierge-based environment and
does not supply these standalone Ubuntu 26.04 guests. Enabling automatic live
runs requires a separate runner/provisioning and credential decision. No
credentials should be committed; keep the SSH password out of saved logs.
