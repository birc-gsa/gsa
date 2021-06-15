from __future__ import annotations

import typing
import argparse
import yaml
import sys
import os

from . import error
from . import commands
from . import search_methods

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


@command()
def simulate(args: argparse.Namespace) -> None:
    """Simulates data for GSA exercises.

    Choose a sub-command to specify which type of data.
    """
    # This is a menu point. There's not any action in it.
    # If called, we just inform the user to pick a sub-command.
    simulate.parser.print_usage()


@command(
    argument("k", help="Number of chromosomes to simulate.", type=int),
    argument("n", help="Lenght of each chromosome.", type=int),
    argument("-o", "--out",
             help="Fasta file to write the genome to (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
    parent=simulate.subparsers
)
def genome(args: argparse.Namespace) -> None:
    """Simulates genome data."""
    commands.simulate_genome(args.k, args.n, args.out)


@command(
    argument("genome", help="Genome to sample from.",
             type=argparse.FileType('r')),
    argument("k", help="Number of reads.", type=int),
    argument("n", help="Lenght of each read.", type=int),
    argument("-e", "--edits", help="Number of edits to allow (default 0).",
             type=int, default=0),
    argument("-o", "--out",
             help="Fastq file to write the reads to (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
    parent=simulate.subparsers
)
def reads(args: argparse.Namespace) -> None:
    """Simulates reads data."""
    commands.simulate_reads(args.k, args.n, args.edits,
                            args.genome, args.out)


SEARCH_METHODS = [
    cls for cls in vars(search_methods).values()
    if isinstance(cls, type)
    and issubclass(cls, search_methods.Search)
    and cls is not search_methods.Search
]


def exact_wrapper(
    f: typing.Callable[[str, str, typing.TextIO, int], None]
) -> typing.Callable[[argparse.Namespace], None]:
    def search(args: argparse.Namespace) -> None:
        if not os.access(args.genome, os.R_OK):
            error.error(f"Can't open genome file {args.genome}")
        if not os.access(args.reads, os.R_OK):
            error.error(f"Can't open fastq file {args.reads}")
        f(args.genome, args.reads, args.out, 0)
    return search


@command(
    argument("genome", help="Genome to search in (FASTA file).",
             type=str),
    argument("reads", help="Reads to search for (FASTQ file).",
             type=str),
    argument("-o", "--out",
             help="File to write results in (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
)
def search(args: argparse.Namespace) -> None:
    """Search genome for reads.

    Choose a sub-command to specify which type of search.
    """
    # This is a menu point. There's not any action in it.
    # If called, we just inform the user to pick a sub-command.
    search.parser.print_usage()


@command(
    parent=search.subparsers
)
def exact(args: argparse.Namespace) -> None:
    """Run an exact pattern matching algorithm.

    Select the algorithm to run."""
    search.parser.print_usage()


for algo in SEARCH_METHODS:
    parser = exact.subparsers.add_parser(
        algo.name, help=algo.__doc__,
    )
    parser.set_defaults(command=exact_wrapper(algo.map))


@command(
    argument("genome", help="Genome to preprocess (FASTA file).",
             type=str)
)
def preprocess(args: argparse.Namespace) -> None:
    """Preprocess a genome.

    Select the algorithm to preprocess for."""
    preprocess.parser.print_usage()


def preprocess_wrapper(
    f: typing.Callable[[str], None]
) -> typing.Callable[[argparse.Namespace], None]:
    def preprocess(args: argparse.Namespace) -> None:
        if not os.access(args.genome, os.R_OK):
            error.error(f"Can't open genome file {args.genome}")
        f(args.genome)
    return preprocess


for algo in SEARCH_METHODS:
    if algo.can_preprocess:
        parser = preprocess.subparsers.add_parser(
            algo.name, help=algo.__doc__,
        )
        parser.set_defaults(command=preprocess_wrapper(algo.preprocess))


@command(
    argument('config',
             help="Configuration file",
             type=argparse.FileType('r')),
)
def test(args: argparse.Namespace) -> None:
    config = commands.test_config(
        yaml.load(args.config.read(), Loader=yaml.SafeLoader)
    )
    commands.test_setup(config, args.verbose)
    commands.test_preprocess(config, args.verbose)
    commands.test_map(config, args.verbose)
    commands.test_compare(config, args.verbose)


def main() -> None:
    args = ARGS_ROOT.parse_args()
    if 'command' not in args:
        print("Select a command to run.")
        ARGS_ROOT.print_help()
    else:
        args.command(args)
