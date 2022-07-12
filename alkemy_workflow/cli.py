#!/usr/bin/env python

import sys
from datetime import datetime
from pathlib import Path
from .exceptions import (
    GenericWarning,
    GenericException,
    GitException,
    InvalidOption,
    ShowHelp,
)
from .cmds import cmd, cmds, lookup_cmd
from .utils import Config

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PARSER_ERROR = 2

__all__ = ["main"]


def pairwise(iterable):
    return zip(iterable, iterable[1:] + [None])


def prepare_tree(items, enabled=True):
    if not enabled:
        for item in items:
            item["tree"] = str(item["id"])
            yield item
    else:
        level = 0
        for item, next_item in pairwise(items):
            is_last = (next_item is None) or (item["type"] != next_item["type"])
            if level == 0:
                graph = ""
            elif not is_last:
                graph = "├─ "
            else:
                graph = "└─ "
            item["tree"] = f"{' ' * level}{graph}{item.id}"
            if is_last:
                level = level + 1
            yield item


@cmd("[-C=cwd] [--filter=filter] [--noheaders]", defaults={"op_noheaders": False})
def cmd_spaces(kargs, wf):
    """
    List spaces
    Example: spaces --filter 'test*' --noheaders
    """
    header = not kargs["op_noheaders"]
    result = wf.client.query(filter_type="Space", filter_name=kargs.get("filter"))
    fmt = "{id:15} {name:40}"
    if header:
        print(fmt.format(id="Id", name="Space"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cmd(
    "[-C=cwd] [--space=space] [--filter=filter] [--noheaders]",
    defaults={"op_noheaders": False, "space": None},
)
def cmd_folders(kargs, wf):
    """
    List folders from a space
    Example: folders --space 'test' --filter 'abc*' --noheaders
    """
    header = not kargs["op_noheaders"]
    if not kargs["space"]:
        raise InvalidOption("Missing option space")
    result = wf.client.query(
        space=kargs["space"], filter_type="Folder", filter_name=kargs.get("filter")
    )
    fmt = "{id:15} {name:40}"
    if header:
        print(fmt.format(id="Id", name="Folders"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cmd(
    "[-C=cwd] [--space=space] [--folder=folder] [--filter=filter] [--noheaders]",
    defaults={"op_noheaders": False, "space": None, "folder": None},
)
def cmd_lists(kargs, wf):
    """
    List lists from a space or folder
    Example: lists --space 'test' --filter 'abc*' --noheaders
    """
    header = not kargs["op_noheaders"]
    if not kargs["space"] and not kargs["folder"]:
        raise InvalidOption("Missing option space/folder")
    result = wf.client.query(
        space=kargs["space"],
        folder=kargs["folder"],
        filter_type="List",
        filter_name=kargs.get("filter"),
    )
    fmt = "{id:15} {name:40}"
    if header:
        print(fmt.format(id="Id", name="Lists"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cmd(
    "[-C=cwd] [--task_id=task_id] [--space=space] [--folder=folder] [--list=list] [--task=task] [--filter=filter] [--noheaders] [--long]",
    defaults={"op_noheaders": False, "op_long": False},
)
def cmd_tasks(kargs, wf):
    """
    List tasks from a list or subtask
    """
    header = not kargs["op_noheaders"]
    if not kargs.get("list") and not kargs.get("task"):
        raise InvalidOption("Missing option list or task")
    result = wf.client.query(
        space=kargs.get("space"),
        folder=kargs.get("folder"),
        lst=kargs.get("list"),
        task=kargs.get("task"),
        filter_name=kargs.get("filter"),
    )
    fmt = "{label:15} {id:15} {name:40}"
    if header:
        print(fmt.format(id="Id", label="Status", name="Title"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cmd(
    "[-C=cwd] [--space=space] [--folder=folder] [--list=list] [--task=task] [--filter=filter] [--noheaders] [--nohierarchy]",
    defaults={"op_noheaders": False, "op_nohierarchy": False},
)
def cmd_ls(kargs, wf):
    """
    List spaces --> folders --> lists --> tasks --> subtasks
    Example: ls --space 'test' --noheaders
    """
    header = not kargs["op_noheaders"]
    hierarchy = not kargs["op_nohierarchy"]
    result = wf.client.query(
        space=kargs.get("space"),
        folder=kargs.get("folder"),
        lst=kargs.get("list"),
        task=kargs.get("task"),
        filter_name=kargs.get("filter"),
        hierarchy=hierarchy,
    )
    fmt = "{tree:20} {label:15} {name:40}"
    if header:
        print(fmt.format(label="Kind/Status", tree="Id", name="Title"))
        print("-" * 70)
    for item in prepare_tree(result, enabled=hierarchy):
        print(fmt.format(**item))


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
    task_update = {}  # task fields to be updated
    # Start date
    if not task.get("start_date"):
        task_update["start_date"] = int(datetime.utcnow().timestamp() * 1000)
    # Task assignee
    current_user = wf.client.get_user()
    if current_user["id"] not in [x["id"] for x in task["assignees"]]:
        task_update["assignees"] = {
            "add": [ current_user["id"] ]
        }
    # Status
    if task.get("status", {}).get("status") == "to do":
        task_update["status"] = "in_progress"
    # # Open (start) the task
    task.update_task(**task_update)
    # Post a comment
    if not branch_already_exists:
        github_url = wf.git.get_github_url(task.branch_name)
        if github_url:
            comment = f"Branch [{task.branch_name}]({github_url})"
        else:
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
    message = f"[{task['id']}] {task['name']}"
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
        # for f in sorted(cmds, key=lambda x: getattr(x, "cmd")):
        for f in cmds:
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
    exe = Path(argv[0]).name
    try:
        f = lookup_cmd(argv[1])
        f(argv)
        return EXIT_SUCCESS
    except ShowHelp:
        cmd_help([exe, "help", argv[1]])
        return EXIT_SUCCESS
    except GenericWarning as ex:
        print(f"{exe}: {ex}")
        return EXIT_SUCCESS
    except GenericException as ex:
        print(f"{exe}: {ex}")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main(sys.argv))
