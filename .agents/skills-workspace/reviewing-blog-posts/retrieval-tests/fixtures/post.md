# Shipping Our New Cache Layer

## why we built it

Our API was slow, and we recieved reports that pages took seconds to
load. We measured latency, throughput and error rate before and after
the change. Full benchmark details are at https://example.com/benchmarks
if you want to dig in.

## How it works

The cache sits in front of the database and cuts repeat queries for
frequently-read rows.
