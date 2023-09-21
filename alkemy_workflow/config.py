#!/usr/bin/env python

import os
import configparser
import tempfile
import time
from portalocker import Lock
from portalocker.exceptions import LockException
from pathlib import Path
from O365 import Account, FileSystemTokenBackend, connection  # type: ignore
from .exceptions import ConfigException, GitException
from .git import Git


__all__ = ["Config"]

AW_VERBOSE = "AW_VERBOSE"
AW_TASKS = "AW_TASKS"
AW_SKIP_AUTH = "AW_SKIP_AUTH"
CLICKUP_TOKEN = "CLICKUP_TOKEN"
GITHUB_TOKEN = "GITHUB_TOKEN"
CLICKUP = "clickup"
PLANNER = "planner"
DEFAULT_TASKS = CLICKUP
DEFAULT_GIT_BASE_BRANCH = "main"
CLICKUP_STATUS_IN_PROGRESS = "in_progress"
CLICKUP_STATUS_PR = "review"
CLICKUP_STATUS_MA = "done"
CREDENTIALS_KEYS = (
    "default_tasks",
    "default_clickup_token",
    "default_clickup_team_id",
    "default_github_token",
    "o365_tenant_id",
    "o365_client_id",
    "o365_client_secret",
)
CONFIG_KEYS = (
    "default_tasks",
    "git_base_branch",
    "clickup_status_in_progress",
    "clickup_status_pr",
    "clickup_status_ma",
)
O365_TOKEN_REFRESH_MAX_TRIES = 5
O365_SCOPES = [
    "basic",
    "sharepoint_dl",
    "tasks_all",
]

connection.DEFAULT_SCOPES["tasks_all"] = [
    "Tasks.ReadWrite",
    "Tasks.ReadWrite.Shared",
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
]


class Config:
    config_path = None
    default_tasks = None
    default_clickup_token = None
    default_clickup_team_id = None
    default_github_token = None
    git_dir = None
    git_base_branch = DEFAULT_GIT_BASE_BRANCH
    clickup_status_in_progress = CLICKUP_STATUS_IN_PROGRESS
    clickup_status_pr = CLICKUP_STATUS_PR
    clickup_status_ma = CLICKUP_STATUS_MA
    o365_tenant_id = None
    o365_client_id = None
    o365_client_secret = None

    def __init__(self, base_path=None, credentials_path=None, skip_errors=False):
        # Get project config
        self.base_path = base_path
        try:
            self.load_config()
        except GitException:
            self.git_dir = None
            self.config_path = None
        # Load credentials
        self.load_credentials(credentials_path, skip_errors=skip_errors)

    def load_credentials(self, credentials_path=None, skip_errors=False):
        "Load credentials - load token from CLICKUP_TOKEN environment variable or ~/.alkemy_workflow/credentials file"
        credentials_path = credentials_path or self.get_credentials_path()
        if credentials_path.exists():
            cp = configparser.ConfigParser()
            cp.read(credentials_path)
            for config_key in CREDENTIALS_KEYS:
                if config_key == "default_tasks" and self.default_tasks:
                    continue  # Don't override per-project config
                self.retrieve_config(cp, config_key)
        if AW_TASKS in os.environ:
            self.default_tasks = os.environ[AW_TASKS]
        if CLICKUP_TOKEN in os.environ:
            self.default_clickup_token = os.environ[CLICKUP_TOKEN]
        if GITHUB_TOKEN in os.environ:
            self.default_github_token = os.environ[GITHUB_TOKEN]
        if not self.default_tasks:
            self.default_tasks = DEFAULT_TASKS
        if skip_errors:
            pass
        elif self.default_tasks == CLICKUP:
            if not self.default_clickup_token:
                # Check if credentials_path is a temporary file
                if self.is_credentials_path_temporary(credentials_path):
                    raise ConfigException(f"Please set the ClickUp token in the {CLICKUP_TOKEN} environment variable")
                else:
                    raise ConfigException(
                        f"Please set the ClickUp token in {credentials_path} file or in the {CLICKUP_TOKEN} environment variable"
                    )
        elif self.default_tasks == PLANNER:
            if not self.o365_tenant_id or not self.o365_client_id or not self.o365_client_secret:
                raise ConfigException(
                    f"Please set the Office 365 tenant id, client id and client secret in {credentials_path} file"
                )
        else:
            raise ConfigException(f"Invalid value for tasks. Valid values are {CLICKUP} and {PLANNER}")

    def is_credentials_path_temporary(self, credentials_path):
        "Return true if credentials_path is temporary file (i.e. is in tempdir)"
        temp_dir = Path(tempfile.gettempdir())
        return temp_dir in credentials_path.parents

    def load_config(self):
        "Get project config - load alkemy_workflow.ini file from project root folder"
        git = Git(self)
        self.default_tasks = None
        self.git_dir = git.get_toplevel(self.base_path)
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

    def write_config(self, base_branch=None, tasks=None):
        "Write project config file alkemy_workflow.ini"
        cp = configparser.ConfigParser()
        if self.config_path is None:
            raise GitException("Not a git repository (or any of the parent directories)")
        if self.config_path.exists():
            cp.read(self.config_path)
        if not cp.has_section("default"):
            cp["default"] = {}
        if not cp.has_section("git"):
            cp["git"] = {}
        if not cp.has_section("clickup"):
            cp["clickup"] = {}
        if tasks:
            cp.set("default", "tasks", tasks)
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
    def write_credentials(
        cls, tasks, clickup_token, github_token, o365_tenant_id, o365_client_id, o365_client_secret, credentials_path
    ):
        "Write the tokens in the credentials file"
        if clickup_token and not clickup_token.startswith("pk_"):
            raise ConfigException("ClickUp API tokens will always begin with pk_")
        if github_token and not github_token.startswith("gh"):
            raise ConfigException("GitHub tokens will always begin with gh?_ (e.g. ghp_, gho_)")
        credentials_path = credentials_path or cls.get_credentials_path()
        cp = configparser.ConfigParser()
        if credentials_path.exists():
            cp.read(credentials_path)
        if not cp.has_section("default"):
            cp["default"] = {}
        if not cp.has_section("o365"):
            cp["o365"] = {}
        if tasks:
            cp.set("default", "tasks", tasks)
        if clickup_token:
            cp.set("default", "clickup_token", clickup_token)
        if o365_tenant_id:
            cp.set("o365", "tenant_id", o365_tenant_id)
        if o365_client_id:
            cp.set("o365", "client_id", o365_client_id)
        if o365_client_secret:
            cp.set("o365", "client_secret", o365_client_secret)
        if github_token:
            cp.set("default", "github_token", github_token)
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with credentials_path.open("w") as f:
            cp.write(f)

    @classmethod
    def set_verbose(cls):
        "Turn on vebose output"
        os.environ[AW_VERBOSE] = "true"

    @classmethod
    def is_verbose(cls):
        "True if verbose output is enabled"
        return bool(os.environ.get(AW_VERBOSE))

    def get_o365_account(self, interactive=False):
        "Get O365 Account"
        if self.default_tasks != PLANNER:
            raise Exception("Tasks backend is not ot configured as planner")
        credentials = (self.o365_client_id, self.o365_client_secret)
        home_dir = Path.home()
        token_backend = LockableFileSystemTokenBackend(
            home_dir / ".alkemy_workflow",
            token_filename=f"{self.o365_tenant_id}.json",
        )
        account = Account(
            credentials,
            auth_flow_type="authorization",
            tenant_id=self.o365_tenant_id,
            token_backend=token_backend,
        )
        if not account.is_authenticated:
            if account.con.auth_flow_type in ("authorization", "public") and not interactive:
                raise Exception("Please run 'aw configure' to authenticate")
            if account.authenticate(scopes=O365_SCOPES):
                print("Authenticated!")
        return account


class LockableFileSystemTokenBackend(FileSystemTokenBackend):
    """
    GH #350
    A token backend that ensures atomic operations when working with tokens
    stored on a file system. Avoids concurrent instances of O365 racing
    to refresh the same token file.
    """

    def __init__(self, *args, **kwargs):
        self.fs_wait = False
        super().__init__(*args, **kwargs)

    def should_refresh_token(self, con=None):
        """
        Method for refreshing the token when there are concurrently running instances.
        """
        for _ in range(O365_TOKEN_REFRESH_MAX_TRIES):
            if self.token.is_access_expired:
                try:
                    with Lock(self.token_path, "r+", fail_when_locked=True, timeout=0):
                        if con.refresh_token() is False:
                            raise RuntimeError("Error refreshing token")
                    return None
                except LockException:
                    self.fs_wait = True
                    time.sleep(1)
                    self.token = self.load_token()
            else:
                self.fs_wait = False
                return False
        raise RuntimeError("Could not access locked token file")
