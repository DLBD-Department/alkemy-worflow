#!/usr/bin/env python

import os
import subprocess
from pathlib import Path
import pytest
from alkemy_workflow.utils import Config
from alkemy_workflow.clickup import ClickUpClient
from .commons import git_path, git_path_credentials_config, mock_response


class TestClickUp:
    def test_clickup(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        config = Config()
        client = ClickUpClient(config)
        print(client.get_user())
