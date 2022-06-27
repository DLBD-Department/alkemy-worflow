#!/usr/bin/env python

import os
import json
import subprocess
from pathlib import Path
import pytest
import urllib.parse
import requests
from requests.structures import CaseInsensitiveDict
from alkemy_workflow.utils import Config

ENV = {
    'GIT_AUTHOR_NAME': 'test test',
    'GIT_AUTHOR_EMAIL': 'test@example.com',
    'GIT_COMMITTER_NAME': 'test',
    'GIT_COMMITTER_EMAIL': 'test@example.com',
}

X20 = "x" * 20

CREDENTIALS = """
[default]
clickup_token = xxxxxxxxxxxxxxxxxxxx
"""

CONFIG = """
[git]
base_branch = main
"""

HEADERS = json.load(open(Path(__file__).parent / 'data' / 'headers'))


def write_credentials(path):
    os.makedirs(Config.get_credentials_path().parent)
    with open(Config.get_credentials_path(), 'w') as f:
        f.write(CREDENTIALS)


def write_config(path):
    config_path = path / 'alkemy_workflow.ini'
    with open(config_path, 'w') as f:
        f.write(CONFIG)


@pytest.fixture
def git_path(tmp_path):
    subprocess.run(['git', '-C', tmp_path, 'init', '--initial-branch=main'])
    for name in ['a', 'b', 'c']:
        with open(tmp_path / name, 'w') as f:
            f.write(f'{name}\n')
        subprocess.run(['git', '-C', tmp_path, 'add', name])
        subprocess.run(['git', '-C', tmp_path, 'commit', '-m', name], env=ENV)
    return tmp_path


@pytest.fixture
def git_path_credentials_config(git_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: git_path)
    write_credentials(git_path)
    write_config(git_path)
    return git_path


class MockResponse:
    def __init__(self, method, url):
        self.url = url
        self.headers = CaseInsensitiveDict(HEADERS)
        parse_result = urllib.parse.urlparse(url)
        path = Path(
            *(parse_result.path.strip('/') + '.' + method.lower())
            .replace('..', '')
            .split('/')
        )
        filepath = Path(__file__).parent / 'data' / path
        self.encoding = 'utf-8'
        try:
            with open(filepath, 'rb') as f:
                self.content = f.read()
            self.status_code = 200
        except:
            self.status_code = 404
            self.content = b'{"err":"Route not found","ECODE":"APP_001"}'

    @property
    def text(self):
        return str(self.content, self.encoding, errors="replace")

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def mock_response(monkeypatch):
    def mock_request(method, url, **kwargs):
        return MockResponse(method, url)

    monkeypatch.setattr(requests, "request", mock_request)
