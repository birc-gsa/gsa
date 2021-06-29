import sys
import typing
from .vis import cols


def error(*args: typing.Any, **kwargs: typing.Any) -> None:
    print(cols.bright_red("ERROR:"), *args, **kwargs, file=sys.stderr)
    sys.exit(1)


def warning(*args: typing.Any, **kwargs: typing.Any) -> None:
    print(cols.bright_yellow("WARNING:"), *args, **kwargs, file=sys.stderr)


def message(*args: typing.Any, **kwargs: typing.Any) -> None:
    print(*args, **kwargs, file=sys.stderr)
