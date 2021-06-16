from __future__ import annotations

import typing
import argparse
import yaml
import sys
import os

from .args import command, argument, ARGS_ROOT
from . import error
from . import tool_tests
from . import search_methods
from . import simulate as sim


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
    sim.simulate_genome(args.k, args.n, args.out)


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
    sim.simulate_reads(args.k, args.n, args.edits,
                       args.genome, args.out)


def preprocess_wrapper(
    f: typing.Callable[[str], None]
) -> typing.Callable[[argparse.Namespace], None]:
    def preprocess(args: argparse.Namespace) -> None:
        if not os.access(args.genome, os.R_OK):
            error.error(f"Can't open genome file {args.genome}")
        f(args.genome)
    return preprocess


@command(
    argument("genome", help="Genome to preprocess (FASTA file).",
             type=str)
)
def preprocess(args: argparse.Namespace) -> None:
    """Preprocess a genome.

    Select the algorithm to preprocess for."""
    preprocess.parser.print_usage()


# FIXME: preprocessing commands
for algo in search_methods.preprocess:
    parser = preprocess.subparsers.add_parser(
        algo.__name__.lower(), help=algo.__doc__,
    )
    parser.set_defaults(command=algo)


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
    exact.parser.print_usage()


for algo in search_methods.exact_search:
    parser = exact.subparsers.add_parser(
        algo.__name__.lower(), help=algo.__doc__,
    )
    parser.set_defaults(command=algo)


@command(
    argument("-e", "--edits",
             help="Number of edits to allow (default 1).",
             type=int, default=1),
    parent=search.subparsers
)
def approx(args: argparse.Namespace) -> None:
    """Run an approximative pattern matching algorithm.

    Select the algorithm to run."""
    approx.parser.print_usage()


for algo in search_methods.approx_search:
    parser = approx.subparsers.add_parser(
        algo.__name__.lower(), help=algo.__doc__,
    )
    parser.set_defaults(command=algo)


@command(
    argument('config',
             help="Configuration file",
             type=argparse.FileType('r')),
)
def test(args: argparse.Namespace) -> None:
    config = tool_tests.test_config(
        yaml.load(args.config.read(), Loader=yaml.SafeLoader)
    )
    tool_tests.test_setup(config, args.verbose)
    tool_tests.test_preprocess(config, args.verbose)
    tool_tests.test_map(config, args.verbose)
    tool_tests.test_compare(config, args.verbose)


def main() -> None:
    args = ARGS_ROOT.parse_args()
    if 'command' not in args:
        print("Select a command to run.")
        ARGS_ROOT.print_help()
    else:
        args.command(args)
