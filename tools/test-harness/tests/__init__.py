import os
import tempfile

# Isolate the cross-process suite lock (evaluator.run_suite) from any
# real campaign on the developer machine; per-process so parallel test
# runs do not collide.
os.environ.setdefault(
    "EVALUATOR_SUITE_LOCK",
    os.path.join(
        tempfile.gettempdir(), f"evaluator-suite-test-{os.getpid()}.lock"
    ),
)
