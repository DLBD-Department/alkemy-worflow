#!/usr/bin/env python

from pathlib import Path

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property
try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources
from .clickup import ClickUpClient
from .config import Config
from .git import Git
from .github import GitHubClient


__all__ = ["Workflow", "VERSION"]

VERSION = pkg_resources.read_text("alkemy_workflow", "VERSION")


class Workflow:
    def __init__(self, base_path=None, credentials_path=None):
        self.base_path = Path(base_path) if base_path else None
        self.credentials_path = Path(credentials_path) if credentials_path else None

    @cached_property
    def config(self):
        return Config(base_path=self.base_path, credentials_path=self.credentials_path)

    @cached_property
    def git(self):
        return Git(self.config)

    @cached_property
    def github(self):
        return GitHubClient(self.config)

    @cached_property
    def client(self):
        return ClickUpClient(self.config)
