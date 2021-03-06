import argparse

from typing import Callable, Any

from pystr.alphabet import Alphabet
import pystr.bwt

from ..vis import colour, Table, ColSpec, Align, indent
from ..vis.tables import Row
from ..vis.cols import \
    Colour, \
    strip_ansi, \
    underline, bold, plain, \
    bright_blue, bright_green,  bright_red, \
    black, green, magenta, red, blue, yellow

from ..args import command, argument
from . import show


@command(
    parent=show.subparsers
)
def bwt(args: argparse.Namespace) -> None:
    """Show aspects of the BWT search algorithm.

    Pick what to show."""
    bwt.parser.print_usage()


def hit_enter() -> None:
    input("Press ENTER to continue")


def rotation_table(x: str, sa: list[int]) -> Table:
    tbl = Table(
        ColSpec("pointer", align=Align.RIGHT),
        ColSpec("prefix", right_pad=""),
        ColSpec("rotation"),
        ColSpec("r_pointer")
    )
    for j in sa:
        row = tbl.add_row()
        row["rotation"] = str(x[j:])+str(x[:j])
    tbl.add_row()  # so we can index beyond the last
    return tbl


def rot_row(row: Row, a: str, col: Colour) -> None:
    rot = strip_ansi(row["rotation"])
    if rot[-1] == a:
        row["prefix"] = underline(green(a))
        row["rotation"] = colour(rot)[:-1, col][-1, underline & green]
    else:
        row["rotation"] = colour(rot)[-1, red]


def shift_row(row: Row,
              amount: int = 1,
              prefix_col: Colour = green,
              rot_col: Colour = underline
              ) -> None:
    rot = strip_ansi(row["rotation"])
    row["prefix"] = prefix_col(rot[:amount])
    row["rotation"] = rot_col(rot[amount:])


# FIXME: Figure out how to specify that f should take a row
# as its first argument and then *args...
def map_rows(tbl: Table, start: int, stop: int,
             f: Callable[..., Any], *args: Any
             ) -> None:
    for i in range(start, stop):
        f(tbl[i], *args)


def rot_rows(tbl: Table, a: str,
             start: int, stop: int,
             col: Colour = plain) -> None:
    map_rows(tbl, start, stop, rot_row, a, col)


def shift_rows(tbl: Table, start: int, stop: int,
               amount: int = 1,
               prefix_col: Colour = green,
               rot_col: Colour = underline) -> None:
    map_rows(tbl, start, stop, shift_row, amount, prefix_col, rot_col)


@command(
    argument('x', metavar='x', type=str,
             help='string the BWT rotations are made over.'),
    argument('k', metavar='k', type=int, help='current index.'),
    argument('a', metavar='a', type=str, help='character to prepend.'),
    argument('--interactive',
             action=argparse.BooleanOptionalAction,
             default=True,
             help="The visualisation should pause between steps."),
    parent=bwt.subparsers
)
def trans(args: argparse.Namespace) -> None:
    'Show one transition, (i, "a") -> C["a"] + O["a", i], in the BWT search.'

    if len(args.a) != 1:  # pragma: no cover
        print("The prepend-character 'a' must have length 1. " +
              f"You provided '{args.a}'")
        import sys
        sys.exit(1)
    if not (0 <= args.k <= len(args.x)):  # pragma: no cover
        print(f"The index variable k={args.k} must be in the range " +
              f"[0,{len(args.x)}] (a valid index in the rotations).")
        import sys
        sys.exit(1)
    if args.a not in args.x:  # pragma: no cover
        print(f"The character {args.a} is not in the string.")
        import sys
        sys.exit(1)

    x, alpha = Alphabet.mapped_string_with_sentinel(args.x)
    abyte = alpha.map(args.a)[0]  # The letter in x's alphabet
    b, sa = pystr.bwt.burrows_wheeler_transform_bytes(x, alpha)
    ctab = pystr.bwt.CTable(b, len(alpha))
    otab = pystr.bwt.OTable(b, len(alpha))

    print()
    print(bright_blue(f"{underline}String we want to jump from:"))
    print()
    tbl = rotation_table(alpha.revmap(x), sa)
    tbl[args.k]["pointer"] = bold("k ->")
    tbl[args.k]["rotation"] = underline(tbl[args.k]["rotation"])
    print(tbl)
    print()
    if args.interactive:
        hit_enter()
        print()

    print(bright_blue(
        f"{underline}Attempted rotation:"))
    print()
    tbl = rotation_table(alpha.revmap(x), sa)
    tbl[args.k]["pointer"] = bold("k ->")
    tbl[args.k]["prefix"] = bright_green(args.a)
    tbl[args.k]["rotation"] = colour(tbl[args.k]["rotation"])[
        0:-1, underline][-1, black]
    print(tbl)
    print()
    if args.interactive:
        hit_enter()
        print()

    print(bright_blue(f"{underline}Find the bucket:"))
    print()
    tbl = rotation_table(alpha.revmap(x), sa)
    tbl[args.k]["pointer"] = bold("k ->")
    tbl[args.k]["prefix"] = bright_green(args.a)
    tbl[args.k]["rotation"] = colour(tbl[args.k]["rotation"])[
        0:-1, underline][-1, black]

    tbl[ctab[abyte]]["pointer"] = green(f"C[{args.a}] ->")
    for i in range(ctab[abyte], len(sa)):
        row = tbl[i]
        if not row["rotation"].startswith(args.a):
            break
        row["rotation"] = green(row["rotation"])
    print(tbl)
    print()
    if args.interactive:
        hit_enter()
        print()

    print(bright_blue(f"{underline}Count offset:"))
    print()
    tbl = rotation_table(alpha.revmap(x), sa)
    rot_rows(tbl, args.a, 0, args.k)

    tbl[args.k]["pointer"] = bold("k ->")
    tbl[args.k]["prefix"] = bright_green(args.a)
    tbl[args.k]["rotation"] = colour(tbl[args.k]["rotation"])[
        0:-1, blue & underline][-1, black]

    print(tbl)
    print()
    if args.interactive:
        hit_enter()
        print()

    print(bright_blue(f"{underline}Done:"))
    print()
    res_tbl = rotation_table(alpha.revmap(x), sa)
    shift_rows(res_tbl, ctab[abyte], ctab[abyte] + otab[abyte, args.k])

    res_tbl[ctab[abyte]]["pointer"] = green(f"C[{args.a}] ->")

    hit_idx = ctab[abyte] + otab[abyte, args.k]
    if hit_idx < len(x):
        row = res_tbl[hit_idx]
        row["pointer"] = green(f"C[{args.a}]") + " + " + \
            magenta(f"O[{args.a},{args.k}]") + " ->"

        target = args.a + strip_ansi(tbl[args.k]["rotation"])[:-1]
        hit = strip_ansi(tbl[hit_idx]["prefix"]) + \
            strip_ansi(tbl[hit_idx]["rotation"])
        match_col = green if target == hit else red

        shift_row(row)
        row["rotation"] = colour(row["rotation"])[:, underline & match_col]

    else:
        # We are pointing one past the range...
        row = res_tbl[-1]
        row["pointer"] = green(f"C[{args.a}]") + " + " + \
            magenta(f"O[{args.a},{args.k}]") + " ->"

    print()
    print(tbl | res_tbl)
    print()


@command(
    argument('x', metavar='x', type=str,
             help='string the BWT rotations are made over.'),
    argument('p', metavar='p', type=str,
             help='pattern we search for.'),
    argument('--interactive',
             action=argparse.BooleanOptionalAction,
             default=True,
             help="The visualisation should pause between steps."),

    parent=bwt.subparsers
)
def search(args: argparse.Namespace) -> None:
    "Show a BWT search for patter 'p' in string 'x'."

    if len(args.x) < len(args.p):  # pragma: no cover
        print("The pattern can't be longer than the string.")
        import sys
        sys.exit(1)

    x, alpha = Alphabet.mapped_string_with_sentinel(args.x)
    b, sa = pystr.bwt.burrows_wheeler_transform_bytes(x, alpha)
    ctab = pystr.bwt.CTable(b, len(alpha))
    otab = pystr.bwt.OTable(b, len(alpha))

    try:
        p = alpha.map(args.p)
    except KeyError:
        print("We cannot translate p into the same alphabet as x.")
        print("This means that there cannot be matches, so we stop here.")
        import sys
        sys.exit(1)

    L = 0
    R = len(x)
    for j, y in enumerate(reversed(p)):

        print()
        print(bright_blue(underline("Scanning...")))
        print(indent(len("p = ")+len(p)-j-1), "v", sep="")
        if j > 0:
            print(f"p = {colour(str(args.p))[-j:, underline]}")
        else:
            print(f"p = {args.p}")
        print()
        print("Prepending:", green(alpha.revmap(y)))
        print()

        start_tbl = rotation_table(alpha.revmap(x), sa)
        start_tbl[L]["pointer"] = bold("L ->")
        start_tbl[R]["pointer"] = bold("R ->")
        for i in range(L, R):
            row = start_tbl[i]
            row["rotation"] = colour(row["rotation"])[:j, underline & bold]

        L_tbl = rotation_table(alpha.revmap(x), sa)
        L_tbl[L]["pointer"] = bold("L ->")
        rot_rows(L_tbl, alpha.revmap(y), 0, L, blue)

        R_tbl = rotation_table(alpha.revmap(x), sa)
        R_tbl[R]["pointer"] = bold("R ->")
        rot_rows(R_tbl, alpha.revmap(y), 0, R, yellow)

        L = ctab[y] + otab[y, L]
        R = ctab[y] + otab[y, R]

        res_tbl = rotation_table(alpha.revmap(x), sa)
        if L < R:
            res_tbl[L]["pointer"] = bold("L ->")
            res_tbl[R]["pointer"] = bold("R ->")
            shift_rows(res_tbl, ctab[y], L,
                       amount=j + 1, prefix_col=red, rot_col=blue)
            shift_rows(res_tbl, L, R, amount=j + 1,
                       prefix_col=underline & green, rot_col=yellow)
        else:
            res_tbl[L]["pointer"] = bold("L & R ->")

        print()
        print(start_tbl | L_tbl | R_tbl | res_tbl)
        print()
        if args.interactive:
            hit_enter()
        print()

        if L >= R:
            L, R = 0, 0
            break

    tbl = rotation_table(alpha.revmap(x), sa)
    if L < R:
        print(bright_green("Found matches:"))
        print()
        tbl[L]["pointer"] = bold("L ->")
        tbl[R]["pointer"] = bold("R ->")
        for i in range(L, R):
            row = tbl[i]
            row["rotation"] = \
                colour(row["rotation"])[:len(p),
                                        bright_green & underline & bold]
        print(tbl)
        print()

    else:
        tbl[L]["pointer"] = bold("L & R ->")

        print(tbl)
        print()
        print(bright_red("No hits."))
        print()
