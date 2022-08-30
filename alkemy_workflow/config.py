#!/usr/bin/env python

import os
import configparser
import tempfile
from pathlib import Path
from .exceptions import ConfigException, GitException
from .git import Git


__all__ = ["Config"]

CLICKUP_TOKEN = "CLICKUP_TOKEN"
GITHUB_TOKEN = "GITHUB_TOKEN"
DEFAULT_GIT_BASE_BRANCH = "main"
CLICKUP_STATUS_IN_PROGRESS = "in_progress"
CLICKUP_STATUS_PR = "in_review"
CLICKUP_STATUS_MA = "done"
CREDENTIALS_KEYS = (
    "default_clickup_token",
    "default_clickup_team_id",
    "default_github_token",
)
CONFIG_KEYS = (
    "git_base_branch",
    "clickup_status_in_progress",
    "clickup_status_pr",
    "clickup_status_ma",
)


class Config:

    config_path = None
    default_clickup_token = None
    default_clickup_team_id = None
    default_github_token = None
    git_dir = None
    git_base_branch = DEFAULT_GIT_BASE_BRANCH
    clickup_status_in_progress = CLICKUP_STATUS_IN_PROGRESS
    clickup_status_pr = CLICKUP_STATUS_PR
    clickup_status_ma = CLICKUP_STATUS_MA

    def __init__(self, base_path=None, credentials_path=None):
        # Load credentials
        self.load_credentials(credentials_path)
        # Get project config
        try:
            self.load_config(base_path)
        except GitException:
            self.git_dir = None
            self.config_path = None

    def load_credentials(self, credentials_path=None):
        "Load credentials - load token from CLICKUP_TOKEN environment variable or ~/.alkemy_workflow/credentials file"
        credentials_path = credentials_path or self.get_credentials_path()
        if credentials_path.exists():
            cp = configparser.ConfigParser()
            cp.read(credentials_path)
            for config_key in CREDENTIALS_KEYS:
                self.retrieve_config(cp, config_key)
        if CLICKUP_TOKEN in os.environ:
            self.default_clickup_token = os.environ[CLICKUP_TOKEN]
        if GITHUB_TOKEN in os.environ:
            self.default_github_token = os.environ[GITHUB_TOKEN]
        if not self.default_clickup_token:
            # Check if credentials_path is a temporary file
            if self.is_credentials_path_temporary(credentials_path):
                raise ConfigException(
                    f"Please set the ClickUp token in the {CLICKUP_TOKEN} environment variable"
                )
            else:
                raise ConfigException(
                    f"Please set the ClickUp token in {credentials_path} file or in the {CLICKUP_TOKEN} environment variable"
                )

    def is_credentials_path_temporary(self, credentials_path):
        "Return true if credentials_path is temporary file (i.e. is in tempdir)"
        temp_dir = Path(tempfile.gettempdir())
        return temp_dir in credentials_path.parents

    def load_config(self, base_path):
        "Get project config - load alkemy_workflow.ini file from project root folder"
        git = Git(self)
        self.git_dir = git.get_toplevel(base_path)
        self.config_path = self.git_dir / "alkemy_workflow.ini"
        if self.config_path.exists():
            # Load project config
            cp = configparser.ConfigParser()
            cp.read(self.config_path)
            for config_key in CONFIG_KEYS:
                self.retrieve_config(cp, config_key)

    def retrieve_config(self, cp, config_key):
        section, key = config_key.split("_", 1)
        try:
            setattr(self, config_key, cp[section][key])
        except KeyError:
            pass

    def write_config(self, base_branch=None):
        "Write project config file alkemy_workflow.ini"
        cp = configparser.ConfigParser()
        if self.config_path is None:
            raise GitException(
                "Not a git repository (or any of the parent directories)"
            )
        if self.config_path.exists():
            cp.read(self.config_path)
        if not cp.has_section("git"):
            cp["git"] = {}
        if not cp.has_section("clickup"):
            cp["clickup"] = {}
        if cp["clickup"].get("clickup_status_in_progress") is None:
            cp.set(
                "clickup",
                "status_in_progress",
                self.clickup_status_in_progress,
            )
        if cp["clickup"].get("clickup_status_pr") is None:
            cp.set(
                "clickup",
                "status_pr",
                self.clickup_status_pr,
            )
        if cp["clickup"].get("clickup_status_ma") is None:
            cp.set(
                "clickup",
                "status_ma",
                self.clickup_status_ma,
            )
        if base_branch:
            cp.set("git", "base_branch", base_branch)
        elif not cp.has_option("git", "base_branch"):
            git = Git(self)
            cp.set("git", "base_branch", git.get_current_branch())
        with self.config_path.open("w") as f:
            cp.write(f)

    @classmethod
    def get_credentials_path(cls):
        "Get credential file path"
        try:
            home_dir = Path.home()
            return home_dir / ".alkemy_workflow" / "credentials"
        except Exception:
            with tempfile.NamedTemporaryFile() as f:
                return Path(f.name)

    @classmethod
    def write_credentials(cls, clickup_token, github_token, credentials_path):
        "Write the tokens in the credentials file"
        if clickup_token and not clickup_token.startswith("pk_"):
            raise ConfigException("ClickUp API tokens will always begin with pk_")
        if github_token and not github_token.startswith("gh"):
            raise ConfigException(
                "GitHub tokens will always begin with gh?_ (e.g. ghp_, gho_)"
            )
        credentials_path = credentials_path or cls.get_credentials_path()
        cp = configparser.ConfigParser()
        if credentials_path.exists():
            cp.read(credentials_path)
        if not cp.has_section("default"):
            cp["default"] = {}
        if clickup_token:
            cp.set("default", "clickup_token", clickup_token)
        if github_token:
            cp.set("default", "github_token", github_token)
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with credentials_path.open("w") as f:
            cp.write(f)
