import typing
import os
import os.path
import itertools
import subprocess
import time

from . import simulate
from . import messages
from . import utils

from .vis import Table, ColSpec


T = typing.TypeVar('T')


class perf_config:
    def __init__(self, config: dict[str, typing.Any]) -> None:
        self.tools = config['tools'] if 'tools' in config else None
        if not self.tools:
            messages.error("No tools specification in configuration file")

        genomes = config['genomes'] if 'genomes' in config else None
        if not genomes:
            messages.error("No genomes specification in configuration file")

        reads = config['reads'] if 'reads' in config else None
        if not reads:
            messages.error("No reads specification in configuration file")

        genomes_k: list[int] = utils.get_yaml_list(genomes, 'chromosomes')
        genomes_n: list[int] = utils.get_yaml_list(genomes, 'length')
        self.genomes = list(itertools.product(genomes_k, genomes_n))

        reads_k: list[int] = utils.get_yaml_list(reads, 'number')
        reads_n: list[int] = utils.get_yaml_list(reads, 'length')
        reads_e: list[int] = utils.get_yaml_list(reads, 'edits')
        self.reads = list(itertools.product(reads_k, reads_n, reads_e))

        self.genomes_reads = list(
            itertools.product(self.genomes, self.reads)
        )


def perf_setup(config: perf_config, verbose: bool) -> None:
    # Setting up directories
    utils.check_make_dir('__PERF__', verbose)
    utils.check_make_dir('__PERF__/data', verbose)
    utils.check_make_dir('__PERF__/tools', verbose)

    for tool in config.tools:
        utils.check_make_dir(f'__PERF__/tools/{utils.tool_dir(tool)}', verbose)

    # Simulating data
    for k, n in config.genomes:
        fasta_name = f"__PERF__/data/{utils.genome_name(n, k)}"
        with open(fasta_name, 'w') as f:
            simulate.simulate_genome(k, n, f)

        bname = os.path.basename(fasta_name)
        for tool in config.tools:
            utils.relink(f"../../data/{bname}",
                         f'__PERF__/tools/{utils.tool_dir(tool)}/{bname}')

    for (k, n), (num, length, e) in config.genomes_reads:
        fasta_name = f"__PERF__/data/{utils.genome_name(n, k)}"
        fastq_name = f"__PERF__/data/{utils.reads_name(n, k, num, length, e)}"
        with (open(fasta_name, 'r') as fasta_f,
              open(fastq_name, 'w') as fastq_f):
            simulate.simulate_reads(num, length, e, fasta_f, fastq_f)

            bname = os.path.basename(fastq_name)
            for tool in config.tools:
                utils.relink(f"../../data/{bname}",
                             f'__PERF__/tools/{utils.tool_dir(tool)}/{bname}')


def dup(n: int, itr: typing.Iterable[T]) -> typing.Iterator[T]:
    """Modifies the iterator itr so we get each element n times."""
    for x in iter(itr):
        for _ in range(n):
            yield x


def perf_preprocess(config: perf_config,
                    repeats: int,
                    out: typing.TextIO,
                    verbose: bool) -> None:

    prep_tools = [
        name for name, tool in config.tools.items() if 'preprocess' in tool
    ]

    # No need to check this for all repeats, so just check at the beginning...
    for name in prep_tools:
        tool = config.tools[name]
        for k, n in dup(repeats, config.genomes):
            fastafile = f'__PERF__/tools/{utils.tool_dir(name)}/{utils.genome_name(n, k)}'  # noqal: E501
            if not os.path.isfile(fastafile):
                messages.error(f"Genome file {fastafile} not found")

    res_tbl = Table(
        ColSpec("no_chrom", right_pad=", "),
        ColSpec("chrom_len", right_pad=", "),
        *(ColSpec(tool, right_pad=", ") for tool in prep_tools[:-1]),
        ColSpec(prep_tools[-1])
    )
    # header
    res_tbl.append_row(
        "Chromosomes", "Chromosome length",
        *prep_tools
    )

    for k, n in dup(repeats, config.genomes):
        row = res_tbl.add_row()
        row["no_chrom"] = k
        row["chrom_len"] = n

    for name in prep_tools:
        tool = config.tools[name]
        for i, (k, n) in enumerate(dup(repeats, config.genomes)):
            cmd = tool['preprocess'].format(
                genome=f'__PERF__/tools/{utils.tool_dir(name)}/{utils.genome_name(n, k)}'  # noqal: E501
            )
            start = time.time()
            res = subprocess.run(
                args=cmd,
                shell=True,
                stdout=open(os.devnull, 'w'),
                stderr=open(os.devnull, 'w')
            )
            if res.returncode != 0:
                messages.error("Preprocessing failed!")
            end = time.time()
            res_tbl[i+1][name] = str(end-start)

    print(res_tbl, file=out)


def perf_map(config: perf_config,
             repeats: int,
             out: typing.TextIO,
             verbose: bool) -> None:

    # Check files up front
    for name, tool in config.tools.items():
        for (k, n), (num, length, e) in config.genomes_reads:
            fastaname = f'__PERF__/tools/{utils.tool_dir(name)}/{utils.genome_name(n, k)}'                 # noqal: E501
            fastqname = f"__PERF__/tools/{utils.tool_dir(name)}/{utils.reads_name(n, k, num, length, e)}"  # noqal: E501

            if not os.path.isfile(fastaname):
                messages.error(f"Couldn't find fasta file {fastaname}")
            if not os.path.isfile(fastqname):
                messages.error(f"Couldn't find fast1 file {fastqname}")

    tool_names = list(config.tools.keys())
    res_tbl = Table(
        ColSpec("no_chrom", right_pad=", "),
        ColSpec("chrom_len", right_pad=", "),
        ColSpec("no_reads", right_pad=", "),
        ColSpec("read_len", right_pad=", "),
        ColSpec("edits", right_pad=", "),
        *(ColSpec(tool, right_pad=", ") for tool in tool_names[:-1]),
        ColSpec(tool_names[-1])
    )
    res_tbl.append_row(
        "Chromosomes", "Chromosome length",
        "Number of reads", "Read length", "Edits",
        *tool_names
    )
    for (k, n), (num, length, e) in dup(repeats, config.genomes_reads):
        row = res_tbl.add_row()
        row["no_chrom"] = k
        row["chrom_len"] = n
        row["no_reads"] = num
        row["read_len"] = length
        row["edits"] = e

    for name, tool in config.tools.items():
        for i, ((k, n), (num, length, e)) \
                in enumerate(dup(repeats, config.genomes_reads)):

            fastaname = f'__PERF__/tools/{utils.tool_dir(name)}/{utils.genome_name(n, k)}'                 # noqal: E501
            fastqname = f"__PERF__/tools/{utils.tool_dir(name)}/{utils.reads_name(n, k, num, length, e)}"  # noqal: E501

            cmd = tool['map'].format(
                genome=fastaname,
                reads=fastqname,
                e=e,
                outfile=os.devnull
            )
            start = time.time()
            res = subprocess.run(
                args=cmd,
                shell=True,
                stdout=open(os.devnull, 'w'),
                stderr=open(os.devnull, 'w')
            )
            if res.returncode != 0:
                messages.error(f"Mapping failed for command: {cmd}")
            end = time.time()
            res_tbl[i+1][name] = str(end-start)

    print(res_tbl, file=out)
