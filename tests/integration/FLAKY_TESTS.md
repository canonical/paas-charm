# Flaky integration tests investigation

Tracking notes for flaky `integration_test.yaml` jobs. Data source: failed jobs of 5 of the last
30 PR runs (37908078001, 37846136142, 37802179610, 37787255639, 37694267857), read with
`gh run view --log-failed`.

## Findings

Failures are not specific to a test or a framework. Every parametrisation of the failing
spread job fails together, with `TimeoutError: wait timed out after 600s/1800s` from
`jubilant.wait`. In each case the wait never converges because a **third-party charm**, or the
Kubernetes cluster under it, is broken:

| Spread job | Runs | What was broken |
|------------|------|-----------------|
| `integrations_test_oauth` | 3 | `traefik-public` charm container in `crash loop backoff` while installing (run 37908078001); OIDC login redirect loop in run 37787255639 |
| `integrations_test_loki` | 1 | `postgresql-k8s` hook failures (`postgresql-pebble-ready`, `leader-elected`) then crash loop; `django-k8s` stuck on `missing integrations: postgresql` |
| `integrations_test_tracing` | 1 | `tempo-worker` `upgrade-charm` hook failed, then crash loop; `kratos` stuck waiting |
| `integrations_test_mongodb` | 1 | `mongodb-k8s` hook `upgrade-version-a-relation-created` failed, then crash loop |
| `integrations_test_mysql` | 1 | Same symptom class as above (timeout waiting for a dependency) |
| `integrations_test_ingress` | 1 | `flask-k8s` `peers-relation-created` failed: `dial tcp 10.152.183.1:443: i/o timeout` (Kubernetes API server unreachable from the unit) |
| `integrations_test_smtp` | 1 | `Failed to send information: please run connect() first` (smtp-integrator/mailcatcher not ready) |

Common pattern: a charm hook fails once (Kubernetes API `i/o timeout`, `httpx.ConnectTimeout`,
postgres not yet listening on its socket), the charm container then enters
`crash loop backoff` with exponentially growing back-off (up to 5m), and the test waits until its
timeout. Hooks that fail once are normally retried by Juju, so an extra-slow or overloaded runner
is the most likely trigger. The failed-job logs do not contain the Kubernetes event dump from the
spread `debug:` section, so resource pressure is not yet confirmed.

Several dependencies are not pinned to a revision (`postgresql-k8s` `14/stable`, `tempo`/`loki`
channels, `smtp-integrator` `latest/edge`, `mongodb`/`mysql` partly pinned), so upstream
changes can also cause failures.

## Likely root cause: hooks are not retried

`concierge.yaml` sets the Juju model default `automatically-retry-hooks: "false"` (added in the
charm-ci migration, #298). Every temporary test model inherits it, so a hook that fails once for a
transient reason (API server `i/o timeout`, postgres not yet listening) leaves the unit in `error`
for good and the test waits until its timeout. This matches every failure above. This branch
sets it to `"true"` so Juju retries failed hooks; CI on this PR is the validation.

## Local reproduction attempt

Built all artifacts with `opcli artifacts build` (about 1 hour) and ran
`opcli spread run -- integration-test-local:ubuntu-24.04:build/tests/integration/run:integrations_test_smtp`.
The LXD VM provisioning failed before any test ran: the VM root disk was 19 GB (the `disk: 50G`
backend option is not honoured in local mode), so the rawfile CSI driver reported
`ResourceExhausted: Not enough disk space` and the Juju controller pod never started.
Running locally needs a larger default LXD root disk.

## Not done

No test ran locally (see above). The `smtp` failure (`SMTPServerDisconnected` surfaced by the
Django app) is not explained by the retry setting and needs separate investigation.

## Next steps

1. Capture the spread `debug:` output (events, `describe pods`) for failed jobs to confirm or
   rule out resource pressure; consider a larger runner in `canonical/charm-ci`.
2. Pin the remaining unpinned third-party charm revisions.
3. Consider tolerating a transient `error` status for third-party apps in `jubilant.wait`, or
   job-level retry for infrastructure failures.
