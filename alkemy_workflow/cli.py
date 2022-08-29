#!/usr/bin/env python

import sys
from datetime import datetime
from pathlib import Path
import click
from .exceptions import (
    ClickUpException,
    GenericWarning,
    GenericException,
)
from .config import Config
from .utils import Workflow, VERSION

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


def get_current_task(wf):
    "Get task for current git branch"
    current_branch = wf.git.get_current_branch()
    task_id = current_branch.split("-")[0]
    if task_id == wf.config.git_base_branch:
        raise GenericException(
            f"Please execute from feature branches, not {wf.config.git_base_branch}"
        )
    return wf.client.get_task_by_id(task_id)


def check_task_status(task, status):
    statuses = task.get_list().get_statuses()
    if status in statuses:
        return True
    else:
        click.secho(
            f"Status '{status}' not found. Valid statuses are: {', '.join(statuses)}",
            fg="red",
        )
        return False


@click.group("cli")
@click.version_option(VERSION)
@click.pass_context
@click.option(
    "-C",
    "--cwd",
    help="Run as if git was started in <path> instead of the current working directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--credentials-path",
    help="Credentials file path",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
)
def cli(ctx, cwd, credentials_path):
    ctx.obj = Workflow(cwd, credentials_path)


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
@click.option("--repo", help="Remote repository URL")
@click.pass_context
def cmd_branch(ctx, task_id, repo):
    """
    Open a task and create a new git branch

    Example: aw branch '#12abcd45'
    """
    wf = ctx.obj
    task = wf.client.get_task_by_id(task_id)
    if repo:
        # Create a new remote branch
        branch_already_exists = wf.github.create_branch(repo, task.branch_name)
    else:
        # Create a new local branch a switch to it
        branch_already_exists = wf.git.create_branch(task.branch_name)
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
    new_status = wf.config.clickup_status_in_progress
    if task["status"].get("type") == "open" and check_task_status(task, new_status):
        task_update["status"] = new_status
    # Update the task
    task.update_task(**task_update)
    # Post a comment
    if not branch_already_exists:
        github_url = wf.git.get_github_url(task.branch_name, repo)
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
    task = get_current_task(wf)
    # Prepare the commit message
    if message:
        commit_message = f"[{task['id']}] {task['name']} - {message}"
    else:
        commit_message = f"[{task['id']}] {task['name']}"
    # Commit
    print(wf.git.run("commit", "-m", commit_message))


@cli.command("pr")
@click.option("--repo", help="Remote repository URL")
@click.argument("task_id", required=False)
@click.pass_context
def cmd_pr(ctx, repo, task_id):
    """
    Push local commits to the remote branch and create a pull request on GitHub

    Example: aw pr
    """
    wf = ctx.obj
    if task_id:
        # Task id argument
        task = wf.client.get_task_by_id(task_id)
    else:
        # Get task from current git branch
        task = get_current_task(wf)
    # Update status
    if wf.config.clickup_status_pr:
        new_status = wf.config.clickup_status_pr
        if check_task_status(task, new_status):
            task.update_task(status=new_status)
    # Push
    if not repo:
        wf.git.push()
    # Create the pull request
    repo = repo or wf.git.get_remote_url()
    title = f"[{task['id']}] {task['name']}"
    wf.github.create_pull_request(repo, task.branch_name, title)


@cli.command("lr")
@click.option("--repo", help="Remote repository URL")
@click.argument("task_id", required=False)
@click.pass_context
def cmd_lr(ctx, repo, task_id):
    """
    List pull requests on repository

    Example: aw lr
    """
    wf = ctx.obj
    # List the pull request
    repo = repo or wf.git.get_remote_url()
    response = wf.github.list_pull_request(repo)

    for pr in response:
        print(pr["number"], "   |   ", pr["title"], "   |   ", pr["diff_url"])


@cli.command("merge")
@click.option("--repo", help="Remote repository URL")
@click.option("--pr_nr", help="Pull request number")
@click.argument("task_id", required=False)
@click.pass_context
def cmd_ma(ctx, repo, pr_nr, task_id):
    """
    Merge a certain pull request

    Example: aw merge 1
    """
    wf = ctx.obj

    # Merge the pull request
    repo = repo or wf.git.get_remote_url()
    wf.github.merge_pull_request(repo, pr_nr)

    if task_id:
        # Task id argument
        task = wf.client.get_task_by_id(task_id)
    else:
        # Get task from current git branch
        task = get_current_task(wf)
    # Update status
    if wf.config.clickup_status_ma:
        new_status = wf.config.clickup_status_ma
        if check_task_status(task, new_status):
            task.update_task(status=new_status)


@cli.command("get-status")
@click.argument("task_id")
@click.pass_context
def cmd_get_status(ctx, task_id):
    """
    Get task status

    Example: aw get-status '#12abcd45'
    """
    wf = ctx.obj
    task = wf.client.get_task_by_id(task_id)
    space = task.get_space()
    print(
        f"""\
Task id:  {task.task_id}
Status:   {task.status}
Space:    {space['name']}
Folder:   {task['folder']['name']}
List:     {task['list']['name']}
Title:    {task['name']}"""
    )


@cli.command("set-status")
@click.argument("task_id")
@click.argument("status")
@click.pass_context
def cmd_set_status(ctx, task_id, status):
    """
    Change task status

    Example: aw set-status '#12abcd45' 'done'
    """
    wf = ctx.obj
    task = wf.client.get_task_by_id(task_id)
    # Update the task
    try:
        task.update_task(status=status)
    except ClickUpException:
        statuses = task.get_list().get_statuses()
        raise GenericException(
            f"Error setting status. Valid statuses are: {', '.join(statuses)}"
        )


@cli.command("configure")
@click.option("--clickup-token", help="ClickUp API token")
@click.option("--github-token", help="GitHub token")
@click.pass_context
def cmd_configure(ctx, clickup_token, github_token):
    """
    Configures credentials (Clickup and GitHub tokens).

    Example: aw configure
    """
    wf = ctx.obj
    prompt = "ClickUP API token: "
    clickup_token = clickup_token or input(prompt).strip()
    prompt = "GitHub token: "
    github_token = github_token or input(prompt).strip()
    Config.write_credentials(clickup_token, github_token, wf.credentials_path)
    wf.client.get_user()
    click.secho("ClickUP API token verified", fg="green")
    if wf.config.default_github_token:
        wf.github.get_user()
        click.secho("GitHub token verified", fg="green")


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
