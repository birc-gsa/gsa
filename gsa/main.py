from __future__ import annotations
import sys
import typing
import argparse
import yaml
import itertools
import os.path

from . import commands

ARGS_ROOT = argparse.ArgumentParser(
    description='''
        Helper tool for exercises in Genome Scale Algorithms.
        '''
)
ARGS_ROOT.add_argument(
    '-v', '--verbose',
    help="Verbose output",
    action='store_true',
    default=False
)
SUBCOMMANDS = ARGS_ROOT.add_subparsers()


class argument:
    flags: tuple[str, ...]
    options: dict[str, typing.Any]

    def __init__(self, *flags: str, **options: typing.Any) -> None:
        self.flags = flags
        self.options = options


class command:
    args: tuple[argument, ...]
    parser: argparse.ArgumentParser
    parent: argparse._SubParsersAction
    _subparsers: typing.Optional[argparse._SubParsersAction]

    def __init__(self,
                 *args: argument,
                 parent: argparse._SubParsersAction = SUBCOMMANDS
                 ) -> None:
        self.args = args
        self.parent = parent
        self._subparsers = None

    def __call__(
        self,
        cmd: typing.Callable[[argparse.Namespace], None]
    ) -> command:
        self.cmd = cmd
        self.parser = self.parent.add_parser(
            cmd.__name__, description=cmd.__doc__
        )
        for arg in self.args:
            self.parser.add_argument(*arg.flags, **arg.options)
        self.parser.set_defaults(command=cmd)
        return self

    @property
    def subparsers(self) -> argparse._SubParsersAction:
        if self._subparsers is None:
            self._subparsers = self.parser.add_subparsers()
        return typing.cast(argparse._SubParsersAction, self._subparsers)


@command()
def simulate(args: argparse.Namespace) -> None:
    """Simulates data for GSA exercises.

    Choose a sub-command to specify which type of data.
    """
    # This is a menu point. There's not any action in it.
    # If called, we just inform the user to pick a sub-command.
    simulate.parser.print_usage()


@command(
    argument("k", help="Number of chromosomes to simulate.", type=int),
    argument("n", help="Lenght of each chromosome.", type=int),
    argument("-o", "--out",
             help="Fasta file to write the genome to (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
    parent=simulate.subparsers
)
def genome(args: argparse.Namespace) -> None:
    """Simulates genome data."""
    commands.simulate_genome(args.k, args.n, args.out)


@command(
    argument("genome", help="Genome to sample from.",
             type=argparse.FileType('r')),
    argument("k", help="Number of reads.", type=int),
    argument("n", help="Lenght of each read.", type=int),
    argument("-e", "--edits", help="Number of edits to allow (default 0).",
             type=int, default=0),
    argument("-o", "--out",
             help="Fastq file to write the reads to (default stdout).",
             type=argparse.FileType('w'), default=sys.stdout),
    parent=simulate.subparsers
)
def reads(args: argparse.Namespace) -> None:
    """Simulates reads data."""
    commands.simulate_reads(args.k, args.n, args.edits,
                            args.genome, args.out)


@command()
def test(args: argparse.Namespace) -> None:
    """Tests tools for GSA exercises.

    Choose a sub-command to specify which type of data.
    """
    # This is a menu point. There's not any action in it.
    # If called, we just inform the user to pick a sub-command.
    test.parser.print_usage()


def get_yaml_list(d: dict[str, typing.Any], name: str) -> list[typing.Any]:
    if name not in d:
        print(f"Warning: missing yaml field {name}")
        return []
    return d[name] if isinstance(d[name], list) else [d[name]]


def check_make_dir(dirname: str) -> None:
    if os.path.isfile(dirname):
        print(f"File '{dirname}' exists and isn't a directory")
        sys.exit(1)
    if not os.path.isdir(dirname):
        print(f"Creating directory '{dirname}'")
        os.mkdir(dirname)


def relink(src: str, dst: str) -> None:
    if os.path.islink(dst):
        os.remove(dst)
    if os.path.isfile(dst) or os.path.isdir(dst):
        print(f"File/directory {dst} is in the way of a symbolic link.")
        sys.exit(1)
    os.symlink(src, dst)


def test_genome_name(length: int, chromosomes: int) -> str:
    return f"genome-{length}-{chromosomes}.fa"


def test_reads_name(genome_length: int, chromosomes: int,
                    no_reads: int, read_lengths: int, edits: int) -> str:
    fasta = test_genome_name(genome_length, chromosomes)
    return f"{fasta}-reads-{no_reads}-{read_lengths}-{edits}.fq"


def test_out_name(genome_length: int, chromosomes: int,
                  no_reads: int, read_lengths: int, edits: int) -> str:
    fasta = test_genome_name(genome_length, chromosomes)
    return f"{fasta}-reads-{no_reads}-{read_lengths}-{edits}.sam"


class test_config:

    def __init__(self, config: dict[str, typing.Any]) -> None:
        self.reference = \
            config['reference-tool'] if 'reference-tool' in config else None
        if not self.reference:
            print("There is no reference tool to compare results against")
            sys.exit(1)

        self.tools = config['tools'] if 'tools' in config else None
        if not self.tools:
            print("No tools specification in configuration file")
            sys.exit(1)

        genomes = config['genomes'] if 'genomes' in config else None
        if not genomes:
            print("No genomes specification in configuration file")
            sys.exit(1)

        reads = config['reads'] if 'reads' in config else None
        if not reads:
            print("No reads specification in configuration file")
            sys.exit(1)

        genomes_k: list[int] = get_yaml_list(genomes, 'chromosomes')
        genomes_n: list[int] = get_yaml_list(genomes, 'length')
        self.genomes = list(itertools.product(genomes_k, genomes_n))

        reads_k: list[int] = get_yaml_list(reads, 'number')
        reads_n: list[int] = get_yaml_list(reads, 'length')
        reads_e: list[int] = get_yaml_list(reads, 'edits')
        self.reads = list(itertools.product(reads_k, reads_n, reads_e))


def test_setup(config: test_config, verbose: bool) -> None:
    # Setting up directories
    check_make_dir('test')
    check_make_dir('test/data')
    check_make_dir('test/tools')

    for tool in config.tools:
        check_make_dir(f'test/tools/{tool}')

    # Simulating data
    for k, n in config.genomes:
        fasta_name = f"test/data/{test_genome_name(n, k)}"
        with open(fasta_name, 'w') as f:
            commands.simulate_genome(k, n, f)

        bname = os.path.basename(fasta_name)
        for tool in config.tools:
            relink(f"../../data/{bname}", f'test/tools/{tool}/{bname}')

        for num, length, e in config.reads:
            fastq_name = f"test/data/{test_reads_name(n, k, num, length, e)}"
            with (open(fasta_name, 'r') as fasta_f,
                  open(fastq_name, 'w') as fastq_f):
                commands.simulate_reads(num, length, e, fasta_f, fastq_f)

            bname = os.path.basename(fastq_name)
            for tool in config.tools:
                relink(f"../../data/{bname}", f'test/tools/{tool}/{bname}')


def preprocess(config: test_config, verbose: bool) -> None:
    for name, tool in config.tools.items():
        if 'preprocess' in tool:
            for k, n in config.genomes:
                cmd = tool['preprocess'].format(
                    genome=f'test/tools/{name}/{test_genome_name(n, k)}'
                )
                if verbose:
                    print("Preprocessing:", cmd)
                res = os.system(f"{cmd} >& /dev/null")
                if res != 0:
                    print("Preprocessing failed!")
                    sys.exit(1)


def map(config: test_config, verbose: bool) -> None:
    for name, tool in config.tools.items():
        for k, n in config.genomes:
            fastaname = f'test/tools/{name}/{test_genome_name(n, k)}'
            for num, length, e in config.reads:
                fastqname = f"test/tools/{name}/{test_reads_name(n, k, num, length, e)}"
                outname = f"test/tools/{name}/{test_out_name(n, k, num, length, e)}"
                cmd = tool['map'].format(
                    genome=fastaname,
                    reads=fastqname,
                    e=e,
                    outfile=outname
                )
                if verbose:
                    print("Mapping:", cmd)
                res = os.system(f"{cmd} >& /dev/null")
                if res != 0:
                    print("Command:", cmd)
                    print("Mapping failed!")
                    sys.exit(1)


@command(
    argument('config',
             help="Configuration file",
             type=argparse.FileType('r')),
    parent=test.subparsers
)
def exact(args: argparse.Namespace) -> None:
    config = test_config(
        yaml.load(args.config.read(), Loader=yaml.SafeLoader)
    )
    test_setup(config, args.verbose)
    preprocess(config, args.verbose)
    map(config, args.verbose)


def main() -> None:
    args = ARGS_ROOT.parse_args()
    if 'command' not in args:
        print("Select a command to run.")
        ARGS_ROOT.print_help()
    else:
        args.command(args)
