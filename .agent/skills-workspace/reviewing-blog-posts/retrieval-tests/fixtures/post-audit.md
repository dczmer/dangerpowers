# How We Cut p99 Latency in Half

## What we changed

We added a write-behind cache in front of the sessions store. This made
it much faster, and we saw the difference on the first day. It batches
writes and flushes them asynchronously, so callers stop waiting on the
database round trip.

## Why write-behind is tricky

Write-behind caching keeps the cache authoritative and flushes writes
to the backing store later. Readers can observe data that has not been
durably persisted yet, and a crash between flush intervals loses
acknowledged writes unless the flush log is durable. Understanding the
failure window requires reasoning about the interplay of the flush
interval, the durability of the log, and the recovery procedure.

## Rollout notes

We rolled the cache out service by service over two weeks. This went
smoothly and we did not have to roll anything back.
