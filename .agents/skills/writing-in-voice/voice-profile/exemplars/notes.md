- csv export flaky test again. failed twice on CI today, passes locally every time
- first guess was timezone. nope, CI runs in UTC and so do i

TODO: check if the fixture data changed recently

- [x] pinned the random seed in the fixture factory (didn't help)
- [x] ran it 50 times locally in a loop (all green, of course)
- [ ] run it in the CI container image locally... can't get the image to build on my laptop :/ skipping for now

ah, that's because the test sorts by `created_at` and the factory creates all the rows in the same millisecond on a fast machine. locally it's slow enough that the timestamps differ. on CI they tie and the db returns them in whatever order it feels like.

**the test was never testing the sort order, it was testing how fast the machine is.**

TLDR: add a secondary sort key on `id` in the export query. that's probably a real bug too, not just a test problem; real users could see rows shuffle between exports.

questions i still have:

- do any other exports sort on a timestamp alone? i bet the invoice one does
- is it worth adding a lint rule for `order_by` on a single non-unique column? seems like overkill, but maybe
- why does the CI box create rows so much faster? is it using an in-memory db? i thought we turned that off

IDEA: write a tiny helper for tests that spaces out factory timestamps by 1ms, so ties only happen when a test asks for them on purpose.

---
