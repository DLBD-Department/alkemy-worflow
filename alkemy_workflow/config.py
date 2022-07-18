#!/usr/bin/env python

import os
import configparser
from pathlib import Path
from .exceptions import ConfigException
from .git import Git


__all__ = ["Config"]

CLICKUP_TOKEN = "CLICKUP_TOKEN"
DEFAULT_GIT_BASE_BRANCH = "main"
CLICKUP_STATUS_IN_PROGRESS = "in_progress"
CLICKUP_STATUS_PR = "in_review"


class Config:

    default_clickup_token = None
    default_clickup_team_id = None
    git_dir = None
    git_base_branch = DEFAULT_GIT_BASE_BRANCH
    clickup_status_in_progress = CLICKUP_STATUS_IN_PROGRESS
    clickup_status_pr = CLICKUP_STATUS_PR

    def __init__(self, base_path=None):
        # Load credentials
        self.load_credentials()
        # Get project config
        self.load_config(base_path)

    def load_credentials(self):
        "Load credentials - load token from CLICKUP_TOKEN environment variable or ~/.alkemy_workflow/credentials file"
        credentials_path = self.get_credentials_path()
        if CLICKUP_TOKEN in os.environ:
            self.default_clickup_token = os.environ[CLICKUP_TOKEN]
        elif credentials_path.exists():
            cp = configparser.ConfigParser()
            cp.read(credentials_path)
            self.retrieve_config(cp, "default", "clickup_token")
            self.retrieve_config(cp, "default", "clickup_team_id")
        if not self.default_clickup_token:
            raise ConfigException(
                f"Please set the ClickUp token in {credentials_path} file or in the {CLICKUP_TOKEN} environment variable"
            )

    def load_config(self, base_path):
        "Get project config - load alkemy_workflow.ini file from project root folder"
        git = Git(self)
        self.git_dir = git.get_toplevel(base_path)
        self.config_path = self.git_dir / "alkemy_workflow.ini"
        if self.config_path.exists():
            cp = configparser.ConfigParser()
            cp.read(self.config_path)
            self.retrieve_config(cp, "git", "base_branch")
            self.retrieve_config(cp, "clickup", "status_in_progress")
            self.retrieve_config(cp, "clickup", "status_pr")

    def retrieve_config(self, cp, section, key):
        try:
            setattr(self, section + "_" + key, cp[section][key])
        except KeyError:
            pass

    def write_config(self, base_branch=None):
        "Write project config file alkemy_workflow.ini"
        cp = configparser.ConfigParser()
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
        if base_branch:
            cp.set("git", "base_branch", base_branch)
        elif not cp.has_option("git", "base_branch"):
            git = Git(self)
            cp.set("git", "base_branch", git.get_current_branch())
        with open(self.config_path, "w") as f:
            cp.write(f)

    @classmethod
    def get_credentials_path(cls):
        "Get credential file path"
        home_dir = Path.home()
        return home_dir / ".alkemy_workflow" / "credentials"

    @classmethod
    def write_credentials(cls, token):
        "Write the token in the credentials file"
        if not token.startswith("pk_"):
            raise ConfigException("Tokens will always begin with pk_")
        credentials_path = cls.get_credentials_path()
        cp = configparser.ConfigParser()
        if credentials_path.exists():
            cp.read(credentials_path)
        if not cp.has_section("default"):
            cp["default"] = {}
        cp.set("default", "clickup_token", token)
        os.makedirs(credentials_path.parent, exist_ok=True)
        with open(credentials_path, "w") as f:
            cp.write(f)
