from __future__ import annotations
from mypy_extensions import (Arg, DefaultArg)

import typing
import pickle
import pystr.alphabet
import pystr.bwt
import pystr.exact
import os

from . import fasta
from . import fastq
from . import sam
from . import error


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

PystrPreprocessedGenome = dict[
    str, typing.Callable[[str], typing.Iterator[int]]
]


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


class BWT(Search):
    name = "bwt"
    can_preprocess = True

    @staticmethod
    def preprocess(fastaname: str) -> None:

        preproc_name = f"{fastaname}.bwt_tables"
        if os.path.isfile(preproc_name) and \
                not os.access(preproc_name, os.W_OK):
            error.error(f"Can't open genome file {preproc_name}")

        preprocessed: dict[
            str,
            tuple[pystr.alphabet.Alphabet,
                  list[int],
                  pystr.bwt.CTable,
                  pystr.bwt.OTable]
        ] = {}
        with open(fastaname, 'r') as f:
            genome = fasta.read_fasta(f)
            for chrname, seq in genome.items():
                bwt, alpha, sa = pystr.bwt.burrows_wheeler_transform(seq)
                ctab = pystr.bwt.CTable(bwt, len(alpha))
                otab = pystr.bwt.OTable(bwt, len(alpha))
                preprocessed[chrname] = (alpha, sa, ctab, otab)

        with open(preproc_name, 'wb') as preprocfile:
            pickle.dump(preprocessed, preprocfile)

    @staticmethod
    def map(fastaname: str,
            fastqname: str,
            out: typing.TextIO,
            edits: int
            ) -> None:

        preprocessed: PystrPreprocessedGenome = {}

        preproc_name = f"{fastaname}.bwt_tables"
        if os.access(preproc_name, os.R_OK):
            with open(preproc_name, 'rb') as preproc_file:
                preproc_tables = pickle.load(preproc_file)
                for chrname, (alpha, sa, ctab, otab) in preproc_tables.items():
                    preprocessed[chrname] = pystr.bwt.searcher_from_tables(
                        alpha, sa, ctab, otab
                    )
        else:
            # We don't have preprocessed info, so we build tables from
            # scratch
            with open(fastaname, 'r') as f:
                genome = fasta.read_fasta(f)
            for chrname, seq in genome.items():
                preprocessed[chrname] = pystr.bwt.preprocess(seq)

        with open(fastqname, 'r') as f:
            for readname, read, qual in fastq.scan_reads(f):
                for chrname, search in preprocessed.items():
                    for pos in search(read):
                        sam.sam_record(
                            out,
                            readname, chrname,
                            pos, f'{len(read)}M',
                            read, qual
                        )
