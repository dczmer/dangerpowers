# The Outage That Taught Us About Timeouts

## The bug

Last Tuesday our checkout service fell over at peak traffic. A
downstream inventory service had grown slower over weeks, and our
checkout clients waited forever on responses that never came. Threads
piled up until the service ran out of them and stopped answering
health checks.

## The fix

We added a two-second timeout to every downstream call and a circuit
breaker that stops calling a service after five consecutive failures.
Once the breaker trips, requests fail fast and we serve a cached
fallback for inventory counts.

## The results

P99 checkout latency dropped from 40 seconds to 900 milliseconds
during the next traffic spike. No thread exhaustion since the deploy,
and the circuit breaker has tripped twice without customer impact.
