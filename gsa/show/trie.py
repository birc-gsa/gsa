#!/usr/bin/env python3

import argparse
from pystr.trie import depth_first_trie

from . import show
from ..args import command, argument


@command(
    argument('strings', metavar='STRING', type=str, nargs='+',
             help='strings to build the trie of.'),
    parent=show.subparsers
)
def trie(args: argparse.Namespace) -> None:
    'Display a trie of a set of strings.'
    trie = depth_first_trie(*args.strings)
    print(trie.to_dot())
