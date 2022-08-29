#!/usr/bin/env python

import json
import urllib
import requests
from pathlib import Path
from .exceptions import GitHubException

REPO_BASE_URL = "https://github.com/"
SERVER_URL = "https://api.github.com/"

__all__ = ["GitHubClient"]


class GitHubClient:
    def __init__(self, config):
        self.server = SERVER_URL
        self.config = config

    def send_request(
        self, part, method="GET", request_args=None, payload=None, **kwargs
    ):
        "Send HTTP Request to GitHub"
        part = part.format(**kwargs)
        url = urllib.parse.urljoin(self.server, part)
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.config.default_github_token}",
        }
        request_args = request_args or dict()
        if payload is not None:
            request_args["json"] = payload
        response = requests.request(
            method=method, url=url, headers=headers, **request_args
        )
        # self.save_response(response)
        payload = response.json()
        if response.status_code < 200 or response.status_code > 299:
            raise GitHubException(payload["message"])
        return payload

    def save_response(self, response):
        rqs = response.request
        path_url = (
            rqs.path_url.strip("/").replace("..", "").split("?")[0]
            + "."
            + rqs.method.lower()
        )
        filename = Path.cwd() / "tests" / "data" / Path(*path_url.split("/"))
        print(filename)
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("wb") as f:
            f.write(response.content)
        headers_filename = filename.parent / (filename.name + ".headers")
        with headers_filename.open("w") as f:
            headers = dict(response.headers)
            headers["__Status__"] = response.status_code
            json.dump(headers, f, indent=2)

    def extract_repo(self, repo_url):
        if not repo_url.startswith(REPO_BASE_URL):
            raise GitHubException(
                f"Invalid repository URL, must starts with {REPO_BASE_URL}"
            )
        repo_url = repo_url[len(REPO_BASE_URL) :]
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]
        return repo_url

    def get_ref(self, repo_url, ref):
        "Get a reference"
        repo = self.extract_repo(repo_url)
        return self.send_request(f"repos/{repo}/git/refs/heads/{ref}")

    def create_ref(self, repo_url, branch_name, sha):
        "Create a reference"
        repo = self.extract_repo(repo_url)
        return self.send_request(
            f"repos/{repo}/git/refs",
            method="POST",
            payload={"ref": f"refs/heads/{branch_name}", "sha": sha},
        )

    def create_branch(self, repo_url, branch_name, base_branch=None):
        "Create a new remote branch"
        base_branch = base_branch or self.config.git_base_branch
        # Check if branch already exists
        try:
            ref_response = self.get_ref(repo_url, branch_name)
            return True  # branch already exists
        except GitHubException:
            pass
        # Get base branch ref
        ref_response = self.get_ref(repo_url, base_branch)
        # Create the new branch
        self.create_ref(repo_url, branch_name, ref_response["object"]["sha"])
        return False  # new branch

    def create_pull_request(self, repo_url, branch_name, title, base_branch=None):
        "Create a new pull request"
        base_branch = base_branch or self.config.git_base_branch
        repo = self.extract_repo(repo_url)
        payload = {"title": title, "head": branch_name, "base": base_branch}
        return self.send_request(f"repos/{repo}/pulls", method="POST", payload=payload)

    def list_pull_request(self, repo_url):
        "List pull request"
        repo = self.extract_repo(repo_url)
        return self.send_request(f"repos/{repo}/pulls")

    def merge_pull_request(self, repo_url, pr_nr, base_branch=None):
        "Create a new pull request"
        base_branch = base_branch or self.config.git_base_branch
        repo = self.extract_repo(repo_url)
        return self.send_request(f"repos/{repo}/pulls/{pr_nr}/merge", method="PUT")

    def get_user(self):
        return self.send_request("user")

    def list_issues(self, repo_url):
        "List repository issues"
        repo = self.extract_repo(repo_url)
        return self.send_request(f"repos/{repo}/issues", per_page=100)
