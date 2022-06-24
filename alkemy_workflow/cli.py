#!/usr/bin/env python

import os
import sys
import fnmatch
import configparser
from datetime import datetime
from .exceptions import GenericWarning, GenericException, GitException, ShowHelp
from .clickup import ClickUpClient, Task
from .cmds import cmd, cmds, lookup_cmd
from .utils import Config, Git


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PARSER_ERROR = 2


def match(kargs, key, target, target_key=None):
    if target_key is None:
        target_key = key
    pat = kargs.get(key)
    if not pat:
        return True
    else:
        return fnmatch.fnmatch(target.get(target_key, '').lower(), pat.lower())


@cmd("[-C=cwd] [--space=space] [--noheaders]", defaults={"op_noheaders": False})
def cmd_spaces(kargs, config):
    """
    List spaces
    Example: spaces --space 'test*' --noheaders
    """
    client = ClickUpClient(config)
    header = not kargs["op_noheaders"]
    fmt = "{name:40}"
    if header:
        print(fmt.format(name="Space"))
        print("-" * 70)
    spaces = client.get_spaces()
    for space in spaces:
        if match(kargs, "space", space, "name"):
            print(fmt.format(**space))


@cmd(
    "[-C=cwd] [--noheaders] [--long] [--id=id] [--status=status] [--space=space] [--folder=folder] [--list=list] [--title=title]",
    defaults={"op_noheaders": False, "op_long": False},
)
def cmd_tasks(kargs, config):
    """
    List tasks
    Example: tasks --name 'test*' --noheaders --long
    """
    client = ClickUpClient(config)
    header = not kargs["op_noheaders"]
    if kargs["op_long"]:
        fmt = "{id:10} {status:20} {space:20} {folder:20} {list:30} {name:60}"
    else:
        fmt = "{id:10} {status:20} {name:60}"
    if header:
        print(
            fmt.format(
                id="Id",
                status="Status",
                space="Space",
                folder="Folder",
                list="List",
                name="Title",
            )
        )
        print("-" * 120)
    tasks = client.get_tasks()["tasks"]
    spaces = client.get_spaces_id_name_map()
    for task in tasks:
        task["space"] = spaces.get(task["space"]["id"])
        task["folder"] = task.get("folder", {}).get("name", "-")
        task["status"] = task.get("status", {}).get("status", "-")
        task["list"] = task.get("list", {}).get("name", "-")
        if not match(kargs, "id", task):
            continue
        if not match(kargs, "status", task):
            continue
        if not match(kargs, "space", task):
            continue
        if not match(kargs, "folder", task):
            continue
        if not match(kargs, "list", task):
            continue
        if not match(kargs, "title", task, "name"):
            continue
        print(fmt.format(**task))


@cmd("[-C=cwd] task_id")
def cmd_branch(kargs, config):
    """
    Open a task and create a new git branch
    Example: branch 1234
    """
    task_id = kargs['positional'][0]
    client = ClickUpClient(config)
    git = Git(config)
    task = Task(client, task_id)
    branch_already_exists = False
    # Create a new branch a switch to it
    git.run("checkout", config.git_base_branch)
    try:
        git.run("checkout", "-b", task.branch_name)
        git.run("push", "--set-upstream", "origin", task.branch_name)
    except GitException:
        branch_already_exists = True
        git.run("checkout", task.branch_name)
    # Update the task
    start_date = task.data.get("start_date") or int(
        datetime.utcnow().timestamp() * 1000
    )
    # Open (start) the task
    task.update(status="in_progress", start_date=start_date)
    # Post a comment
    if not branch_already_exists:
        comment = f"Branch {task.branch_name}"
        task.post_task_comment(comment)


@cmd("[-C=cwd] [-m=message]")
def cmd_commit(kargs, config):
    """
    Create a new commit an the current feature branch
    Example: commit
    """
    client = ClickUpClient(config)
    git = Git(config)
    # Get task_id by branch name
    current_branch = git.get_current_branch()
    task_id = current_branch.split('-')[0]
    if task_id == config.git_base_branch:
        raise GenericException(
            f"Please commit from feature branches, not {config.git_base_branch}"
        )
    task = Task(client, task_id)
    # Prepare the commit message
    message = f"[{task.data['id']}] {task.data['name']}"
    if kargs.get('m'):
        message = message + ' - ' + kargs['m']
    # Commit
    print(git.run("commit", "-m", message))


@cmd("[-C=cwd]")
def cmd_status(kargs, config):
    """
    Status
    Example: status
    """
    client = ClickUpClient(config)
    git = Git(config)
    # Get task_id by branch name
    current_branch = git.get_current_branch()
    task_id = current_branch.split('-')[0]
    # Print task
    if task_id != config.git_base_branch:
        task = Task(client, task_id)
        spaces = client.get_spaces_id_name_map()
        task.data["space"] = spaces.get(task.data["space"]["id"])
        task.data["folder"] = task.data.get("folder", {}).get("name", "-")
        task.data["status"] = task.data.get("status", {}).get("status", "-")
        task.data["list"] = task.data.get("list", {}).get("name", "-")
        fmt = """\
Task id: {id}
Status:  {status}
Space:   {space}
Folder:  {folder}
List:    {list:30}
Title:   {name}
"""
        print(fmt.format(**task.data))
    print(git.run("status"))


@cmd(load_config=False)
def cmd_configure(kargs, config):
    """
    Configures credentials (Clickup API token).
    Example: configure
    """
    prompt = "ClickUP API token: "
    token = input(prompt).strip()
    if token:
        if not token.startswith('pk_'):
            raise GenericException("Tokens will always begin with pk_")
        credentials_path = Config.get_credentials_path()
        cp = configparser.ConfigParser()
        if credentials_path.exists():
            cp.read(credentials_path)
        if not cp.has_section('default'):
            cp['default'] = {}
        cp.set('default', 'clickup_token', token)
        os.makedirs(credentials_path.parent, exist_ok=True)
        with open(credentials_path, 'w') as f:
            cp.write(f)
    config = Config()
    client = ClickUpClient(config)
    response = client.get_user()
    if 'err' in response:
        raise GenericException(response['err'])


@cmd("[command]", load_config=False)
def cmd_help(kargs, config):
    """
    Display information about commands.
    """
    try:
        command = kargs['positional'][0]
    except KeyError:
        command = None
    if command:
        f = lookup_cmd(command)
        usage_text = getattr(f, "usage", "")
        help_text = (getattr(f, "__doc__", "") or "").rstrip("\n\t ")
        print(f"usage: {kargs['exe']} {f.cmd} {usage_text} {help_text}")
    else:
        print(f"usage: {kargs['exe']} <command> [parameters]")
        print("")
        print("Commands:")
        for f in sorted(cmds, key=lambda x: getattr(x, "cmd")):
            usage_text = getattr(f, "usage", "")
            help_text = (getattr(f, "__doc__", "") or "").rstrip("\n\t ")
            print(f" {f.cmd} {usage_text} {help_text}")
            print("")


def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        cmd_help(argv)
        return EXIT_PARSER_ERROR
    try:
        f = lookup_cmd(argv[1])
        f(argv)
        return EXIT_SUCCESS
    except ShowHelp:
        cmd_help([argv[0], 'help', argv[1]])
        return EXIT_SUCCESS
    except GenericWarning as ex:
        print(f"{argv[0]}: {ex}")
        return EXIT_SUCCESS
    except GenericException as ex:
        print(f"{argv[0]}: {ex}")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main(sys.argv))
