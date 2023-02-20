#!/usr/bin/env pytholick

import re
import fnmatch
from datetime import datetime
import click
from requests.exceptions import HTTPError
from .exceptions import (
    SpaceNotFound,
    ListNotFound,
    TaskNotFound,
    GenericException,
)

BRANCH_SEPARATOR = "-"
TASK_ID_LENGTH = 28

__all__ = ["PlannerClient"]

# ClickUp/Planner Mapping
# Workspace => Organization
# Space => Team
# Folder => N/A
# List => Plan
# Taks => Task
# SubTask => N/A


class PlannerClient:
    def __init__(self, config):
        self.config = config
        self.account = config.get_o365_account(False)
        self.teams = self.account.teams()
        self.planner = self.account.planner()
        self.organization = None

    def get_user(self):
        user = self.account.get_current_user()
        return {"id": user.object_id}

    def get_team_by_id(self, team_id):
        "Get a team by id"
        teams = self.get_organization().get_teams()
        try:
            return [team for team in teams if team.get("id") == team_id][0]
        except Exception:
            raise SpaceNotFound(f"Space '{team_id}' not found")

    def get_plan_by_id(self, plan_id):
        "Get a plan by id"
        try:
            return Plan(self, self.planner.get_plan_by_id(plan_id))
        except HTTPError:
            raise ListNotFound(f"List '{plan_id}' not found")

    def get_task_by_id(self, task_id, plan=None):
        "Get a task by id"
        try:
            task_id = task_id.lstrip("#")
            return Task(self, self.planner.get_task_by_id(task_id), plan=plan)
        except HTTPError:
            raise TaskNotFound(f"Task '{task_id}' not found")

    def get_task(self, task_id, plan=None, team=None):
        "Get a task by id"
        if not task_id:
            return None
        else:
            return self.get_task_by_id(task_id, plan=plan)

    def get_organization(self, index=0):
        "Get the organization"
        if self.organization is None:
            data = {
                "id": "workspace",
                "name": "Organization",
            }
            try:
                url = self.account.protocol.service_url + "organization"
                content = self.account.con.get(url).json()
                data["id"] = content["value"][index]["id"]
                data["name"] = content["value"][index]["displayName"]
            except Exception:
                pass
            self.organization = Organization(self, data)
        return self.organization

    def get_space(self, space_id_or_name):
        "Get a team by name or id"
        return self.get_team(space_id_or_name)

    def get_team(self, team_id_or_name):
        "Get a team by name or id"
        if not team_id_or_name:
            return None
        else:  # get by name/id
            teams = self.get_organization().get_teams()
            try:
                return [team for team in teams if team.get("name") == team_id_or_name or team.get("id") == team_id_or_name][0]
            except Exception:
                raise SpaceNotFound(f"Space '{team_id_or_name}' not found")

    def get_plan(self, plan_id_or_name, team=None):
        "Get a list by name or id"
        if not plan_id_or_name:
            return None
        try:
            return self.get_plan_by_id(plan_id_or_name)
        except ListNotFound:
            if not team:
                raise GenericException("Please specify space")
            try:
                plan_id = [
                    plan.object_id for plan in team.get_plans() if plan.title.lower().strip() == plan_id_or_name.lower().strip()
                ][0]
                return self.get_plan_by_id(plan_id)
            except Exception:
                raise ListNotFound(f"List '{plan_id_or_name}' not found")

    def query(
        self,
        space=None,
        folder=None,
        lst=None,
        task=None,
        filter_type=None,
        filter_name=None,
        hierarchy=False,
    ):
        "Get spaces/folders/lists/tasks"
        result = []
        # Organization
        if hierarchy:
            organization = self.get_organization()
            result.append(organization)
        # Get team
        team = self.get_team(space)
        if team and hierarchy:
            result.append(team)
        # Get plan
        plan = self.get_plan(lst, team=team)
        if plan and hierarchy:
            if team is None:
                team = plan.get_team()
                result.append(team)
            result.append(plan)
        # Get task
        task = self.get_task(task, plan=plan, team=team)
        if task and hierarchy:
            append_plan = False
            append_team = False
            if plan is None:
                plan = task.get_plan()
                append_plan = True
            if team is None:
                team = task.get_team()
                append_team = True
            if append_team:
                result.append(team)
            if append_plan:
                result.append(plan)
            result.append(task)
        # Prepare result
        if task:
            # Task subtasks
            result.append(task)
        elif plan:
            # List tasks
            result.extend(plan.get_tasks())
        elif team:
            # Plans
            result.extend(team.get_plans())
        else:
            # Teams
            result.extend(self.get_organization().get_teams())
        # Filter result by type
        if filter_type:
            result = [x for x in result if x["type"] == filter_type]
        # Filter result by name
        if filter_name:
            match = lambda x: fnmatch.fnmatch(x["name"].lower(), filter_name.lower())
            result = [x for x in result if match(x)]
        return result

    def get_task_from_branch(self, current_branch):
        "Get task ID from branch name"
        return current_branch[0:TASK_ID_LENGTH]


class Organization(dict):
    def __init__(self, client, data):
        self.update(data)
        self.organization_id = data["id"]
        self.client = client
        self["type"] = "Workspace"
        self["label"] = self["type"]

    def get_teams(self, archived=False):
        "Get teams"
        return [Team(self.client, team) for team in self.client.teams.get_my_teams()]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")

    def __eq__(self, other) -> bool:
        return other is not None and isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class Team(dict):
    def __init__(self, client, team):
        self.client = client
        self.update(team.__dict__)
        self["id"] = team.object_id
        self["name"] = team.display_name
        self["type"] = "Space"
        self["label"] = self["type"]

    def get_plans(self, archived=False):
        "Get plans"
        return [Plan(self.client, plan) for plan in self.client.planner.list_group_plans(self["id"])]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")

    def __eq__(self, other) -> bool:
        return other is not None and isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class Plan(dict):
    def __init__(self, client, plan):
        self.client = client
        self.plan = plan
        self.update(plan.__dict__)
        self["id"] = plan.object_id
        self["name"] = plan.title
        self["type"] = "List"
        self["label"] = self["type"]
        self.buckets = dict([(x.object_id, x.name) for x in self.plan.list_buckets()])

    def get_tasks(self, include_closed=False):
        return [Task(self.client, task, plan=self) for task in self.plan.list_tasks()]

    def get_statuses(self):
        return [x.name for x in sorted(self.plan.list_buckets(), key=lambda x: x.order_hint, reverse=True)]

    def get_bucket_id(self, status):
        buckets = dict((x.name, x.object_id) for x in self.plan.list_buckets())
        return buckets.get(status)

    def get_team(self):
        return self.client.get_team_by_id(self["group_id"])

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")

    def __eq__(self, other) -> bool:
        return other is not None and isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class Task(dict):
    def __init__(self, client, task, plan=None):
        self.client = client
        self.task = task
        self.update(task.__dict__)
        self["id"] = task.object_id
        self["task_id"] = task.object_id
        self["name"] = task.title
        self["type"] = "Task"
        if plan is None:
            plan = self.client.get_plan_by_id(self["plan_id"])
        self["plan"] = plan
        self["label"] = self["status"] = plan.buckets[self.bucket_id]
        self["folder"] = {"name": "-"}
        self["list"] = {"name": plan.title}
        self["assignees"] = list(self.assignments.keys())

    def update_task(self, title=None, status=None, start_date_time=None, assignments=None, **kwargs):
        "Update task"
        data = {}
        # Title
        if title:
            data["title"] = title
            self["title"] = title
            self["name"] = title
        # Status (bucket)
        if status is not None:
            bucket_id = self.plan.get_bucket_id(status)
            if bucket_id:
                data["bucketId"] = bucket_id
                self["label"] = self["status"] = status
        # Date and time at which the task starts
        if start_date_time:
            data["startDateTime"] = start_date_time.isoformat().split(".")[0] + "Z"
            self["start_date_time"] = start_date_time
        # Task assignee
        if assignments:
            data["assignments"] = assignments
        if data:
            url = self.task.build_url(self.task._endpoints.get("task").format(id=self.task.object_id))
            response = self.task.con.patch(url, data=data, headers={"If-Match": self.task._etag, "Prefer": "return=representation"})
            if not response:
                return False
            return True

    def post_task_comment(self, comment_text):
        "Add a comment in the task description"
        details = self.task.get_details()
        if details.description:
            description = f"{details.description}\n{comment_text}"
        else:
            description = comment_text
        details.update(description=description)

    def start_task(self, show_warnings=False):
        "Start working on a task"
        # Update the task
        task_update = {}  # task fields to be updated
        # Start date
        if not self.get("start_date_time"):
            task_update["start_date_time"] = datetime.utcnow()
        # Task assignee
        current_user = self.client.get_user()
        if current_user["id"] not in self.assignments.keys():
            assignments = self.assignments
            # https://learn.microsoft.com/en-us/graph/api/resources/planner-order-hint-format?view=graph-rest-1.0
            assignments[current_user["id"]] = {
                "@odata.type": "microsoft.graph.plannerAssignment",
                "orderHint": " !",
            }
            task_update["assignments"] = assignments
            self["assignees"] = list(self.assignments.keys())
        # Status
        in_progress = self.client.config.clickup_status_in_progress
        if self["status"] != in_progress:
            statuses = self.get_list().get_statuses()
            if in_progress in statuses:
                task_update["status"] = in_progress
            elif show_warnings:
                click.secho(
                    f"Warning: Status '{in_progress}' not found. Valid statuses are: {', '.join(statuses)}",
                    fg="yellow",
                )
        # Update the task
        self.update_task(**task_update)

    def get_subtasks(self, include_closed=False):
        "Get subtasks"
        return []

    def has_subtasks(self, include_closed=False):
        "Returns true if the task has subtasks"
        return False

    @property
    def branch_name(self):
        "Branch name"
        name = self.get("name")
        branch_name = BRANCH_SEPARATOR.join(
            (
                self.task_id.strip("#"),
                re.sub(r"[^A-Za-z0-9_\-]+", "", name.replace(" ", BRANCH_SEPARATOR)).lower(),
            )
        )
        return branch_name

    def get_team(self):
        "Get task team"
        return self.get_plan().get_team()

    def get_space(self):
        "Get task space (team)"
        return self.get_team()

    def get_plan(self):
        "Get plan"
        return self["plan"]

    def get_list(self):
        "Get list (plan)"
        return self.get_plan()

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")

    def __eq__(self, other) -> bool:
        return other is not None and isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
