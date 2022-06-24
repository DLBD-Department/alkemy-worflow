#!/usr/bin/env python

import os
import subprocess
from pathlib import Path
import pytest
from alkemy_workflow.utils import Config, Git
from alkemy_workflow.exceptions import ConfigException, GitException
from .commons import (
    git_path,
    git_path_credentials_config,
    write_credentials,
    X20,
)


class TestConfig:
    def test_missing_credentials(self, tmp_path, monkeypatch):
        "Missing credentials file"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with pytest.raises(ConfigException):
            Config()

    def test_env_credentials(self, git_path, monkeypatch):
        "Credentials in environment"
        monkeypatch.setattr(Path, "home", lambda: git_path)
        monkeypatch.setenv("CLICKUP_TOKEN", X20)
        assert 'CLICKUP_TOKEN' in os.environ
        config = Config(git_path)
        assert config.git_dir == git_path
        assert config.default_clickup_token == X20

    def test_env_credentials_not_git(self, tmp_path, monkeypatch):
        "Config in environment not a git repo"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("CLICKUP_TOKEN", X20)
        assert 'CLICKUP_TOKEN' in os.environ
        with pytest.raises(GitException):
            Config(tmp_path)

    def test_credentials(self, git_path, monkeypatch):
        "Read config from file"
        monkeypatch.setattr(Path, "home", lambda: git_path)
        write_credentials(git_path)
        config = Config(git_path)
        assert config.git_dir == git_path
        assert config.default_clickup_token == X20

    def test_config(self, git_path_credentials_config, monkeypatch):
        "Read config from file"
        config = Config(git_path_credentials_config)
        assert config.default_clickup_token == X20
        assert config.git_dir == git_path_credentials_config
        assert config.git_base_branch == "main"

    def test_config_cwd(self, git_path_credentials_config, monkeypatch):
        "Read config from file in current dir"
        monkeypatch.chdir(git_path_credentials_config)
        config = Config()
        assert config.default_clickup_token == X20
        assert config.git_dir == git_path_credentials_config
        assert config.git_base_branch == "main"


class TestGit:
    def test_current_branch(self, git_path_credentials_config, monkeypatch):
        "Read config from file"
        config = Config(git_path_credentials_config)
        git = Git(config)
        assert git.get_current_branch() == "main"

    def test_get_toplevel(self, git_path_credentials_config, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        config = Config()
        git = Git(config)
        os.makedirs(git_path_credentials_config / 'aaaa' / 'bbbb')
        monkeypatch.chdir(git_path_credentials_config)
        assert git.get_toplevel() == git_path_credentials_config
        monkeypatch.chdir(git_path_credentials_config / 'aaaa')
        assert git.get_toplevel() == git_path_credentials_config
        assert (
            git.get_toplevel(git_path_credentials_config / 'aaaa' / 'bbbb')
            == git_path_credentials_config
        )

    def test_status(self, git_path_credentials_config, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        config = Config()
        git = Git(config)
        assert 'alkemy_workflow.ini' in git.run('status', '--porcelain')
