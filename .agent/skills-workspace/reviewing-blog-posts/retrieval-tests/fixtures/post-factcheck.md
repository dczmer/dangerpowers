# Migrating to Postgres 17

Our platform team finished migrating the production fleet to Postgres
17 last quarter. The migration took three weekends and touched every
service that writes to the primary.

## Why we upgraded

The monorepo contains 240 packages, and our schema migrations run as
part of the CI pipeline for each one. Postgres 17 introduced
incremental backup, which lets us take small daily backups instead of
full weekly ones, and the JSON_TABLE function finally lets analysts
query JSON documents with plain SQL.
