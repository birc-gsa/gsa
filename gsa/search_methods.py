from __future__ import annotations
from mypy_extensions import Arg

import argparse
import typing
import pickle
import pystr.alphabet
import pystr.bwt
import pystr.exact
import os

from . import fasta
from . import fastq
from . import sam
from . import messages

T = typing.TypeVar('T')

# I'm telling flake8 to shut up a few places here, because it
# moronically complains that the strings in Arg() are undefined
# names (which they are, but they are also fucking strings).
# It's a known issue, but not fixed yet
PystrExactSearchF = typing.Callable[
    [Arg(str, "x"),      # noqal F821
     Arg(str, "p")],     # noqal F821
    typing.Iterator[int]
]

PystrExactPreprocessedF = typing.Callable[
    [Arg(str, "p")],   # noqal F821
    typing.Iterator[int]
]

PystrApproxPreprocessedF = typing.Callable[
    [Arg(str, "p"),        # noqal F821
     Arg(int, "edits")],   # noqal F821
    typing.Iterator[tuple[int, str]]
]

PystrPreprocessF = typing.Callable[
    [Arg(str, "x")],     # noqal F821
    typing.Any
]

PystrReadExactPreprocessF = typing.Callable[
    [typing.Any],     # noqal F821
    PystrExactPreprocessedF
]

PystrReadApproxPreprocessF = typing.Callable[
    [typing.Any],     # noqal F821
    PystrApproxPreprocessedF
]

GSACommandF = typing.Callable[
    [Arg(argparse.Namespace, "args")],      # noqal F821
    None
]


def check_preprocess_input(args: argparse.Namespace) -> None:
    if not os.access(args.genome, os.R_OK):
        messages.error(f"Can't open genome file {args.genome}")


def preprocess_wrapper(prep: PystrPreprocessF) -> GSACommandF:
    def wrap(args: argparse.Namespace) -> None:
        check_preprocess_input(args)
        preproc_name = args.genome + '.' + prep.__name__
        if os.path.isfile(preproc_name) and \
                not os.access(preproc_name, os.W_OK):
            messages.error(f"Can't open preprocessing file {preproc_name}")

        with open(args.genome, 'r') as f:
            genome = fasta.read_fasta(f)
        preprocessed = {
            chrname: prep(seq) for chrname, seq in genome.items()
        }
        with open(preproc_name, 'wb') as preprocfile:
            pickle.dump(preprocessed, preprocfile)

    wrap.__name__ = prep.__name__
    wrap.__doc__ = prep.__name__
    return wrap


def check_map_input(args: argparse.Namespace) -> None:
    if not os.access(args.genome, os.R_OK):
        messages.error(f"Can't open genome file {args.genome}")
    if not os.access(args.reads, os.R_OK):
        messages.error(f"Can't open fastq file {args.reads}")


def exact_search_wrapper(search: PystrExactSearchF) -> GSACommandF:
    def wrap(args: argparse.Namespace) -> None:
        check_map_input(args)
        with open(args.genome, 'r') as f:
            genome = fasta.read_fasta(f)
        with open(args.reads, 'r') as f:
            for readname, read, qual in fastq.scan_reads(f):
                for chrname, seq in genome.items():
                    for pos in search(seq, read):
                        sam.sam_record(
                            args.out,
                            readname, chrname,
                            pos, f'{len(read)}M',
                            read, qual
                        )
    wrap.__name__ = search.__name__
    wrap.__doc__ = search.__doc__
    return wrap


def read_or_compute_preprocessed(
    genome: str,
    prep: PystrPreprocessF,
    search_wrap: typing.Callable[[typing.Any], T]
) -> dict[str, T]:
    preproc_name = genome + '.' + prep.__name__
    if os.path.isfile(preproc_name) and os.access(preproc_name, os.R_OK):
        # Unpickle the preprocessed file
        with open(preproc_name, 'rb') as preproc_file:
            preproc_table = pickle.load(preproc_file)
    else:  # we need to do the preprocessing now
        with open(genome, 'r') as f:
            chromosomes = fasta.read_fasta(f)
        preproc_table = {
            chrname: prep(seq) for chrname, seq in chromosomes.items()
        }
    return {
        chrname: search_wrap(x) for chrname, x in preproc_table.items()
    }


def exact_search_preprocess_wrapper(
    name: str, doc: str,
    prep: PystrPreprocessF,
    search_wrap: PystrReadExactPreprocessF
) -> GSACommandF:
    def wrap(args: argparse.Namespace) -> None:
        check_map_input(args)

        searchers = read_or_compute_preprocessed(
            args.genome, prep, search_wrap
        )
        with open(args.reads, 'r') as f:
            for readname, read, qual in fastq.scan_reads(f):
                for chrname, search in searchers.items():
                    for pos in search(read):
                        sam.sam_record(
                            args.out,
                            readname, chrname,
                            pos, f'{len(read)}M',
                            read, qual
                        )
    wrap.__name__ = name
    wrap.__doc__ = doc
    return wrap


def approx_search_preprocess_wrapper(
    name: str, doc: str,
    prep: PystrPreprocessF,
    search_wrap: PystrReadApproxPreprocessF
) -> GSACommandF:
    def wrap(args: argparse.Namespace) -> None:
        check_map_input(args)

        searchers = read_or_compute_preprocessed(
            args.genome, prep, search_wrap
        )
        with open(args.reads, 'r') as f:
            for readname, read, qual in fastq.scan_reads(f):
                for chrname, search in searchers.items():
                    for pos, cigar in search(read, args.edits):
                        sam.sam_record(
                            args.out,
                            readname, chrname,
                            pos, cigar,
                            read, qual
                        )
    wrap.__name__ = name
    wrap.__doc__ = doc
    return wrap


def exact_bwt(x: str) -> typing.Any:
    """Preprocessing for the exact BWT search."""
    print("PREPROCESSING BWT")
    bwt, alpha, sa = pystr.bwt.burrows_wheeler_transform(x)
    ctab = pystr.bwt.CTable(bwt, len(alpha))
    otab = pystr.bwt.OTable(bwt, len(alpha))
    return alpha, sa, ctab, otab


def exact_bwt_search_wrapper(tables: typing.Any) -> PystrExactPreprocessedF:
    return pystr.bwt.exact_searcher_from_tables(*tables)


def approx_bwt(x: str) -> typing.Any:
    """Preprocessing for the approximative BWT search."""
    bwt, alpha, sa = pystr.bwt.burrows_wheeler_transform(x)
    ctab = pystr.bwt.CTable(bwt, len(alpha))
    otab = pystr.bwt.OTable(bwt, len(alpha))
    # FIXME: ad rotab
    return alpha, sa, ctab, otab


def approx_bwt_search_wrapper(tables: typing.Any) -> PystrApproxPreprocessedF:
    return pystr.bwt.approx_searcher_from_tables(*tables)


preprocess: list[GSACommandF] = [
    preprocess_wrapper(exact_bwt),
    preprocess_wrapper(approx_bwt)
]

exact_search: list[GSACommandF] = [
    exact_search_wrapper(pystr.exact.naive),
    exact_search_wrapper(pystr.exact.kmp),
    exact_search_wrapper(pystr.exact.border),
    exact_search_wrapper(pystr.exact.bmh),
    exact_search_preprocess_wrapper(
        'bwt',
        'Burrows-Wheeler FM-index search',
        exact_bwt, exact_bwt_search_wrapper)
]

approx_search: list[GSACommandF] = [
    approx_search_preprocess_wrapper(
        'bwt',
        'Burrows-Wheeler FM-index search',
        approx_bwt, approx_bwt_search_wrapper)
]
