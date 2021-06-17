import sys
import typing


def error(*args: typing.Any, **kwargs: typing.Any) -> None:
    print("ERROR:", *args, **kwargs, file=sys.stderr)
    sys.exit(1)


def warning(*args: typing.Any, **kwargs: typing.Any) -> None:
    print("WARNING:", *args, **kwargs, file=sys.stderr)


def message(*args: typing.Any, **kwargs: typing.Any) -> None:
    print(*args, **kwargs, file=sys.stderr)
