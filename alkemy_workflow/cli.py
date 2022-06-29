#!/usr/bin/env python

import sys
import fnmatch
from datetime import datetime
from .exceptions import GenericWarning, GenericException, GitException, ShowHelp
from .cmds import cmd, cmds, lookup_cmd
from .utils import Config

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PARSER_ERROR = 2

__all__ = ["main"]


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def match(kargs, key, target, target_key=None):
    if target_key is None:
        target_key = key
    pat = kargs.get(key)
    if not pat:
        return True
    else:
        return fnmatch.fnmatch(target.get(target_key, "").lower(), pat.lower())


@cmd("[-C=cwd] [--space=space] [--noheaders]", defaults={"op_noheaders": False})
def cmd_spaces(kargs, wf):
    """
    List spaces
    Example: spaces --space 'test*' --noheaders
    """
    header = not kargs["op_noheaders"]
    fmt = "{name:40}"
    if header:
        print(fmt.format(name="Space"))
        print("-" * 70)
    spaces = wf.client.get_spaces()
    for space in spaces:
        if match(kargs, "space", space, "name"):
            print(fmt.format(**space))


@cmd(
    "[-C=cwd] [--noheaders] [--long] [--id=id] [--status=status] [--space=space] [--folder=folder] [--list=list] [--title=title]",
    defaults={"op_noheaders": False, "op_long": False},
)
def cmd_tasks(kargs, wf):
    """
    List tasks
    Example: tasks --title 'test*' --noheaders --long
    """
    header = not kargs["op_noheaders"]
    if kargs["op_long"]:
        fmt = "{task.task_id:10} {task.status:20} {task.space:20} {task.folder:20} {task.list:30} {task.title:60}"
    else:
        fmt = "{task.task_id:10} {task.status:20} {task.title:60}"
    if header:
        print(
            fmt.format(
                task=AttrDict(
                    task_id="Id",
                    status="Status",
                    space="Space",
                    folder="Folder",
                    list="List",
                    title="Title",
                )
            )
        )
        print("-" * 120)
    tasks = wf.client.get_tasks()
    for task in tasks:
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
        if not match(kargs, "title", task):
            continue
        print(fmt.format(task=task))


@cmd("[-C=cwd] task_id")
def cmd_branch(kargs, wf):
    """
    Open a task and create a new git branch
    Example: branch '#12abcd45'
    """
    task_id = kargs["positional"][0]
    task = wf.client.get_task_by_id(task_id)
    branch_already_exists = False
    # Create a new branch a switch to it
    wf.git.run("checkout", wf.config.git_base_branch)
    try:
        wf.git.run("checkout", "-b", task.branch_name)
    except GitException:
        branch_already_exists = True
        wf.git.run("checkout", task.branch_name)
    try:
        wf.git.run("push", "--set-upstream", "origin", task.branch_name)
    except GitException:
        pass
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
def cmd_commit(kargs, wf):
    """
    Create a new commit an the current feature branch
    Example: commit
    """
    # Get task_id by branch name
    current_branch = wf.git.get_current_branch()
    task_id = current_branch.split("-")[0]
    if task_id == wf.config.git_base_branch:
        raise GenericException(
            f"Please commit from feature branches, not {wf.config.git_base_branch}"
        )
    task = wf.client.get_task_by_id(task_id)
    # Prepare the commit message
    message = f"[{task.data['id']}] {task.data['name']}"
    if kargs.get("m"):
        message = message + " - " + kargs["m"]
    # Commit
    print(wf.git.run("commit", "-m", message))


@cmd("[-C=cwd]")
def cmd_pr(kargs, wf):
    """
    Push local commits to the remote branch and create a pull request on GitHub
    Example: pr
    """
    wf.git.run("push")
    wf.git.run_gh("pr", "create", "--fill")


@cmd("[-C=cwd]")
def cmd_status(kargs, wf):
    """
    Status
    Example: status
    """
    # Get task_id by branch name
    current_branch = wf.git.get_current_branch()
    task_id = current_branch.split("-")[0]
    # Print task
    if task_id != wf.config.git_base_branch:
        task = wf.client.get_task_by_id(task_id)
        fmt = """\
Task id: {task.task_id}
Status:  {task.status}
Space:   {task.space}
Folder:  {task.folder}
List:    {task.list}
Title:   {task.title}
"""
        print(fmt.format(task=task))
    print(wf.git.run("status"))


@cmd("[--clickup-token=token]")
def cmd_configure(kargs, wf):
    """
    Configures credentials (Clickup API token).
    Example: configure
    """
    prompt = "ClickUP API token: "
    token = kargs.get("clickup-token") or input(prompt).strip()
    if token:
        Config.write_credentials(token)
    wf.client.get_user()


@cmd("[-C=cwd] [--base-branch=git-base-branch]")
def cmd_init(kargs, wf):
    """
    Write alkemy_workflow.ini config file into the project root folder
    Example: init --base-branch=main
    """
    wf.config.write_config(base_branch=kargs.get("base-branch"))


@cmd("[command]")
def cmd_help(kargs, wf):
    """
    Display information about commands.
    """
    try:
        command = kargs["positional"][0]
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
        cmd_help([argv[0], "help", argv[1]])
        return EXIT_SUCCESS
    except GenericWarning as ex:
        print(f"{argv[0]}: {ex}")
        return EXIT_SUCCESS
    except GenericException as ex:
        print(f"{argv[0]}: {ex}")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main(sys.argv))
