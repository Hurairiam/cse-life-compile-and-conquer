"""
tests/
CSE Life: Compile & Conquer — the test package.

This repository has no pytest suite and pytest is not installed on the
build machines (recon §14), so the standing convention is a headless
module with an `if __name__ == "__main__":` block, run with `python -m`
from the project root. The modules in here follow it: plain `assert`,
no fixtures, no imports beyond the standard library and the game.

    python -m tests.test_quest_state

Each module runs its own checks, prints one PASS or FAIL line per case,
and exits non-zero if anything failed — so it works as a manual check
today and as a CI step the moment there is one. Naming the functions
`test_*` is deliberate: if pytest is ever installed, it collects these
files unchanged.
"""
