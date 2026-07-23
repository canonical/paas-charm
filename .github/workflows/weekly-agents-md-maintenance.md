---
emoji: 🤖
description: Weekly maintenance of AGENTS.md from merged PRs and source changes since the last run.
on:
  schedule:
    - cron: '0 6 * * 1'
  workflow_dispatch:
permissions:
  actions: read
  contents: read
  issues: read
  pull-requests: read
tools:
  github:
    mode: gh-proxy
    toolsets: [default]
safe-outputs:
  create-pull-request:
    allowed-files:
      - AGENTS.md
---

# Weekly AGENTS.md Maintenance

## Task

Maintain `AGENTS.md` so it stays accurate and current.

1. Identify the baseline time:
   - Find the previous successful run of this workflow on the default branch.
   - Use that run's creation time as the baseline.
   - If no previous successful run exists, use the last 7 days.
2. Collect changes since the baseline:
   - List pull requests merged into the default branch in that window.
   - List source files changed in that window (focus on code and configuration files, not generated files).
3. Update `AGENTS.md`:
   - If it does not exist, create it.
   - Summarize important behavior, architecture, workflows, and ownership signals reflected by merged PRs and source changes.
   - Keep the document concise, factual, and repository-specific.
4. Create a pull request only when `AGENTS.md` content changes.

## Safe Outputs

- Use `create-pull-request` when `AGENTS.md` is added or updated.
- Use `noop` with a short explanation when there are no relevant merged PRs, no relevant source changes, or no net change to `AGENTS.md`.
