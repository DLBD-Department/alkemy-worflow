#!/usr/bin/env python

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property
from .clickup import ClickUpClient
from .config import Config
from .git import Git
from .github import GitHubClient


__all__ = ["Workflow"]


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
    def github(self):
        return GitHubClient(self.config)

    @cached_property
    def client(self):
        return ClickUpClient(self.config)
