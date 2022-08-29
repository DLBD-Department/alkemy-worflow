#!/usr/bin/env python

import os
import io
from alkemy_workflow.cli import main, EXIT_SUCCESS, EXIT_FAILURE, EXIT_PARSER_ERROR
from alkemy_workflow.utils import Workflow
from .commons import git_path, git_path_credentials_config, mock_response


class TestCmds:
    def test_main(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw"]) == EXIT_SUCCESS
        assert main(["aw", "--help"]) == EXIT_SUCCESS
        assert main(["aw", "mango", "--help"]) == EXIT_PARSER_ERROR
        assert main(["aw", "help", "-mango"]) == EXIT_PARSER_ERROR
        assert main(["aw", "help", "--mango"]) == EXIT_PARSER_ERROR
        assert main(["aw", "configure", "--help"]) == EXIT_SUCCESS
        assert main(["aw", "branch", "--help"]) == EXIT_SUCCESS
        assert main(["aw", "commit", "--help"]) == EXIT_SUCCESS

    def test_configure_not_pk(
        self, git_path_credentials_config, mock_response, monkeypatch
    ):
        monkeypatch.chdir(git_path_credentials_config)
        assert (
            main(
                ["aw", "configure", "--clickup-token", "abcd", "--github-token", "abcd"]
            )
            == EXIT_FAILURE
        )
        assert (
            main(
                [
                    "aw",
                    "configure",
                    "--clickup-token",
                    "pk_abcd",
                    "--github-token",
                    "abcd",
                ]
            )
            == EXIT_FAILURE
        )
        assert (
            main(
                [
                    "aw",
                    "configure",
                    "--clickup-token",
                    "abcd",
                    "--github-token",
                    "ghp_abcd",
                ]
            )
            == EXIT_FAILURE
        )

    def test_configure_stdin(
        self, git_path_credentials_config, mock_response, monkeypatch
    ):
        monkeypatch.chdir(git_path_credentials_config)
        monkeypatch.setattr("sys.stdin", io.StringIO("pk_abcd\nghp_abcd\n"))
        assert main(["aw", "configure"]) == EXIT_SUCCESS
        wf = Workflow()
        assert wf.config.default_clickup_token == "pk_abcd"

    def test_configure(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert (
            main(
                [
                    "aw",
                    "configure",
                    "--clickup-token",
                    "pk_abcd",
                    "--github-token",
                    "ghp_abcd",
                ]
            )
            == EXIT_SUCCESS
        )
        wf = Workflow()
        assert wf.config.default_clickup_token == "pk_abcd"
        assert wf.config.default_github_token == "ghp_abcd"
        assert (
            main(
                [
                    "aw",
                    "configure",
                    "--clickup-token",
                    "pk_1234",
                    "--github-token",
                    "ghp_1234",
                ]
            )
            == EXIT_SUCCESS
        )
        wf.config.load_credentials()
        assert wf.config.default_clickup_token == "pk_1234"
        assert wf.config.default_github_token == "ghp_1234"

    def test_configure_credentials_path(
        self, tmp_path, git_path, mock_response, monkeypatch
    ):
        credentials_path = tmp_path / "credentials"
        monkeypatch.chdir(git_path)
        print(
            main(
                [
                    "aw",
                    "--credentials-path",
                    credentials_path,
                    "configure",
                    "--clickup-token",
                    "pk_abcd",
                    "--github-token",
                    "ghp_abcd",
                ]
            )
        )
        wf = Workflow(credentials_path=credentials_path)
        assert wf.config.default_clickup_token == "pk_abcd"
        assert wf.config.default_github_token == "ghp_abcd"
        assert credentials_path.exists()
        credentials_path.unlink()
        assert (
            main(
                [
                    "aw",
                    "--credentials-path",
                    credentials_path,
                    "configure",
                    "--clickup-token",
                    "pk_1234",
                    "--github-token",
                    "ghp_1234",
                ]
            )
            == EXIT_SUCCESS
        )
        wf.config.load_credentials(credentials_path=credentials_path)
        assert wf.config.default_clickup_token == "pk_1234"
        assert wf.config.default_github_token == "ghp_1234"
        assert credentials_path.exists()

    def test_spaces(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "spaces"]) == EXIT_SUCCESS

    def test_branch(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "branch", "99abcd99"]) == EXIT_SUCCESS

    def test_commit_no_branch(
        self, git_path_credentials_config, mock_response, monkeypatch
    ):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "commit"]) == EXIT_FAILURE

    def test_commit_no_file(
        self, git_path_credentials_config, mock_response, monkeypatch
    ):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "branch", "99abcd99"]) == EXIT_SUCCESS
        assert main(["aw", "commit"]) == EXIT_FAILURE

    def test_commit(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        wf = Workflow()
        assert main(["aw", "branch", "99abcd99"]) == EXIT_SUCCESS
        with open(git_path_credentials_config / "x", "w") as f:
            f.write("x\n")
        wf.git.run("add", "x")
        assert main(["aw", "commit"]) == EXIT_SUCCESS

    def test_init_no_git(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["aw", "init"]) == EXIT_FAILURE

    def test_init_exists(self, git_path_credentials_config, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "init"]) == EXIT_SUCCESS

    def test_init_exists(self, git_path_credentials_config, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        wf = Workflow()
        os.unlink(wf.config.config_path)
        assert main(["aw", "init"]) == EXIT_SUCCESS
        assert wf.config.config_path.exists()
        wf.config.load_config(wf.config.config_path.parent)
        assert wf.config.git_base_branch == "main"

    def test_init_exists_opt(self, git_path_credentials_config, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        wf = Workflow()
        os.unlink(wf.config.config_path)
        assert main(["aw", "init", "--base-branch=devel"]) == EXIT_SUCCESS
        assert wf.config.config_path.exists()
        wf.config.load_config(wf.config.config_path.parent)
        assert wf.config.git_base_branch == "devel"

    def test_set_status(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "get-status", "99abcd99"]) == EXIT_SUCCESS
        assert main(["aw", "set-status", "99abcd99", "done"]) == EXIT_SUCCESS

    def test_branch_github(self, tmp_path, mock_response, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["aw", "branch", "99abcd99"]) == EXIT_FAILURE
        assert (
            main(
                ["aw", "branch", "99abcd99", "--repo", "https://github.com/OWNER/REPO"]
            )
            == EXIT_SUCCESS
        )
        assert main(["aw", "commit"]) == EXIT_FAILURE
