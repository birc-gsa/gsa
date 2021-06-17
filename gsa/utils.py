import typing
import urllib.parse
import os.path

from . import messages


def get_yaml_list(d: dict[str, typing.Any], name: str) -> list[typing.Any]:
    if name not in d:
        print(f"Warning: missing yaml field {name}")
        return []
    if isinstance(d[name], list):
        # I don't know why the cast is necessary. It should be
        # obvious from the isinstance check. But mypy wants it.
        return typing.cast(list[typing.Any], d[name])
    else:
        return [d[name]]


def check_make_dir(dirname: str, verbose: bool) -> None:
    if os.path.isfile(dirname):
        messages.error(f"File '{dirname}' exists and isn't a directory")
    if not os.path.isdir(dirname):
        if verbose:
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
