import typing
import os
import os.path
import itertools
import subprocess

from . import simulate
from . import messages
from . import utils
from .vis import Table, ColSpec


class test_config:

    def __init__(self, config: dict[str, typing.Any]) -> None:
        self.reference = \
            config['reference-tool'] if 'reference-tool' in config else None
        if not self.reference:
            messages.error(
                "There is no reference tool to compare results against")

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


def test_setup(config: test_config, verbose: bool) -> None:
    # Setting up directories
    utils.check_make_dir('test')
    utils.check_make_dir('test/data')
    utils.check_make_dir('test/tools')

    for tool in config.tools:
        utils.check_make_dir(f'test/tools/{utils.tool_dir(tool)}')

    # Simulating data
    for k, n in config.genomes:
        fasta_name = f"test/data/{utils.genome_name(n, k)}"
        with open(fasta_name, 'w') as f:
            simulate.simulate_genome(k, n, f)

        bname = os.path.basename(fasta_name)
        for tool in config.tools:
            utils.relink(f"../../data/{bname}",
                         f'test/tools/{utils.tool_dir(tool)}/{bname}')

    for (k, n), (num, length, e) in config.genomes_reads:
        fasta_name = f"test/data/{utils.genome_name(n, k)}"
        fastq_name = f"test/data/{utils.reads_name(n, k, num, length, e)}"
        with (open(fasta_name, 'r') as fasta_f,
              open(fastq_name, 'w') as fastq_f):
            simulate.simulate_reads(num, length, e, fasta_f, fastq_f)

            bname = os.path.basename(fastq_name)
            for tool in config.tools:
                utils.relink(f"../../data/{bname}",
                             f'test/tools/{utils.tool_dir(tool)}/{bname}')


def test_preprocess(config: test_config, verbose: bool) -> None:
    for name, tool in config.tools.items():
        if 'preprocess' in tool:
            for k, n in config.genomes:
                fastafile = \
                    f'test/tools/{utils.tool_dir(name)}/{utils.genome_name(n, k)}'  # noqal: E501
                if not os.path.isfile(fastafile):
                    messages.error(f"Genome file {fastafile} not found")
                cmd = tool['preprocess'].format(
                    genome=fastafile
                )
                if verbose:
                    print("Preprocessing:", cmd)
                res = subprocess.run(
                    args=cmd,
                    shell=True,
                    stdout=open(os.devnull, 'w'),
                    stderr=open(os.devnull, 'w')
                )
                if res.returncode != 0:
                    messages.error("Preprocessing failed!")


def test_map(config: test_config, verbose: bool) -> None:
    for name, tool in config.tools.items():
        for (k, n), (num, length, e) in config.genomes_reads:
            fastaname = f'test/tools/{utils.tool_dir(name)}/{utils.genome_name(n, k)}'                 # noqal: E501
            fastqname = f"test/tools/{utils.tool_dir(name)}/{utils.reads_name(n, k, num, length, e)}"  # noqal: E501
            outname = f"test/tools/{name}/{utils.out_name(n, k, num, length, e)}"                      # noqal: E501

            if not os.path.isfile(fastaname):
                messages.error(f"Couldn't find fasta file {fastaname}")
            if not os.path.isfile(fastqname):
                messages.error(f"Couldn't find fast1 file {fastqname}")

            cmd = tool['map'].format(
                genome=fastaname,
                reads=fastqname,
                e=e,
                outfile=outname
            )
            if verbose:
                print("Mapping:", cmd)
            res = subprocess.run(
                args=cmd,
                shell=True,
                stdout=open(os.devnull, 'w'),
                stderr=open(os.devnull, 'w')
            )
            if res.returncode != 0:
                messages.error(f"Mapping failed for command: {cmd}")


def sam_files(tool: str, config: test_config) -> list[str]:
    return [
        f"test/tools/{utils.tool_dir(tool)}/{utils.out_name(n, k, num, length, e)}"  # noqal: E501
        for (k, n), (num, length, e) in config.genomes_reads
    ]


def compare_files(fname1: str, fname2: str) -> bool:
    if not os.access(fname1, os.R_OK):
        messages.warning(f"Can't open file {fname1}")
        return False

    if not os.access(fname2, os.R_OK):
        messages.warning(f"Can't open file {fname2}")
        return False

    with (open(fname1) as f1,
          open(fname2) as f2):
        return set(f1.readlines()) == set(f2.readlines())


def test_tool(ref_sams: list[str],
              tool_sams: list[str],
              verbose: bool) -> list[bool]:

    results = [False] * len(ref_sams)
    tooltest = True
    for i, (refsam, toolsam) in enumerate(zip(ref_sams, tool_sams)):
        if verbose:
            messages.message(f"Comparing: {refsam} vs {toolsam}", end="\t")
        cmp_res = compare_files(refsam, toolsam)
        results[i] = cmp_res
        tooltest &= cmp_res
        if verbose:
            if cmp_res:
                messages.message("\u2705")
            else:
                messages.message("\u274c")
    return results


def test_compare(config: test_config,
                 report_out: typing.TextIO,
                 verbose: bool) -> None:
    ref_sams = sam_files(config.reference, config)
    res: dict[str, list[bool]] = {}
    for tool in config.tools:
        if tool == config.reference:
            continue
        tool_sams = sam_files(tool, config)
        res[tool] = test_tool(ref_sams, tool_sams, verbose)

    tool_names = list(res.keys())
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
        *(f"{tool}" for tool in res)
    )
    for i, ((no_chrom, chrom_len), (no_reads, read_len, edits))\
            in enumerate(config.genomes_reads):
        row = res_tbl.add_row()
        row["no_chrom"] = no_chrom
        row["chrom_len"] = chrom_len
        row["no_reads"] = no_reads
        row["read_len"] = read_len
        row["edits"] = edits
        for tool, bits in res.items():
            row[tool] = "OK" if bits[i] else "FAIL"
    print(res_tbl, file=report_out)
