# Reading Parquet from Python

See https://example.com/pyarrow-docs for the full API reference.

## Setup

Install pyarrow and pandas, then load a file:

```python
import pyarrow.parquet as pq

table = pq.read_table("/data/events/2026/09/partition_00000000000000000000000000000001_snappy.parquet")
df = table.to_pandas()
print(df.groupby("event_type").agg({"user_id": "nunique", "session_id": "nunique", "timestamp": ["min", "max"]}))
```

> Benchmark note from the author: on my machine the load above takes a little over two seconds for a two-gigabyte file with several hundred thousand rows
