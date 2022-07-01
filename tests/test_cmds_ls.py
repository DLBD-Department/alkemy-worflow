#!/usr/bin/env python

import os
import io
import subprocess
from pathlib import Path
import pytest
from alkemy_workflow.cli import main, EXIT_SUCCESS, EXIT_FAILURE, EXIT_PARSER_ERROR
from alkemy_workflow.utils import Workflow
from .commons import git_path, git_path_credentials_config, mock_response


class TestCmdsLs:
    def test_ls(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "ls"]) == EXIT_SUCCESS

    def test_spaces(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "spaces"]) == EXIT_SUCCESS
        assert main(["aw", "spaces", "--filter", "R*"]) == EXIT_SUCCESS
        assert main(["aw", "spaces", "--filter", "R*", "--noheaders"]) == EXIT_SUCCESS

    def test_ls_space(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "ls", "--space", "R&D"]) == EXIT_SUCCESS
        assert main(["aw", "ls", "--space", "10000001"]) == EXIT_SUCCESS
        assert (
            main(["aw", "ls", "--space", "10000001", "--noheaders", "--nohierarchy"])
            == EXIT_SUCCESS
        )

    def test_folders(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert main(["aw", "folders", "--space", "R&D"]) == EXIT_SUCCESS
        assert (
            main(["aw", "folders", "--space", "10000001", "--noheaders"])
            == EXIT_SUCCESS
        )

    def test_ls_folder(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert (
            main(["aw", "ls", "--space", "R&D", "--folder", "Project 1"])
            == EXIT_SUCCESS
        )
        assert (
            main(["aw", "ls", "--space", "10000001", "--folder", "Project 1"])
            == EXIT_SUCCESS
        )
        assert main(["aw", "ls", "--folder", "Project 1"]) == EXIT_FAILURE
        assert main(["aw", "ls", "--folder", "20000001"]) == EXIT_SUCCESS
        assert (
            main(["aw", "ls", "--folder", "20000001", "--noheaders", "--nohierarchy"])
            == EXIT_SUCCESS
        )

    def test_lists(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert (
            main(["aw", "lists", "--space", "R&D", "--folder", "Project 1"])
            == EXIT_SUCCESS
        )
        assert (
            main(["aw", "lists", "--space", "10000001", "--folder", "Project 1"])
            == EXIT_SUCCESS
        )
        assert main(["aw", "lists", "--folder", "Project 1"]) == EXIT_FAILURE
        assert main(["aw", "lists", "--folder", "20000001"]) == EXIT_SUCCESS
        assert (
            main(["aw", "lists", "--folder", "20000001", "--noheaders"]) == EXIT_SUCCESS
        )

    def test_ls_list(self, git_path_credentials_config, mock_response, monkeypatch):
        monkeypatch.chdir(git_path_credentials_config)
        assert (
            main(
                [
                    "aw",
                    "ls",
                    "--space",
                    "R&D",
                    "--folder",
                    "Project 1",
                    "--list",
                    "Backlog",
                ]
            )
            == EXIT_SUCCESS
        )
        assert (
            main(
                [
                    "aw",
                    "ls",
                    "--space",
                    "10000001",
                    "--folder",
                    "Project 1",
                    "--list",
                    "Backlog",
                ]
            )
            == EXIT_SUCCESS
        )
        assert (
            main(["aw", "ls", "--folder", "20000001", "--list", "Backlog"])
            == EXIT_SUCCESS
        )
        assert main(["aw", "ls", "--list", "Backlog"]) == EXIT_FAILURE
        assert main(["aw", "ls", "--list", "30000001"]) == EXIT_SUCCESS
