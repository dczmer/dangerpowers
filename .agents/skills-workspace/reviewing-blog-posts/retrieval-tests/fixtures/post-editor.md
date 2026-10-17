# Tuning Our Postgres Pool

> EDITOR: Is the 50ms figure still up to date? Confirm it or update it.

Our API servers talk to Postgres through a connection pool sized at
twenty connections per node. At that size the average query wait is
around 50ms under normal load.

> EDITOR: The middle section feels too long — can you tighten it up?

When we raised the pool to two hundred connections per node, throughput
barely moved. The database CPU was already saturated, so extra waiting
connections just queued. We settled on forty connections per node as
the sweet spot for our hardware.

## Takeaways

Pool sizing cannot fix a database that is already the bottleneck.
Measure database CPU before adding connections.
