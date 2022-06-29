#!/usr/bin/env python

from pathlib import Path
from .exceptions import InvalidOption, CommandNotFound, ShowHelp
from .utils import Workflow

__all__ = [
    "cmd",
    "cmds",
    "lookup_cmd",
    "parse_args",
    "parse_usage",
]

cmds = []


def cmd(usage="", defaults=None):
    "Command decorator"

    def wrap(f):
        def wrapped_f(argv):
            kargs = parse_args(argv, usage, defaults)
            wf = Workflow(kargs.get("C"))
            f(kargs, wf)

        wrapped_f.__name__ = f.__name__
        wrapped_f.usage = usage
        wrapped_f.__doc__ = getattr(f, "__doc__", None)
        wrapped_f.cmd = f.__name__[4:] if f.__name__.startswith("cmd_") else f.__name__
        cmds.append(wrapped_f)
        return wrapped_f

    return wrap


def parse_args(args, usage, defaults=None):
    "Parse command lines arguments"
    required, optionals, arguments = parse_usage(usage)
    result = []
    kargs = dict(defaults or {})
    kargs["positional"] = result
    opt = None
    args = list(args)
    if args:
        kargs["exe"] = Path(args.pop(0)).name  # args[0] is the executable file name
        if kargs["exe"] == "__main__.py":
            kargs["exe"] = "aw"
    if args:
        kargs["cmd"] = args.pop(0)  # args[0] is the command
    while args:
        arg = args.pop(0)
        if opt is not None:  # arguments value
            value = arg
            kargs[opt] = value
            opt = None
        elif arg in ("--help", "-h", "-?"):
            raise ShowHelp()
        elif required:  # required positional argument
            result.append(arg)
            required.pop(0)
        elif optionals and arg[0] != "-":  # optional positional argument
            result.append(arg)
            optionals.pop(0)
        elif "=" in arg:  # argument --key=value
            (opt, next_arg) = arg.split("=", 1)
            if not opt.startswith("--"):
                raise InvalidOption(f"invalid option: {arg}")
            opt = opt[2:]
            args.insert(0, next_arg)
        else:
            if not arg.startswith("-"):
                raise InvalidOption(f"invalid option: {arg}")
            t = arg.lstrip("-")
            if t in ("help", "h", "?"):
                raise ShowHelp()
            if arguments.get(t) == bool:  # boolean arg
                kargs["op_" + t] = True
            else:
                opt = t
    if opt is not None:
        raise InvalidOption(f"missing value for {opt}")
    if required:  # check missing required values
        raise InvalidOption("missing {}".format(required.pop(0)))
    while optionals:  # add missing optional values
        result.append(None)
        optionals.pop()
    return kargs


def parse_usage(usage):
    "Parse usage help line"
    usage = usage.split("\n")[0].split()
    required = []
    optionals = []
    arguments = {}
    while usage:
        item = usage.pop(0)
        if not item.startswith("["):
            required.append(item)
        else:
            item = item.strip("[]")
            if item[0] != "-":
                optionals.append(item)
            else:
                item = item.lstrip("-")
                if "=" in item:
                    item = item.split("=")[0]
                    arguments[item] = str
                else:
                    arguments[item] = bool
    return required, optionals, arguments


def lookup_cmd(cmd):
    for f in cmds:
        if cmd == getattr(f, "cmd"):
            return f
    raise CommandNotFound('Invalid command "{}"; use "help" for a list.'.format(cmd))
