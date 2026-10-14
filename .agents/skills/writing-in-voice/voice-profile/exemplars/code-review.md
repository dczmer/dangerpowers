IIUC this retry wrapper runs on every failed request, including requests where the server already processed the operation and only the response was lost in transit. i think that's a correctness problem for the POST path, because POST isn't idempotent in this service.

here's the sequence i'm worried about:

1. client sends `POST /orders`
2. server writes the order, then the connection drops before the response gets back
3. wrapper sees a network error and retries
4. server writes a second order

does the server dedupe on the request id? if it does then this is fine and i'm wrong. if not, i think we have two options:

- only retry idempotent methods (GET, PUT, DELETE) and let POST fail loud
- send an idempotency key on POST and have the server honor it -- more work, but it fixes the real problem

i'd lean toward the first one for this PR, since it's a small, contained change with predictable behavior, and we can file a separate ticket for the idempotency-key implementation.

**blocking:** the POST retry, until we know the dedupe answer.

**nit:** `max_attempts` defaults to 5 here but 3 in the README. probably just pick one.

not sure who owns the order handler these days, so i'll tag someone from that team to confirm the deduplication behavior before we merge anything that changes retry semantics.
