"""Tests related to our logging/verbosity setup."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from ansiblelint.testing import run_ansible_lint


# substrs is a list of tuples, where:
#    component 1 is the substring in question
#    component 2 is whether or not to invert ("NOT") the match
@pytest.mark.parametrize(
    ("verbosity", "substrs"),
    (
        pytest.param(
            "",
            [
                ("WARNING  Listing 1 violation(s) that are fatal", False),
                ("DEBUG ", True),
                ("INFO ", True),
            ],
            id="default",
        ),
        pytest.param(
            "-q",
            [
                ("WARNING ", True),
                ("DEBUG ", True),
                ("INFO ", True),
            ],
            id="q",
        ),
        pytest.param(
            "-qq",
            [
                ("WARNING ", True),
                ("DEBUG ", True),
                ("INFO ", True),
            ],
            id="qq",
        ),
        pytest.param(
            "-v",
            [
                ("WARNING  Listing 1 violation(s) that are fatal", False),
                ("INFO     Set ANSIBLE_LIBRARY=", False),
                ("DEBUG ", True),
            ],
            id="v",
        ),
        pytest.param(
            "-vv",
            [
                ("WARNING  Listing 1 violation(s) that are fatal", False),
                ("INFO     Set ANSIBLE_LIBRARY=", False),
            ],
            id="really-loquacious",
        ),
        pytest.param(
            "-vv",
            [
                ("WARNING  Listing 1 violation(s) that are fatal", False),
                ("INFO     Set ANSIBLE_LIBRARY=", False),
            ],
            id="vv",
        ),
    ),
)
def test_verbosity(verbosity: str, substrs: list[tuple[str, bool]]) -> None:
    """Checks that our default verbosity displays (only) warnings."""
    # Piggyback off the .yamllint in the root of the repo, just for testing.
    # We'll "override" it with the one in the fixture, to produce a warning.
    cwd = os.path.realpath(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."),
    )

    fakerole = os.path.join("test", "fixtures", "verbosity-tests")

    if verbosity:
        result = run_ansible_lint(verbosity, fakerole, cwd=Path(cwd))
    else:
        result = run_ansible_lint(fakerole, cwd=Path(cwd))

    for substr, invert in substrs:
        if invert:
            assert substr not in result.stderr, result.stderr
        else:
            assert substr in result.stderr, result.stderr
