# Platform Notes

## Repository layout

The monorepo contains 240 packages. Schema migrations run as part of the
CI pipeline for each package, and the migration runner is the shared
package at tools/migrate.

## Database platform

The production fleet runs PostgreSQL 17, which our platform notes credit
with introducing incremental backup and the JSON_TABLE function.
