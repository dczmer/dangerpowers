# Moving thumbnail generation off the upload path

TLDR: uploads are slow because we resize every image inline before we return the response. I want to push that work onto a queue and let a worker do it, so the upload returns as soon as the original file is stored.

## Background

Right now the upload handler does four things in a row: validates the file, stores the original, generates three thumbnail sizes, and writes the metadata row. The thumbnail step is most of the latency (roughly 70-80% of the request time in the samples I pulled, but I only looked at one day of logs, so take that with a grain of salt).

It also means a burst of large uploads ties up web workers doing CPU work they were never sized for. We've had at least two pages this quarter that I think trace back to this, i.e. the web pool saturates and health checks start failing.

The challenges we will face are:

* The UI currently assumes the thumbnails exist the moment the upload returns. That's going to break.
* We don't have a queue in this service yet, so we'd be adding new infra, alerts, a runbook, etc.
* Retries. If the worker dies halfway through, we need to know which sizes got written.
* I'm not sure how the CDN cache behaves if it sees a 404 for a thumbnail and then the file shows up a few seconds later.

## Options

:x: **Make the resize faster.** We could swap libraries or drop a size. This helps a little, but it doesn't fix the real problem, which is doing CPU-heavy work on the request path at all.

:x: **Resize lazily on first read.** Simple, but it just moves the latency to whoever views the image first, and the CDN corner-case above gets worse.

:white_check_mark: **Queue + worker.** The upload stores the original, writes the metadata row with `thumbnails: pending`, enqueues a job, and returns. The worker generates the sizes and flips the status. The UI shows a placeholder while it's pending.

(CQ): is "pending" the right name, or do we want a real state machine here? I'd rather not over-design this, but I also don't want to rename a column later.

## Open questions

TODO: confirm the UI team is ok with a placeholder state. Obviously it's a UX change, though I think it's a small one.

TODO: figure out the retry story. My gut says the worker should regenerate every size on retry and overwrite, since resizing is idempotent, but I haven't checked whether we version the object keys.

TODO: does the existing job framework in the other service work for this, or is it too tied to that codebase?

_How might we make uploads fast and predictable under load, without making the image experience worse for the people viewing them..._
