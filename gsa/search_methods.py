from __future__ import annotations
import typing
import pystr.exact
from mypy_extensions import (Arg, DefaultArg)

from . import fasta
from . import fastq
from . import sam


class Search:
    name: str = "<abstract>"
    can_preprocess: bool = False
    can_approx: bool = False

    @staticmethod
    def preprocess(fastaname: str) -> None:
        ...

    @staticmethod
    def map(fastaname: str,
            fastqname: str,
            out: typing.TextIO,
            edits: int
            ) -> None:
        ...


# I'm telling flake8 to shut up a few places here, because it
# moronically complains that the strings in Arg() are undefined
# names (which they are, but they are also fucking strings).
# It's a known issue, but not fixed yet
PystrExactSearchF = typing.Callable[
    [Arg(str, "x"),      # noqal F821
     Arg(str, "p")],     # noqal F821
    typing.Iterator[int]]


GSASearchF = typing.Callable[
    [Arg(str, "fastaname"),      # noqal F821
     Arg(str, "fastqname"),      # noqal F821
     Arg(typing.TextIO, "out"),  # noqal F821
     DefaultArg(int, "edits")],  # noqal F821
    None]


def exact_search_wrapper(search: PystrExactSearchF) -> GSASearchF:
    def wrap(fastaname: str,
             fastqname: str,
             out: typing.TextIO,
             edits: int = 0
             ) -> None:
        with open(fastaname, 'r') as f:
            genome = fasta.read_fasta(f)
        with open(fastqname, 'r') as f:
            for readname, read, qual in fastq.scan_reads(f):
                print('=' * 10, readname, '=' * 10)
                for chrname, seq in genome.items():
                    for pos in search(seq, read):
                        sam.sam_record(
                            out,
                            readname, chrname,
                            pos, f'{len(read)}M',
                            read, qual
                        )
    return wrap


class Naive(Search):
    """The naive quadratic time algorithm."""
    name = "naive"
    map = exact_search_wrapper(pystr.exact.naive)


class KMP(Search):
    """The Knuth-Morris-Pratt linear-time algorithm."""
    name = "kmp"
    map = exact_search_wrapper(pystr.exact.kmp)


class Border(Search):
    """The border-array linear-time algorithm."""
    name = "border"
    map = exact_search_wrapper(pystr.exact.border)


class BMH(Search):
    """The Boyer-Moore-Horspool linear-time algorithm."""
    name = "bmh"
    map = exact_search_wrapper(pystr.exact.bmh)
