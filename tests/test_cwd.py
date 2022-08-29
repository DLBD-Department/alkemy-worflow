#!/usr/bin/env python

from alkemy_workflow.cli import main, EXIT_SUCCESS, EXIT_FAILURE, EXIT_PARSER_ERROR
from .commons import git_path, git_path_credentials_config


class TestCwd:
    def test_init_no_git(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["aw", "-C", tmp_path, "init"]) == EXIT_FAILURE

    def test_init_dir_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["aw", "-C", "not-found", "init"]) == EXIT_PARSER_ERROR

    def test_init(self, tmp_path, git_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["aw", "-C", git_path, "init"]) == EXIT_SUCCESS
