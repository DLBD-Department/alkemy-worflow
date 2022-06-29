#!/usr/bin/env python

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property
import os
import subprocess
import configparser
from pathlib import Path
from .clickup import ClickUpClient
from .exceptions import GitException, ConfigException


__all__ = ["Config", "Git", "Workflow"]

CLICKUP_TOKEN = "CLICKUP_TOKEN"
DEFAULT_GIT_BASE_BRANCH = "main"


class Git:
    def __init__(self, config):
        self.config = config

    def run(self, *args, git_dir=None):
        git_dir = git_dir or (self.config and self.config.git_dir) or None
        if git_dir:
            args = ["git", "-C", git_dir] + list(args)
        else:
            args = ["git"] + list(args)
        completed_process = subprocess.run(args, capture_output=True)
        if completed_process.returncode != 0:
            raise GitException(completed_process.stderr.decode("utf-8"))
        return completed_process.stdout.strip().decode("utf-8")

    def run_gh(self, *args, git_dir=None):
        git_dir = git_dir or (self.config and self.config.git_dir) or None
        args = ["gh"] + list(args)
        completed_process = subprocess.run(args, capture_output=True, cwd=git_dir)
        if completed_process.returncode != 0:
            raise GitException(completed_process.stderr.decode("utf-8"))
        return completed_process.stdout.strip().decode("utf-8")

    def get_current_branch(self):
        "Get current branch"
        return self.run("rev-parse", "--abbrev-ref", "HEAD")

    def get_toplevel(self, git_dir=None):
        "Get the path of the top-level directory of the working tree"
        return Path(self.run("rev-parse", "--show-toplevel", git_dir=git_dir))


class Config:

    default_clickup_token = None
    default_clickup_team_id = None
    git_dir = None
    git_base_branch = DEFAULT_GIT_BASE_BRANCH

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


class Workflow:
    def __init__(self, base_path=None):
        self.base_path = base_path

    @cached_property
    def config(self):
        return Config(base_path=self.base_path)

    @cached_property
    def git(self):
        return Git(self.config)

    @cached_property
    def client(self):
        return ClickUpClient(self.config)
