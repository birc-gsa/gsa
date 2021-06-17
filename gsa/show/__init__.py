import argparse

from ..args import command


@command()
def show(args: argparse.Namespace) -> None:
    """Commands for showing various algorithms and
    data structures.

    Select command."""
    show.parser.print_usage()
