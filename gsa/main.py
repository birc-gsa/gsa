from __future__ import annotations
import sys
import typing
import argparse

ARGS_ROOT = argparse.ArgumentParser(
    description='''
        Helper tool for exercises in Genome Scale Algorithms.
        '''
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
        cmd: typing.Callable[[argparse.ArgumentParser], None]
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


@command()
def simulate(args: argparse.ArgumentParser) -> None:
    """Simulates data for GSA exercises.

    Choose a sub-command to specify which type of data.
    """
    # This is a menu point. There's not any action in it.
    simulate.parser.print_usage()


@command(
    argument("k", help="Number of chromosomes to simulate.", type=int),
    argument("n", help="Lenght of each chromosome.", type=int),
    argument("-o", "--out", help="Fasta file to write the genome to (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
    parent=simulate.subparsers
)
def genome(args: argparse.ArgumentParser) -> None:
    """Simulates genome data."""
    # FIXME
    print("simulating genome", args)


@command(
    argument("genome", help="Genome to sample from.",
             type=argparse.FileType('r')),
    argument("k", help="Number of reads.", type=int),
    argument("n", help="Lenght of each read.", type=int),
    argument("-e", "--edits", help="Number of edits to allow (default 0).",
             type=int, default=0),
    argument("-o", "--out", help="Fastq file to write the reads to (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
    parent=simulate.subparsers
)
def reads(args: argparse.ArgumentParser) -> None:
    """Simulates reads data."""
    print("simulating reads", args)
    # FIXME


def main() -> None:
    args = ARGS_ROOT.parse_args()
    if 'command' not in args:
        print("Select a command to run.")
        ARGS_ROOT.print_help()
    else:
        args.command(args)
