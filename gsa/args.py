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


CommandHandler = typing.Callable[[argparse.Namespace], None]


class argument:
    flags: tuple[str, ...]
    options: dict[str, typing.Any]

    def __init__(self, *flags: str, **options: typing.Any) -> None:
        self.flags = flags
        self.options = options


class command:
    _args: tuple[argument, ...]
    _parent: argparse._SubParsersAction

    _parser: typing.Optional[argparse.ArgumentParser]
    _subparsers: typing.Optional[argparse._SubParsersAction]

    _cmd: typing.Optional[typing.Callable[[argparse.Namespace], None]]

    def __init__(self,
                 *args: argument,
                 parent: argparse._SubParsersAction = SUBCOMMANDS
                 ) -> None:
        self._args = args
        self._parent = parent
        self._parser = None
        self._subparsers = None
        self._cmd = None

    def __call__(self, cmd: CommandHandler) -> command:
        self._cmd = cmd
        self._parser = self._parent.add_parser(
            cmd.__name__, description=cmd.__doc__
        )
        assert self._parser is not None
        for arg in self._args:
            self._parser.add_argument(*arg.flags, **arg.options)
        self._parser.set_defaults(command=cmd)
        return self

    @property
    def parser(self) -> argparse.ArgumentParser:
        assert self._parser is not None
        return self._parser

    @property
    def subparsers(self) -> argparse._SubParsersAction:
        assert self._parser is not None
        if self._subparsers is None:
            self._subparsers = self._parser.add_subparsers()
        return self._subparsers

    @property
    def cmd(self) -> typing.Callable[[argparse.Namespace], None]:
        assert self._cmd is not None
        return self._cmd
