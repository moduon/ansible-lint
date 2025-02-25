"""PyTest Fixtures.

They should not be imported, instead add code below to your root conftest.py
file:

pytest_plugins = ['ansiblelint.testing']
"""
from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING

import pytest

from ansiblelint.config import Options, options
from ansiblelint.constants import DEFAULT_RULESDIR
from ansiblelint.rules import RulesCollection
from ansiblelint.testing import RunFromText

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _pytest.fixtures import SubRequest


@pytest.fixture(name="default_rules_collection")
def fixture_default_rules_collection() -> RulesCollection:
    """Return default rule collection."""
    assert os.path.isdir(DEFAULT_RULESDIR)
    # For testing we want to manually enable opt-in rules
    options.enable_list = ["no-same-owner"]
    return RulesCollection(rulesdirs=[DEFAULT_RULESDIR], options=options)


@pytest.fixture()
def default_text_runner(default_rules_collection: RulesCollection) -> RunFromText:
    """Return RunFromText instance for the default set of collections."""
    return RunFromText(default_rules_collection)


@pytest.fixture()
def rule_runner(request: SubRequest, config_options: Options) -> RunFromText:
    """Return runner for a specific rule class."""
    rule_class = request.param
    config_options.enable_list.append(rule_class().id)
    collection = RulesCollection(options=config_options)
    collection.register(rule_class())
    return RunFromText(collection)


@pytest.fixture(name="config_options")
def fixture_config_options() -> Iterator[Options]:
    """Return configuration options that will be restored after testrun."""
    global options  # pylint: disable=global-statement,invalid-name # noqa: PLW0603
    original_options = copy.deepcopy(options)
    yield options
    options = original_options
