#!/usr/bin/env python

import os
import sys
import traceback
from pathlib import Path
import click
import pzp
from .exceptions import (
    ClickUpException,
    GenericWarning,
    GenericException,
)
from click.exceptions import MissingParameter
from .config import Config, CLICKUP, PLANNER, AW_SKIP_AUTH
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


def pick_task(wf, space=None, folder=None, lst=None, task=None):
    "Select a task"
    result = wf.client.query(
        space=space,
        folder=folder,
        lst=lst,
        task=task,
        hierarchy=True,
    )
    fmt = "{tree:45} {label:15} {name:40}"
    header_str = fmt.format(label="Kind/Status", tree="Id", name="Title")
    last_item = None
    while True:
        items = prepare_tree(result, enabled=True)
        item = pzp.pzp(
            items,
            format_fn=lambda item: fmt.format(**item),
            header_str=header_str,
            layout="reverse-list",
        )
        if item is None:
            return None
        elif item["type"] == "Space":
            item["space"] = {"id": item["id"]}
        elif item["type"] == "Folder":
            item["folder"] = {"id": item["id"]}
        elif item["type"] == "List":
            item["list"] = {"id": item["id"]}
        elif item["type"] == "Task":
            if last_item == item or not item.has_subtasks():
                return item.id
            else:
                item["task"] = {"id": item["id"]}
        elif item["type"] == "Subtask":
            return item.id
        result = wf.client.query(
            space=item.get("space", {}).get("id"),
            folder=item.get("folder", {}).get("id"),
            lst=item.get("list", {}).get("id"),
            task=item.get("task", {}).get("id"),
            hierarchy=True,
        )
        last_item = item


def get_current_task(wf):
    "Get task for current git branch"
    current_branch = wf.git.get_current_branch()
    task_id = current_branch.split("-")[0]
    if task_id == wf.config.git_base_branch:
        raise GenericException(f"Please execute from feature branches, not {wf.config.git_base_branch}")
    return wf.client.get_task_by_id(task_id)


def check_task_status(task, status):
    statuses = task.get_list().get_statuses()
    if status in statuses:
        return True
    else:
        click.secho(
            f"Warning: Status '{status}' not found. Valid statuses are: {', '.join(statuses)}",
            fg="yellow",
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
@click.option(
    "-v",
    "--verbose",
    help="Verbose output",
    default=False,
    is_flag=True,
)
def cli(ctx, cwd, credentials_path, verbose):
    if verbose:
        Config.set_verbose()
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
    fmt = "{id:40.40} {name:40}"
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
    fmt = "{id:40.40} {name:40}"
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
    fmt = "{id:40.40} {name:40}"
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
    result = wf.client.query(space=space, folder=folder, lst=list, task=task, filter_name=filter)
    fmt = "{label:15.15} {id:40.40} {name:40}"
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
    fmt = "{tree:45.45} {label:15.15} {name:40}"
    if headers:
        print(fmt.format(label="Kind/Status", tree="Id", name="Title"))
        print("-" * 70)
    for item in prepare_tree(result, enabled=hierarchy):
        print(fmt.format(**item))


@cli.command("branch")
@click.argument("task_id", required=False)
@click.option("--repo", help="Remote repository URL")
@click.pass_context
def cmd_branch(ctx, task_id, repo):
    """
    Open a task and create a new git branch

    Example: aw branch '#12abcd45'
    """
    wf = ctx.obj
    if task_id is None:
        # Show task picker
        task_id = pick_task(wf=wf)
        if task_id is None:
            raise MissingParameter(ctx=ctx, param_hint="'TASK_ID'", param_type="argument")
    task = wf.client.get_task_by_id(task_id)
    if repo:
        # Create a new remote branch
        branch_already_exists = wf.github.create_branch(repo, task.branch_name)
    else:
        # Create a new local branch a switch to it
        branch_already_exists = wf.git.create_branch(task.branch_name)
    # Update the task
    task.start_task(show_warnings=True)
    # Post a comment
    if not branch_already_exists:
        github_url = wf.git.get_github_url(task.branch_name, repo)
        if github_url:
            comment = f"Branch [{task.branch_name}]({github_url})"
        else:
            comment = f"Branch {task.branch_name}"
        task.post_task_comment(comment)
    click.secho(f"Branch {task.branch_name}", fg="green")


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
    # Push
    if not repo:
        wf.git.push()
    # Create the pull request
    repo = repo or wf.git.get_remote_url()
    title = f"[{task['id']}] {task['name']}"
    response = wf.github.create_pull_request(repo, task.branch_name, title)
    click.secho(f"Pull request created\n{response['html_url']}", fg="green")
    # Update task status
    if wf.config.clickup_status_pr:
        new_status = wf.config.clickup_status_pr
        if check_task_status(task, new_status):
            task.update_task(status=new_status)


@cli.command("lr")
@click.option("--repo", help="Remote repository URL")
@click.option("--headers/--noheaders", default=True, help="Show/hide headers")
@click.argument("task_id", required=False)
@click.pass_context
def cmd_lr(ctx, repo, headers, task_id):
    """
    List pull requests on repository

    Example: aw lr
    """
    wf = ctx.obj
    # List the pull request
    repo = repo or wf.git.get_remote_url()
    result = wf.github.list_pull_request(repo)

    fmt = "{number:6} {title:50.50} {diff_url}"
    if headers:
        print(fmt.format(number="Pr.num", title="Title", diff_url="Diff url"))
        print("-" * 70)
    for item in result:
        print(fmt.format(**item))


@cli.command("merge")
@click.option("--repo", help="Remote repository URL")
@click.option("--pr_nr", help="Pull request number")
@click.argument("task_id", required=False)
@click.pass_context
def cmd_ma(ctx, repo, pr_nr, task_id):
    """
    Merge a certain pull request

    Example: aw merge --pr_nr 1
    """
    wf = ctx.obj
    # Merge the pull request
    repo = repo or wf.git.get_remote_url()
    if pr_nr is None:
        # Show pull request picker
        fmt = "{number:6} {title:50.50} {diff_url}"
        pull_requets = wf.github.list_pull_request(repo)
        pr = pzp.pzp(
            pull_requets,
            format_fn=lambda item: fmt.format(**item),
            fullscreen=False,
        )
        if pr is None:
            raise MissingParameter(ctx=ctx, param_hint="'--pr_nr'", param_type="option")
        else:
            pr_nr = pr["number"]
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
@click.argument("task_id", required=False)
@click.pass_context
def cmd_get_status(ctx, task_id):
    """
    Get task status

    Example: aw get-status '#12abcd45'
    """
    wf = ctx.obj
    if task_id is None:
        # Show task picker
        task_id = pick_task(wf=wf)
        if task_id is None:
            raise MissingParameter(ctx=ctx, param_hint="'TASK_ID'", param_type="argument")
    task = wf.client.get_task_by_id(task_id)
    space = task.get_space()
    style = lambda x: click.style(x, "cyan")
    print(
        f"""\
{style('Task id:')}  {task.task_id}
{style('Status:')}   {task.status}
{style('Space:')}    {space['name']}
{style('Folder:')}   {task['folder']['name']}
{style('List:')}     {task['list']['name']}
{style('Title:')}    {task['name']}"""
    )


@cli.command("set-status")
@click.argument("task_id", required=False)
@click.argument("status", required=False)
@click.pass_context
def cmd_set_status(ctx, task_id, status):
    """
    Change task status

    Example: aw set-status '#12abcd45' 'done'
    """
    wf = ctx.obj
    if task_id is None:
        # Show task picker
        task_id = pick_task(wf=wf)
        if task_id is None:
            raise MissingParameter(ctx=ctx, param_hint="'TASK_ID'", param_type="argument")
    task = wf.client.get_task_by_id(task_id)
    if status is None:
        # Show status picker
        statuses = task.get_list().get_statuses()
        status = pzp.pzp(
            statuses,
            fullscreen=False,
        )
        if status is None:
            raise MissingParameter(ctx=ctx, param_hint="'STATUS'", param_type="argument")
    elif not check_task_status(task, status):
        return
    # Update the task
    try:
        task.update_task(status=status)
        click.secho(f"Task {task_id} status changed to {status}", fg="green")
    except ClickUpException:
        statuses = task.get_list().get_statuses()
        raise GenericException(f"Error setting status. Valid statuses are: {', '.join(statuses)}")


@cli.command("configure")
@click.option("--tasks", help="Tasks backend", type=click.Choice([CLICKUP, PLANNER], case_sensitive=False))
@click.option("--clickup-token", help="ClickUp API token")
@click.option("--github-token", help="GitHub token")
@click.option("--tenant_id", help="O365 Directory (tenant) ID")
@click.option("--client_id", help="O365 Application (client) ID")
@click.option("--client_secret", help="O365 Application (client) secret")
@click.pass_context
def cmd_configure(ctx, tasks, clickup_token, github_token, tenant_id, client_id, client_secret):
    """
    Configures credentials (Clickup/Planner and GitHub).

    Example: aw configure
    """
    wf = ctx.obj
    prev_config = Config(base_path=wf.base_path, credentials_path=wf.credentials_path, skip_errors=True)
    tasks = tasks or click.prompt(
        "Task backend", type=click.Choice([CLICKUP, PLANNER], case_sensitive=False), default=prev_config.default_tasks
    )
    if tasks == CLICKUP:
        clickup_token = clickup_token or click.prompt("ClickUP API token", default=prev_config.default_clickup_token)
    elif tasks == PLANNER:
        tenant_id = tenant_id or click.prompt("O365 Directory (tenant) ID", default=prev_config.o365_tenant_id)
        client_id = client_id or click.prompt("O365 Application (client) ID", default=prev_config.o365_client_id)
        client_secret = client_secret or click.prompt("O365 Application (client) secret", default=prev_config.o365_client_secret)
    github_token = github_token or click.prompt("GitHub token", default=prev_config.default_github_token)
    Config.write_credentials(tasks, clickup_token, github_token, tenant_id, client_id, client_secret, wf.credentials_path)
    # Check credentials
    if AW_SKIP_AUTH in os.environ:
        return
    if tasks == CLICKUP:
        wf.client.get_user()
        click.secho("ClickUP API token verified", fg="green")
    elif tasks == PLANNER:
        wf.config.get_o365_account(interactive=True)
        click.secho("O365 credentials verified", fg="green")
    if wf.config.default_github_token:
        wf.github.get_user()
        click.secho("GitHub token verified", fg="green")


@cli.command("init")
@click.option("--base-branch", help="Git base branch")
@click.option("--tasks", help="Tasks backend", type=click.Choice([CLICKUP, PLANNER], case_sensitive=False))
@click.pass_context
def cmd_init(ctx, base_branch, tasks):
    """
    Write alkemy_workflow.ini config file into the project root folder

    Example: aw init --base-branch=main --tasks clickup
    """
    wf = ctx.obj
    wf.config.write_config(base_branch=base_branch, tasks=tasks)


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
        click.secho(f"{prog_name}: {ex}", fg="yellow")
        if Config.is_verbose():
            traceback.print_exc(file=sys.stdout)
        return EXIT_SUCCESS
    except GenericException as ex:
        click.secho(f"{prog_name}: {ex}", fg="red")
        if Config.is_verbose():
            traceback.print_exc(file=sys.stdout)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main(sys.argv))
