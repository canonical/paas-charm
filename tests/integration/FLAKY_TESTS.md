# Flaky integration tests investigation

Tracking notes for flaky `integration_test.yaml` jobs. Data source: the last 30 PR runs, failures sampled from 5 of them.

## Observed failures

| Spread job | Failures seen | Symptom |
|------------|---------------|---------|
| `integrations_test_oauth` | 3 (runs 37908078001, 37802179610, 37787255639) | in run 37908078001 the `traefik-public` unit stuck in `error (crash loop backoff ... container=charm)` until `jubilant.wait` times out |
| `integrations_test_ingress` | 1 (run 37694267857) | to be triaged |
| `integrations_test_smtp` | 1 (run 37694267857) | to be triaged |
| `integrations_test_loki` | 1 (run 37846136142) | to be triaged |
| `integrations_test_tracing` | 1 (run 37802179610) | to be triaged |
| `integrations_test_mysql` | 1 (run 37802179610) | to be triaged |
| `integrations_test_mongodb` | 1 (run 37787255639) | to be triaged |

## Hypotheses

- OAuth: the third-party `traefik-public` charm container crash-loops while installing, which is
  an infrastructure/dependency flake rather than a paas-charm bug. Candidates: pin the traefik
  channel/revision, tolerate transient `error` status in `jubilant.wait`, or retry the job.
- Other jobs: check for shared causes (runner resource pressure, charm-hub downloads).

## Next steps

1. Pull logs for each failure above and fill in the symptom column.
2. Re-run failing jobs on this branch to measure the failure rate per test.
3. Apply targeted fixes (pins, retries, longer timeouts) in follow-up commits.
