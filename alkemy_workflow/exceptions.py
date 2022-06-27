#!/usr/bin/env python

__all__ = [
    'GenericException',
    'GenericWarning',
    'TaskNotFound',
    'StatusNotFound',
    'InvalidOption',
    'CommandNotFound',
    'ShowHelp',
    'GitException',
    'ConfigException',
    'ClickUpException',
]


class GenericException(Exception):
    "Generic exception"


class GenericWarning(GenericException):
    "Generic warning (exit with 0 status)"


class TaskNotFound(GenericException):
    "Task not found"


class StatusNotFound(GenericException):
    "Status not found"


class InvalidOption(GenericException):
    "Invalid option (command line argument)"


class CommandNotFound(GenericException):
    "Command not found"


class ShowHelp(GenericException):
    "Show help message"


class GitException(GenericException):
    "Git exception"


class ConfigException(GenericException):
    "Missing configuration exception"


class ClickUpException(GenericException):
    "ClickUp exception"
