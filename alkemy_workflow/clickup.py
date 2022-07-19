#!/usr/bin/env python

import re
import json
import fnmatch
import requests
import urllib
from pathlib import Path
from .exceptions import (
    SpaceNotFound,
    FolderNotFound,
    ListNotFound,
    TaskNotFound,
    ClickUpException,
    GenericException,
)

BRANCH_SEPARATOR = "-"
SERVER_URL = "https://api.clickup.com/api/v2/"

__all__ = ["ClickUpClient"]


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
        # self.save_response(response)
        payload = response.json()
        if "err" in payload:
            raise ClickUpException(payload["err"])
        return payload

    def save_response(self, response):
        rqs = response.request
        path_url = (
            rqs.path_url.strip("/").replace("..", "").split("?")[0]
            + "."
            + rqs.method.lower()
        )
        filename = Path.cwd() / "tests" / "data" / Path(*path_url.split("/"))
        print(filename)
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("wb") as f:
            f.write(response.content)
        headers_filename = filename.parent / (filename.name + ".headers")
        with headers_filename.open("w") as f:
            headers = dict(response.headers)
            headers["__Status__"] = response.status_code
            json.dump(headers, f, indent=2)

    def get_user(self):
        return self.send_request("user")["user"]

    def get_teams(self):
        return self.send_request("team")["teams"]

    def retrieve_team_id(self, index=0):
        teams = self.get_teams()
        self.team_id = teams[index].get("id", None)

    def get_spaces(self, archived=False):
        "Get spaces"
        if self.team_id is None:
            self.retrieve_team_id()
        result = self.send_request(f"team/{self.team_id}/space?archived={archived}")
        return [Space(self, space) for space in result["spaces"]]

    def get_space_by_id(self, space_id):
        "Get a space by id"
        try:
            data = self.send_request(f"space/{space_id}/")
            return Space(self, data)
        except ClickUpException:
            raise SpaceNotFound(f"Space '{space_id}' not found")

    def get_list_by_id(self, list_id):
        "Get a list by id"
        try:
            data = self.send_request(f"list/{list_id}/")
            return List(self, data)
        except ClickUpException:
            raise ListNotFound(f"List '{list_id}' not found")

    def get_task_by_id(self, task_id):
        "Get a task by id"
        try:
            task_id = task_id.lstrip("#")
            data = self.send_request(f"task/{task_id}/")
            return Task(self, data)
        except ClickUpException:
            raise TaskNotFound(f"Task '{task_id}' not found")

    def get_task(self, task_id, lst=None, space=None, folder=None):
        "Get a task by id"
        if not task_id:
            return None
        else:
            return self.get_task_by_id(task_id)

    def get_space(self, space_id_or_name):
        "Get a space by name or id"
        if not space_id_or_name:
            return None
        elif space_id_or_name.isdigit():  # get by id
            return self.get_space_by_id(space_id=space_id_or_name)
        else:  # get by name
            spaces = self.get_spaces()
            try:
                return [
                    space for space in spaces if space.get("name") == space_id_or_name
                ][0]
            except Exception:
                raise SpaceNotFound(f"Space '{space_id_or_name}' not found")

    def get_folder(self, folder_id_or_name, space=None):
        "Get a folder by name or id"
        if not folder_id_or_name:
            return None
        elif folder_id_or_name.isdigit():  # get by id
            return self.get_folder_by_id(folder_id=folder_id_or_name)
        elif space is None:
            raise GenericException("Please specify space")
        else:  # get by name
            return space.get_folder_by_name(name=folder_id_or_name)

    def get_folder_by_id(self, folder_id):
        "Get a folder by id"
        try:
            data = self.send_request(f"folder/{folder_id}/")
            return Folder(self, data)
        except ClickUpException:
            raise FolderNotFound(f"Folder '{folder_id}' not found")

    def get_list(self, list_id_or_name, space=None, folder=None):
        "Get a list by name or id"
        if not list_id_or_name:
            return None
        elif list_id_or_name.isdigit():
            return self.get_list_by_id(list_id=list_id_or_name)
        else:
            lists = []
            if not space and not folder:
                raise GenericException("Please specify space/folder")
            if space:
                lists.extend(space.get_space_lists())
            if folder:
                lists.extend(folder.get_folder_lists())
            try:
                return [lst for lst in lists if lst.get("name") == list_id_or_name][0]
            except Exception:
                raise ListNotFound(f"List '{list_id_or_name}' not found")

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
        # Get space
        space = self.get_space(space)
        if space and hierarchy:
            result.append(space)
        # Get folder
        folder = self.get_folder(folder, space=space)
        if folder and hierarchy:
            if space is None:
                space = Space(self, folder["space"])
                result.append(space)
            result.append(folder)
        # Get list
        lst = self.get_list(lst, space=space, folder=folder)
        if lst and hierarchy:
            if space is None:
                space = Space(self, lst["space"])
                result.append(space)
            if folder is None and lst.get("folder") and not lst["folder"].get("hidden"):
                folder = Folder(self, lst["folder"])
                result.append(folder)
            result.append(lst)
        # Get task
        task = self.get_task(task, lst=lst, space=space, folder=folder)
        if task and hierarchy:
            if space is None:
                space = self.get_space_by_id(task["space"]["id"])
                result.append(space)
            if (
                folder is None
                and task.get("folder")
                and not task["folder"].get("hidden")
            ):
                folder = Folder(self, task["folder"])
                result.append(folder)
            if lst is None and task.get("list"):
                lst = List(self, task["list"])
                result.append(lst)
            result.append(task)
        # Prepare result
        if task:
            # Task subtasks
            result.extend(task.get_subtasks())
        elif lst:
            # List tasks
            result.extend(lst.get_list_tasks())
        elif folder:
            # Folders lists
            result.extend(folder.get_folder_lists())
        elif space:
            # Space folders
            result.extend(space.get_space_folders())
            # Space folderless lists
            result.extend(space.get_space_lists())
        else:
            # Spaces
            result.extend(self.get_spaces())
        # Filter result by type
        if filter_type:
            result = [x for x in result if x["type"] == filter_type]
        # Filter result by name
        if filter_name:
            match = lambda x: fnmatch.fnmatch(x["name"].lower(), filter_name.lower())
            result = [x for x in result if match(x)]
        return result


class Space(dict):
    def __init__(self, client, data):
        self.update(data)
        self.space_id = data["id"]
        self.client = client
        self["type"] = "Space"
        self["label"] = self["type"]

    def get_folder_by_name(self, name):
        "Get space folder by name"
        folders = self.get_space_folders()
        try:
            return [folder for folder in folders if folder.get("name") == name][0]
        except Exception:
            raise FolderNotFound(f"Folder '{name}' not found")

    def get_space_folders(self, archived=False):
        "Get space folders"
        response = self.client.send_request(
            f"space/{self.id}/folder?archived={archived}",
        )
        return [Folder(self.client, data) for data in response["folders"]]

    def get_space_lists(self, archived=False):
        "Get space lists"
        response = self.client.send_request(
            f"space/{self.id}/list?archived={archived}",
        )
        return [List(self.client, data) for data in response["lists"]]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")


class Folder(dict):
    def __init__(self, client, data):
        self.update(data)
        self.client = client
        self["type"] = "Folder"
        self["label"] = self["type"]

    def get_folder_lists(self, archived=False):
        "Get folder lists"
        response = self.client.send_request(
            f"folder/{self.id}/list?archived={archived}",
        )
        return [List(self.client, data) for data in response["lists"]]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")


class List(dict):
    def __init__(self, client, data):
        self.update(data)
        self.client = client
        self["type"] = "List"
        self["label"] = self["type"]

    def get_list_tasks(self, include_closed=False):
        response = self.client.send_request(
            f"list/{self.id}/task?include_closed={include_closed}"
        )
        return [Task(self.client, data) for data in response["tasks"]]

    def get_statuses(self):
        return [x["status"] for x in self.get("statuses")]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")


class Task(dict):
    def __init__(self, client, data):
        self.update(data)
        self.task_id = data["id"]
        self.client = client
        self["type"] = "Subtask" if self.get("parent") else "Task"
        self["label"] = self.status

    def update_task(self, **kargs):
        "Update task"
        self.client.send_request(
            f"task/{self.id}/",
            method="PUT",
            payload=kargs,
        )
        self.update(kargs)

    def post_task_comment(self, comment_text, notify_all=None, assignee=None):
        "Create task command"
        payload = {"comment_text": comment_text}
        if notify_all is not None:
            payload["notify_all"] = notify_all
        if assignee is not None:
            payload["assignee"] = assignee
        return self.client.send_request(
            f"task/{self.id}/comment",
            method="POST",
            payload=payload,
        )

    def get_subtasks(self, include_closed=False):
        "Get subtasks"
        response = self.client.send_request(
            f"list/{self.list['id']}/task?subtasks=true&include_closed={include_closed}"
        )
        return [
            Task(self.client, data)
            for data in response["tasks"]
            if data.get("parent") == self.id
        ]

    @property
    def branch_name(self):
        "Branch name"
        name = self.get("name")
        branch_name = BRANCH_SEPARATOR.join(
            (
                self.task_id.strip("#"),
                re.sub(
                    r"[^A-Za-z0-9_\-]+", "", name.replace(" ", BRANCH_SEPARATOR)
                ).lower(),
            )
        )
        return branch_name

    @property
    def status(self):
        "Task status"
        return self.get("status", {}).get("status", "-")

    def get_space(self):
        "Get task space"
        space_id = self.get("space", {}).get("id")
        return self.client.get_space_by_id(space_id)

    def get_list(self):
        "Get task list"
        list_id = self.get("list", {}).get("id")
        return self.client.get_list_by_id(list_id)

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")
