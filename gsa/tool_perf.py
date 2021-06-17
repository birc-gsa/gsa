import typing
import os
import os.path
import itertools
import subprocess
import urllib.parse

from . import simulate
from . import messages


def get_yaml_list(d: dict[str, typing.Any], name: str) -> list[typing.Any]:
    if name not in d:
        print(f"Warning: missing yaml field {name}")
        return []
    return d[name] if isinstance(d[name], list) else [d[name]]


def check_make_dir(dirname: str) -> None:
    if os.path.isfile(dirname):
        messages.error(f"File '{dirname}' exists and isn't a directory")
    if not os.path.isdir(dirname):
        messages.message(f"Creating directory '{dirname}'")
        os.mkdir(dirname)


def relink(src: str, dst: str) -> None:
    if os.path.islink(dst):
        os.remove(dst)
    if os.path.isfile(dst) or os.path.isdir(dst):
        messages.error(
            f"File/directory {dst} is in the way of a symbolic link.")
    os.symlink(src, dst)


def genome_name(length: int, chromosomes: int) -> str:
    return f"genome-{length}-{chromosomes}.fa"


def reads_name(genome_length: int, chromosomes: int,
               no_reads: int, read_lengths: int, edits: int) -> str:
    fasta = genome_name(genome_length, chromosomes)
    return f"{fasta}-reads-{no_reads}-{read_lengths}-{edits}.fq"


def out_name(genome_length: int, chromosomes: int,
             no_reads: int, read_lengths: int, edits: int) -> str:
    fasta = genome_name(genome_length, chromosomes)
    return f"{fasta}-reads-{no_reads}-{read_lengths}-{edits}.sam"


def tool_dir(tool: str) -> str:
    return urllib.parse.quote_plus(tool)


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

        genomes_k: list[int] = get_yaml_list(genomes, 'chromosomes')
        genomes_n: list[int] = get_yaml_list(genomes, 'length')
        self.genomes = list(itertools.product(genomes_k, genomes_n))

        reads_k: list[int] = get_yaml_list(reads, 'number')
        reads_n: list[int] = get_yaml_list(reads, 'length')
        reads_e: list[int] = get_yaml_list(reads, 'edits')
        self.reads = list(itertools.product(reads_k, reads_n, reads_e))

        self.genomes_reads = list(
            itertools.product(self.genomes, self.reads)
        )


def test_setup(config: test_config, verbose: bool) -> None:
    # Setting up directories
    check_make_dir('test')
    check_make_dir('test/data')
    check_make_dir('test/tools')

    for tool in config.tools:
        check_make_dir(f'test/tools/{tool_dir(tool)}')

    # Simulating data
    for k, n in config.genomes:
        fasta_name = f"test/data/{genome_name(n, k)}"
        with open(fasta_name, 'w') as f:
            simulate.simulate_genome(k, n, f)

        bname = os.path.basename(fasta_name)
        for tool in config.tools:
            relink(f"../../data/{bname}",
                   f'test/tools/{tool_dir(tool)}/{bname}')

    for (k, n), (num, length, e) in config.genomes_reads:
        fasta_name = f"test/data/{genome_name(n, k)}"
        fastq_name = f"test/data/{reads_name(n, k, num, length, e)}"
        with (open(fasta_name, 'r') as fasta_f,
              open(fastq_name, 'w') as fastq_f):
            simulate.simulate_reads(num, length, e, fasta_f, fastq_f)

            bname = os.path.basename(fastq_name)
            for tool in config.tools:
                relink(f"../../data/{bname}",
                       f'test/tools/{tool_dir(tool)}/{bname}')


def test_preprocess(config: test_config, verbose: bool) -> None:
    for name, tool in config.tools.items():
        if 'preprocess' in tool:
            for k, n in config.genomes:
                fastafile = f'test/tools/{tool_dir(name)}/{genome_name(n, k)}'
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
            fastaname = f'test/tools/{tool_dir(name)}/{genome_name(n, k)}'
            fastqname = f"test/tools/{tool_dir(name)}/{reads_name(n, k, num, length, e)}"  # noqal: E501
            outname = f"test/tools/{name}/{out_name(n, k, num, length, e)}"      # noqal: E501

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
        f"test/tools/{tool_dir(tool)}/{out_name(n, k, num, length, e)}"  # noqal: E501
        for (k, n), (num, length, e) in config.genomes_reads
    ]


def compare_files(fname1: str, fname2: str) -> bool:
    with (open(fname1) as f1,
          open(fname2) as f2):
        return set(f1.readlines()) == set(f2.readlines())


def test_compare(config: test_config, verbose: bool) -> None:
    ref_sams = sam_files(config.reference, config)
    for tool in config.tools:
        tooltest = True
        if tool == config.reference:
            continue
        tool_sams = sam_files(tool, config)
        for refsam, toolsam in zip(ref_sams, tool_sams):
            if verbose:
                print(f"Comparing: {refsam} vs {toolsam}", end="\t")
            cmp_res = compare_files(refsam, toolsam)
            tooltest &= cmp_res
            if verbose:
                if cmp_res:
                    print("\u2705")
                else:
                    print("\u274c")
        if tooltest:
            print(f"Tool {tool} passed the test.")
        else:
            print(f"Tool {tool} failed the test.")
