# Retries Done Right

## Why retries matter

Distributed systems fail constantly, so clients need to retry failed
requests. Retries must be idempotent: replaying the same request must
not duplicate the effect. Without idempotency, a retried payment
charges the customer twice.

## Building the retry client

When we added retries to our HTTP client we started with exponential
backoff and jitter. Retries must be idempotent: replaying the same
request must not duplicate the effect. We also cap retries at three
attempts so a hard failure fails fast.

## Our Grafana dashboards

We track retry rate, backoff time, and error ratio on a dashboard the
whole team watches. Retries must be idempotent: replaying the same
request must not duplicate the effect. The alerts page whoever is on
call when the retry rate spikes.
