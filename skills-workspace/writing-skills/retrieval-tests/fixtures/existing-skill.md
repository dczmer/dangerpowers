---
name: deploying-with-acme
description: Use when deploying services to our infrastructure with the acme CLI — covers authentication, environment selection, deploys, rollbacks, and log inspection.
---

# Deploying with Acme

## Overview

The acme CLI is the only supported path for deploying services to staging and
production. It handles image promotion, config injection, and health gating in
one command.

## Prerequisites

- acme CLI v3.2 or newer (`acme version` to check)
- membership in the `deployers` group (request via #infra-access)
- a service manifest (`service.yaml`) at the repository root
- Docker daemon running locally for image builds

## Authentication

Authenticate once per day:

    acme login --sso

This opens the browser SSO flow and stores a token. CI pipelines use
`acme login --token "$ACME_CI_TOKEN"` instead — never use SSO tokens in CI.

Tokens expire after 12 hours. If any command returns `unauthenticated`, run
`acme login --sso` again.

## Environments

Two environments exist:

| Environment | Cluster     | Config source         |
|-------------|-------------|-----------------------|
| staging     | acme-stg-01 | config/staging.yaml   |
| production  | acme-prd-01 | config/production.yaml |

Always deploy to staging first. Production deploys refuse to run unless the
same image digest passed staging health checks within the last 24 hours.

## Deploying

1. Build and tag the image: `acme build .`
2. Deploy to staging: `acme deploy --env staging`
3. Watch the health gate: `acme status --env staging --follow`
4. Promote to production: `acme deploy --env production`
5. Confirm the production health gate: `acme status --env production --follow`

The health gate polls `/healthz` every 10 seconds and declares the deploy
healthy after 6 consecutive successes. A failed gate halts the deploy
automatically; it does not roll back.

## Blue-green deploys

Production supports blue-green mode for zero-downtime cutover:

    acme deploy --env production --strategy blue-green

Blue-green keeps the previous replica set running until the new set passes
the health gate, then shifts traffic atomically. Use it for user-facing
services. Workers and cron jobs use the default rolling strategy — blue-green
doubles their resource cost for no benefit.

A blue-green deploy that fails its gate stays parked: the new replicas keep
running without traffic. Tear them down with `acme deploy --abort` before
retrying, or the next deploy is rejected for exceeding the namespace quota.

## Configuration

acme reads `service.yaml` for deploy parameters:

    name: billing
    replicas: 3
    resources:
      cpu: 500m
      memory: 512Mi
    env:
      LOG_LEVEL: info

Rules:

- `replicas` must be at least 2 in production.
- Never put secrets in `env` — reference secret names with `secretRef`:

      envFrom:
        secretRef: billing-secrets

- Resource requests smaller than 250m/256Mi are rejected by the admission
  controller.
- Changing `name` creates a new service instead of updating the existing one;
  renames require `acme rename` so traffic is migrated.

## Rollback

Roll back the most recent deploy:

    acme rollback --env production

Roll back to a specific digest:

    acme rollback --env production --digest sha256:abc123

Rollback reuses the previous config snapshot; it never re-reads `service.yaml`
from disk.

## Logs

Tail deploy logs:

    acme logs --env staging --since 15m

Logs persist for 7 days. Use `--container` when the pod runs more than one
container; `acme logs` defaults to the first container and silently drops the
rest.

## Gotchas

- `acme deploy` is not idempotent: running it twice with the same digest
  creates two rollouts, and the second one wins the health gate.
- The CLI truncates status output at 80 columns; pipe to `cat` or use
  `--wide` to see full digests.
- `acme deploy` caches credentials in ~/.acme/creds.json — delete that file
  after rotating tokens, or the CLI keeps using the old token until it
  expires.
- `acme rollback` during an active health gate is rejected; wait for the gate
  to pass or fail first.

## Checklist

- [ ] Staging deploy healthy before promoting
- [ ] Same image digest promoted to production
- [ ] Production health gate passed
- [ ] Logs show no startup errors in the first 5 minutes
