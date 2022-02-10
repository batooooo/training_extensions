"""Tests for input parameters with OTE CLI"""

# Copyright (C) 2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.

import pytest
from subprocess import run

from ote_cli.registry import Registry

templates = Registry('external').templates
task_types = {str(template.task_type) for template in templates}
ote_find = ['ote', 'find']
find_task_type_cmd = ote_find + ['--task_type']
find_task_type_cmds = [[find_task_type_cmd, [task_type]] for task_type in task_types]

find_root_by_path = ote_find + ['--root']
paths = ['.', '..', '...', 'external', 'not_exists', '!@#$%^&*()|/?', '1234567890', 'asdfghj']

find_root_by_path_cmds = [[find_task_type_cmd, [task_type]] for task_type in task_types]


@pytest.mark.parametrize("cmd, path", find_root_by_path_cmds, ids=paths)
def test_ote_cli_find_root(cmd, path):
    assert run(cmd + path).returncode == 0


@pytest.mark.parametrize("cmd, task_type", find_task_type_cmds, ids=task_types)
def test_ote_cli_find_task_type(cmd, task_type):
    assert run(cmd + task_type).returncode == 0


def test_ote_cli_find_root_empty_path():
    assert run(find_root_by_path).returncode != 0


def test_ote_cli_find_task_type_not_set():
    assert run(find_task_type_cmd).returncode != 0


def test_ote_cli_find():
    assert run(ote_find).returncode == 0


def test_ote_cli_find_help():
    assert run(ote_find + ['-h']).returncode == 0
    assert run(ote_find + ['--help']).returncode == 0
