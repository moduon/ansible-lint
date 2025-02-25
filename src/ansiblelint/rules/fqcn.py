"""Rule definition for usage of fully qualified collection names for builtins."""
from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

from ansible.plugins.loader import module_loader

from ansiblelint.constants import LINE_NUMBER_KEY
from ansiblelint.rules import AnsibleLintRule, TransformMixin

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap, CommentedSeq

    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable

_logger = logging.getLogger(__name__)

builtins = [
    "add_host",
    "apt",
    "apt_key",
    "apt_repository",
    "assemble",
    "assert",
    "async_status",
    "blockinfile",
    "command",
    "copy",
    "cron",
    "debconf",
    "debug",
    "dnf",
    "dpkg_selections",
    "expect",
    "fail",
    "fetch",
    "file",
    "find",
    "gather_facts",
    "get_url",
    "getent",
    "git",
    "group",
    "group_by",
    "hostname",
    "import_playbook",
    "import_role",
    "import_tasks",
    "include",
    "include_role",
    "include_tasks",
    "include_vars",
    "iptables",
    "known_hosts",
    "lineinfile",
    "meta",
    "package",
    "package_facts",
    "pause",
    "ping",
    "pip",
    "raw",
    "reboot",
    "replace",
    "rpm_key",
    "script",
    "service",
    "service_facts",
    "set_fact",
    "set_stats",
    "setup",
    "shell",
    "slurp",
    "stat",
    "subversion",
    "systemd",
    "sysvinit",
    "tempfile",
    "template",
    "unarchive",
    "uri",
    "user",
    "wait_for",
    "wait_for_connection",
    "yum",
    "yum_repository",
]


class FQCNBuiltinsRule(AnsibleLintRule, TransformMixin):
    """Use FQCN for builtin actions."""

    id = "fqcn"
    severity = "MEDIUM"
    description = (
        "Check whether actions are using using full qualified collection names."
    )
    tags = ["formatting"]
    version_added = "v6.8.0"
    module_aliases: dict[str, str] = {"block/always/rescue": "block/always/rescue"}

    def matchtask(
        self,
        task: dict[str, Any],
        file: Lintable | None = None,
    ) -> list[MatchError]:
        result = []
        module = task["action"]["__ansible_module_original__"]

        if module not in self.module_aliases:
            loaded_module = module_loader.find_plugin_with_context(module)
            target = loaded_module.resolved_fqcn
            self.module_aliases[module] = target
            if target is None:
                _logger.warning("Unable to resolve FQCN for module %s", module)
                self.module_aliases[module] = module
                return []
            if target not in self.module_aliases:
                self.module_aliases[target] = target

        if module != self.module_aliases[module]:
            module_alias = self.module_aliases[module]
            if module_alias.startswith("ansible.builtin"):
                legacy_module = module_alias.replace(
                    "ansible.builtin.",
                    "ansible.legacy.",
                    1,
                )
                if module != legacy_module:
                    result.append(
                        self.create_matcherror(
                            message=f"Use FQCN for builtin module actions ({module}).",
                            details=f"Use `{module_alias}` or `{legacy_module}` instead.",
                            filename=file,
                            lineno=task["__line__"],
                            tag="fqcn[action-core]",
                        ),
                    )
            else:
                if module.count(".") < 2:
                    result.append(
                        self.create_matcherror(
                            message=f"Use FQCN for module actions, such `{self.module_aliases[module]}`.",
                            details=f"Action `{module}` is not FQCN.",
                            filename=file,
                            lineno=task["__line__"],
                            tag="fqcn[action]",
                        ),
                    )
                # TODO(ssbarnea): Remove the c.g. and c.n. exceptions from here once
                # community team is flattening these.
                # See: https://github.com/ansible-community/community-topics/issues/147
                elif not module.startswith("community.general.") or module.startswith(
                    "community.network.",
                ):
                    result.append(
                        self.create_matcherror(
                            message=f"You should use canonical module name `{self.module_aliases[module]}` instead of `{module}`.",
                            filename=file,
                            lineno=task["__line__"],
                            tag="fqcn[canonical]",
                        ),
                    )
        return result

    def matchplay(self, file: Lintable, data: dict[str, Any]) -> list[MatchError]:
        if file.kind != "playbook":
            return []
        if "collections" in data:
            return [
                self.create_matcherror(
                    message="Avoid `collections` keyword by using FQCN for all plugins, modules, roles and playbooks.",
                    lineno=data[LINE_NUMBER_KEY],
                    tag="fqcn[keyword]",
                    filename=file,
                ),
            ]
        return []

    def transform(
        self,
        match: MatchError,
        lintable: Lintable,
        data: CommentedMap | CommentedSeq | str,
    ) -> None:
        if match.tag in {"fqcn[action-core]", "fqcn[action]", "fqcn[canonical]"}:
            target_task = self.seek(match.yaml_path, data)
            # Unfortunately, a lot of data about Ansible content gets lost here, you only get a simple dict.
            # For now, just parse the error messages for the data about action names etc. and fix this later.
            if match.tag == "fqcn[action-core]":
                # split at the first bracket, cut off the last bracket and dot
                current_action = match.message.split("(")[1][:-2]
                # This will always replace builtin modules with "ansible.builtin" versions, not "ansible.legacy".
                # The latter is technically more correct in what ansible has executed so far, the former is most likely better understood and more robust.
                new_action = match.details.split("`")[1]
            elif match.tag == "fqcn[action]":
                current_action = match.details.split("`")[1]
                new_action = match.message.split("`")[1]
            elif match.tag == "fqcn[canonical]":
                current_action = match.message.split("`")[3]
                new_action = match.message.split("`")[1]
            for _ in range(len(target_task)):
                k, v = target_task.popitem(False)
                target_task[new_action if k == current_action else k] = v
            match.fixed = True


# testing code to be loaded only with pytest or when executed the rule file
if "pytest" in sys.modules:
    from ansiblelint.rules import RulesCollection
    from ansiblelint.runner import Runner  # pylint: disable=ungrouped-imports

    def test_fqcn_builtin_fail() -> None:
        """Test rule matches."""
        collection = RulesCollection()
        collection.register(FQCNBuiltinsRule())
        success = "examples/playbooks/rule-fqcn-fail.yml"
        results = Runner(success, rules=collection).run()
        assert len(results) == 3
        assert results[0].tag == "fqcn[keyword]"
        assert "Avoid `collections` keyword" in results[0].message
        assert results[1].tag == "fqcn[action-core]"
        assert "Use FQCN for builtin module actions" in results[1].message
        assert results[2].tag == "fqcn[action]"
        assert "Use FQCN for module actions, such" in results[2].message

    def test_fqcn_builtin_pass() -> None:
        """Test rule does not match."""
        collection = RulesCollection()
        collection.register(FQCNBuiltinsRule())
        success = "examples/playbooks/rule-fqcn-pass.yml"
        results = Runner(success, rules=collection).run()
        assert len(results) == 0, results
