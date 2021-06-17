import argparse
from typing import Callable

from pystr.suffixtree import \
    SuffixTree, \
    naive_st_construction, \
    mccreight_st_construction, \
    lcp_st_construction
from pystr.lcp import lcp_from_sa
from pystr import sais

from . import show
from ..args import command, argument

STConstructor = Callable[[str], SuffixTree]


def lcp_construction_wrapper(x: str) -> SuffixTree:
    sa = sais.sais(x)
    lcp = lcp_from_sa(x, sa)
    return lcp_st_construction(x, sa, lcp)


algos: dict[str, STConstructor] = {
    'naive': naive_st_construction,
    'mccreight': mccreight_st_construction,
    'lcp': lcp_construction_wrapper
}


@command(
    argument('x', metavar='x', type=str,
             help='string to build the suffix tree from.'),
    argument('--algo',
             default='mccreight',
             nargs='?',
             choices=algos.keys(),
             help='construction '),
    parent=show.subparsers
)
def suffixtree(args: argparse.Namespace) -> None:
    """Display a suffix tree."""
    st = algos[args.algo](args.x)
    print(st.to_dot())
