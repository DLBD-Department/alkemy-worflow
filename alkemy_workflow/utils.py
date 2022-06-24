#!/usr/bin/env python

import os
import subprocess
import configparser
from pathlib import Path
from .exceptions import GitException, GenericException


__all__ = [
    'Config',
    'Git',
]


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
            raise GitException(completed_process.stdout.decode('utf-8'))
        return completed_process.stdout.strip().decode('utf-8')

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
    git_base_branch = 'main'

    def __init__(self, base_path=None):
        # Load credentials
        self.load_credentials()
        # Get project config
        self.load_config(base_path)

    def load_credentials(self):
        credentials_path = self.get_credentials_path()
        if 'CLICKUP_TOKEN' in os.environ:
            self.clickup_token = os.environ['CLICKUP_TOKEN']
        elif credentials_path.exists():
            config = configparser.ConfigParser()
            config.read(credentials_path)
            self.retrieve_config(config, 'default', 'clickup_token')
            self.retrieve_config(config, 'default', 'clickup_team_id')
        if not self.default_clickup_token:
            raise GenericException(
                f"Please set the ClickUp token in {credentials_path} file or in the CLICKUP_TOKEN environment variable"
            )

    def load_config(self, base_path):
        git = Git(self)
        self.git_dir = git.get_toplevel(base_path)
        self.config_path = self.git_dir / 'alkemy_workflow.ini'
        if self.config_path.exists():
            config = configparser.ConfigParser()
            config.read(self.config_path)
            self.retrieve_config(config, 'git', 'base_branch')

    def retrieve_config(self, config, section, key):
        try:
            setattr(self, section + '_' + key, config[section][key])
        except KeyError:
            pass

    @classmethod
    def get_credentials_path(cls):
        "Get credential file path"
        home_dir = Path.home()
        return home_dir / '.alkemy_workflow' / 'credentials'
