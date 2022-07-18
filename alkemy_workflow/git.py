#!/usr/bin/env python

import subprocess
from pathlib import Path
from .exceptions import GitException


__all__ = ["Git"]


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

    def get_remote_url(self):
        "Get remote url"
        try:
            return self.run("remote", "get-url", "origin")
        except GitException:
            return None

    def checkout(self, *args):
        "Switch branch"
        return self.run("checkout", *args)

    def pull(self):
        "Fetch from remote(if any)"
        if self.get_remote_url():
            return self.run("pull")

    def push(self, *args):
        "Update remote"
        return self.run("push", *args)

    def get_github_url(self, branch_name):
        "Get link to github (if origin is github)"
        url = self.get_remote_url()
        if not url or "github.com" not in url:
            return None
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "https://github.com/")
        url = url[:-4]
        if branch_name:
            url = url + "/tree/" + branch_name
        return url
