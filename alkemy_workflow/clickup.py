#!/usr/bin/env python

import re
import requests
import urllib
from .exceptions import TaskNotFound, StatusNotFound

BRANCH_SEPARATOR = "-"
SERVER_URL = "https://api.clickup.com/api/v2/"

__all__ = ['ClickUpClient', 'Task']


class ClickUpClient:
    def __init__(self, config):
        self.server = SERVER_URL
        self.config = config
        self.team_id = self.config.default_clickup_team_id

    def send_request(
        self, part, method="GET", request_args=None, payload=None, **kwargs
    ):
        "Send HTTP Request to ClickUP"
        part = part.format(**kwargs)
        url = urllib.parse.urljoin(self.server, part)
        headers = {"Authorization": self.config.default_clickup_token}
        request_args = request_args or dict()
        if payload is not None:
            request_args["json"] = payload
        response = requests.request(
            method=method, url=url, headers=headers, **request_args
        )
        return response.json()

    def get_user(self):
        return self.send_request("user")

    def get_team(self):
        return self.send_request("team")

    def retrieve_team_id(self, index=0):
        teams = self.get_team().get("teams", [])
        self.team_id = teams[index].get("id", None)

    def get_spaces(self, archived=False):
        if self.team_id is None:
            self.retrieve_team_id()
        return self.send_request(
            "team/{team_id}/space?archived={archived}",
            team_id=self.team_id,
            archived=archived,
        )["spaces"]

    def get_spaces_id_name_map(self, archived=False):
        spaces = self.get_spaces(archived)
        return dict([(x.get("id"), x.get("name")) for x in spaces])

    def get_space_by_name(self, name):
        spaces = self.get_spaces()
        return [space for space in spaces if space.get("name") == name][0]

    def get_folders(self, space_id, archived=False):
        return self.send_request(
            "space/{space_id}/folder?archived={archived}",
            space_id=space_id,
            archived=archived,
        )

    def get_folder_by_name(self, space_id, name):
        folders = self.get_folders(space_id).get("folders", [])
        return [folder for folder in folders if folder.get("name") == name][0]

    def get_tasks(self, include_closed=False):
        if self.team_id is None:
            self.retrieve_team_id()
        return self.send_request(
            "team/{team_id}/task?include_closed={include_closed}",
            team_id=self.team_id,
            include_closed=include_closed,
        )

    def get_task_by_id(self, task_id):
        result = self.send_request("task/{task_id}/", task_id=task_id.lstrip("#"))
        if "err" in result:
            raise TaskNotFound("Task not found")
        return result

    def update_task_by_id(self, task_id, payload):
        return self.send_request(
            "task/{task_id}/",
            method="PUT",
            task_id=task_id.lstrip("#"),
            payload=payload,
        )

    def get_list_by_id(self, list_id):
        return self.send_request("list/{list_id}/", list_id=list_id)

    def get_statuses(self, list_id):
        return self.get_list_by_id(list_id)["statuses"]

    def get_status_by_status(self, list_id, status):
        result = [x for x in self.get_statuses(list_id) if x.get("status") == status]
        if not result:
            raise StatusNotFound("Status not found")
        return result[0]

    def post_task_comment(self, task_id, payload):
        return self.send_request(
            "task/{task_id}/comment",
            method="POST",
            task_id=task_id.lstrip("#"),
            payload=payload,
        )


class Task:
    def __init__(self, client, task_id):
        self.task_id = task_id
        self.client = client
        self.config = client.config
        self.load()

    def load(self):
        "Load task by id"
        self.data = self.client.get_task_by_id(self.task_id)

    def update(self, **kargs):
        "Update task"
        self.client.update_task_by_id(self.task_id, kargs)
        self.data.update(kargs)

    @property
    def branch_name(self):
        "Branch name"
        name = self.data.get("name")
        branch_name = BRANCH_SEPARATOR.join(
            (
                self.task_id.strip("#"),
                re.sub(
                    r"[^A-Za-z0-9_\-]+", "", name.replace(" ", BRANCH_SEPARATOR)
                ).lower(),
            )
        )
        return branch_name

    def post_task_comment(self, comment_text, notify_all=None, assignee=None):
        "Create task command"
        payload = {"comment_text": comment_text}
        if notify_all is not None:
            payload["notify_all"] = notify_all
        if assignee is not None:
            payload["assignee"] = assignee
        self.client.post_task_comment(self.task_id, payload)

    def __repr__(self):
        return repr(self.data)
