#!/usr/bin/env python

import sys
from datetime import datetime
from pathlib import Path
import click
from .exceptions import (
    GenericWarning,
    GenericException,
    GitException,
)
from .utils import Config, Workflow

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


@click.group("cli")
@click.pass_context
@click.option(
    "-C",
    "--cwd",
    help="Run as if git was started in <path> instead of the current working directory",
)
def cli(ctx, cwd):
    ctx.obj = Workflow(cwd)


@cli.command("spaces")
@click.option("--filter", help="Filter spaces by name")
@click.option("--headers/--noheaders", default=True, help="Show/hide headers")
@click.pass_context
def cmd_spaces(ctx, filter, headers):
    """
    List spaces

    Example: aw spaces --filter 'test*' --noheaders
    """
    wf = ctx.obj
    result = wf.client.query(filter_type="Space", filter_name=filter)
    fmt = "{id:15} {name:40}"
    if headers:
        print(fmt.format(id="Id", name="Space"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cli.command("folders")
@click.option("--space", help="Space name", required=True)
@click.option("--filter", help="Filter folders by name")
@click.option("--headers/--noheaders", default=True, help="Show/hide headers")
@click.pass_context
def cmd_folders(ctx, space, filter, headers):
    """
    List folders from a space

    Example: aw folders --space 'test' --filter 'abc*' --noheaders
    """
    wf = ctx.obj
    result = wf.client.query(space=space, filter_type="Folder", filter_name=filter)
    fmt = "{id:15} {name:40}"
    if headers:
        print(fmt.format(id="Id", name="Folders"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cli.command("lists")
@click.option("--space", help="Space name")
@click.option("--folder", help="Folder name")
@click.option("--filter", help="Filter lists by name")
@click.option("--headers/--noheaders", default=True, help="Show/hide headers")
@click.pass_context
def cmd_lists(ctx, space, folder, filter, headers):
    """
    List lists from a space or folder

    Example: aw lists --space 'test' --filter 'abc*' --noheaders
    """
    wf = ctx.obj
    if not space and not folder:
        raise click.ClickException("Missing option '--space' or '--folder'")
    result = wf.client.query(
        space=space,
        folder=folder,
        filter_type="List",
        filter_name=filter,
    )
    fmt = "{id:15} {name:40}"
    if headers:
        print(fmt.format(id="Id", name="Lists"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cli.command("tasks")
@click.option("--space", help="Space name")
@click.option("--folder", help="Folder name")
@click.option("--list", help="List name")
@click.option("--task", help="Task id")
@click.option("--filter", help="Filter tasks by name")
@click.option("--headers/--noheaders", default=True, help="Show/hide headers")
@click.pass_context
def cmd_tasks(ctx, space, folder, list, task, filter, headers):
    """
    List tasks from a list or subtask
    """
    wf = ctx.obj
    if not list and not task:
        raise click.ClickException("Missing option '--list' or '--task'")
    result = wf.client.query(
        space=space, folder=folder, lst=list, task=task, filter_name=filter
    )
    fmt = "{label:15} {id:15} {name:40}"
    if headers:
        print(fmt.format(id="Id", label="Status", name="Title"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cli.command("ls")
@click.option("--space", help="Space name")
@click.option("--folder", help="Folder name")
@click.option("--list", help="List name")
@click.option("--task", help="Task id")
@click.option("--filter", help="Filter tasks by name")
@click.option("--headers/--noheaders", default=True, help="Show/hide headers")
@click.option("--hierarchy/--nohierarchy", default=True, help="Show/hide hierarchy")
@click.pass_context
def cmd_ls(ctx, space, folder, list, task, filter, headers, hierarchy):
    """
    List spaces --> folders --> lists --> tasks --> subtasks

    Example: aw ls --space 'test' --noheaders
    """
    wf = ctx.obj
    result = wf.client.query(
        space=space,
        folder=folder,
        lst=list,
        task=task,
        filter_name=filter,
        hierarchy=hierarchy,
    )
    fmt = "{tree:20} {label:15} {name:40}"
    if headers:
        print(fmt.format(label="Kind/Status", tree="Id", name="Title"))
        print("-" * 70)
    for item in prepare_tree(result, enabled=hierarchy):
        print(fmt.format(**item))


@cli.command("branch")
@click.argument("task_id")
@click.pass_context
def cmd_branch(ctx, task_id):
    """
    Open a task and create a new git branch

    Example: aw branch '#12abcd45'
    """
    wf = ctx.obj
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
        task_update["assignees"] = {"add": [current_user["id"]]}
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


@cli.command("commit")
@click.option("-m", "--message", help="Commit message")
@click.pass_context
def cmd_commit(ctx, message):
    """
    Create a new commit an the current feature branch

    Example: aw commit
    """
    wf = ctx.obj
    # Get task_id by branch name
    current_branch = wf.git.get_current_branch()
    task_id = current_branch.split("-")[0]
    if task_id == wf.config.git_base_branch:
        raise GenericException(
            f"Please commit from feature branches, not {wf.config.git_base_branch}"
        )
    task = wf.client.get_task_by_id(task_id)
    # Prepare the commit message
    if message:
        commit_message = f"[{task['id']}] {task['name']} - {message}"
    else:
        commit_message = f"[{task['id']}] {task['name']}"
    # Commit
    print(wf.git.run("commit", "-m", commit_message))


@cli.command("pr")
@click.pass_context
def cmd_pr(ctx):
    """
    Push local commits to the remote branch and create a pull request on GitHub

    Example: aw pr
    """
    wf = ctx.obj
    wf.git.run("push")
    wf.git.run_gh("pr", "create", "--fill")


@cli.command("status")
@click.pass_context
def cmd_status(ctx):
    """
    Status

    Example: aw status
    """
    # Get task_id by branch name
    wf = ctx.obj
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


@cli.command("configure")
@click.option("--clickup-token", help="Clickup API token")
@click.pass_context
def cmd_configure(ctx, clickup_token):
    """
    Configures credentials (Clickup API token).

    Example: aw configure
    """
    wf = ctx.obj
    prompt = "ClickUP API token: "
    token = clickup_token or input(prompt).strip()
    if token:
        Config.write_credentials(token)
    wf.client.get_user()


@cli.command("init")
@click.option("--base-branch", help="Git base branch")
@click.pass_context
def cmd_init(ctx, base_branch):
    """
    Write alkemy_workflow.ini config file into the project root folder

    Example: aw init --base-branch=main
    """
    wf = ctx.obj
    wf.config.write_config(base_branch=base_branch)


def main(argv=None):
    if argv:
        prog_name = Path(argv[0]).name
        args = argv[1:]
    else:
        args = None
        prog_name = "aw"
    try:
        cli(prog_name=prog_name, args=args)
        return EXIT_SUCCESS
    except SystemExit as err:
        return err.code
    except GenericWarning as ex:
        click.secho(f"{prog_name}: {ex}", fg="red")
        return EXIT_SUCCESS
    except GenericException as ex:
        click.secho(f"{prog_name}: {ex}", fg="red")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main(sys.argv))
