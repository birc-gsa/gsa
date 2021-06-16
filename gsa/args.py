from __future__ import annotations

import argparse
import typing

ARGS_ROOT = argparse.ArgumentParser(
    description='''
        Helper tool for exercises in Genome Scale Algorithms.
        '''
)
ARGS_ROOT.add_argument(
    '-v', '--verbose',
    help="Verbose output",
    action='store_true',
    default=False
)
SUBCOMMANDS = ARGS_ROOT.add_subparsers()


class argument:
    flags: tuple[str, ...]
    options: dict[str, typing.Any]

    def __init__(self, *flags: str, **options: typing.Any) -> None:
        self.flags = flags
        self.options = options


class command:
    args: tuple[argument, ...]
    parser: argparse.ArgumentParser
    parent: argparse._SubParsersAction
    _subparsers: typing.Optional[argparse._SubParsersAction]

    def __init__(self,
                 *args: argument,
                 parent: argparse._SubParsersAction = SUBCOMMANDS
                 ) -> None:
        self.args = args
        self.parent = parent
        self._subparsers = None

    def __call__(
        self,
        cmd: typing.Callable[[argparse.Namespace], None]
    ) -> command:
        self.cmd = cmd
        self.parser = self.parent.add_parser(
            cmd.__name__, description=cmd.__doc__
        )
        for arg in self.args:
            self.parser.add_argument(*arg.flags, **arg.options)
        self.parser.set_defaults(command=cmd)
        return self

    @property
    def subparsers(self) -> argparse._SubParsersAction:
        if self._subparsers is None:
            self._subparsers = self.parser.add_subparsers()
        return typing.cast(argparse._SubParsersAction, self._subparsers)
